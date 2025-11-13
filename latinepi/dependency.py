"""
Phase 3: Dependency parsing for Latin inscriptions.

This module uses dependency parsing to understand grammatical relationships
between words, revealing WHO did WHAT to WHOM even in complex inscriptions.
"""

import re
from typing import Dict, Any, List, Tuple, Optional


class LatinDependencyParser:
    """
    Dependency parser for Latin inscriptions using CLTK.

    Analyzes syntactic dependencies to extract:
    - Subject-verb relationships (who performed the action)
    - Object relationships (to whom/for whom)
    - Genitive modifiers (possessive relationships)
    - Nested structures (multiple people, complex dedications)
    """

    def __init__(self):
        """Initialize the dependency parser."""
        self._nlp = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of CLTK to avoid startup overhead."""
        if self._initialized:
            return

        try:
            from cltk import NLP
            self._nlp = NLP(language="lat", suppress_banner=True)
            self._initialized = True
        except ImportError:
            raise ImportError(
                "CLTK is required for dependency parsing. "
                "Install with: pip install cltk"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize CLTK: {e}")

    def parse_dependencies(self, text: str) -> Dict[str, Any]:
        """
        Parse dependencies in the inscription text.

        Args:
            text: The inscription text to parse

        Returns:
            Dictionary containing dependency parse tree and analysis
        """
        self._ensure_initialized()

        # Normalize text
        normalized_text = text.replace('<BR>', ' ').replace('<BR/>', ' ')
        normalized_text = re.sub(r'\s+', ' ', normalized_text.strip())

        try:
            doc = self._nlp.analyze(text=normalized_text)
            return {
                'doc': doc,
                'words': doc.words if hasattr(doc, 'words') else [],
                'sentences': doc.sentences if hasattr(doc, 'sentences') else [],
            }
        except Exception as e:
            return {
                'error': str(e),
                'doc': None,
                'words': [],
                'sentences': []
            }

    def extract_entities_by_dependencies(self, text: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract entities using dependency parsing.

        Identifies:
        - Main verbs (FECIT, POSUIT, etc.)
        - Subjects of verbs (dedicators)
        - Objects of verbs (recipients)
        - Genitive modifiers (possessors/deceased)
        - Nested relationships

        Args:
            text: The inscription text to analyze

        Returns:
            Dictionary of extracted entities with confidence scores
        """
        entities = {}
        parse_result = self.parse_dependencies(text)

        if 'error' in parse_result or not parse_result['words']:
            return entities

        doc = parse_result['doc']
        words = parse_result['words']

        # Extract using dependency rules
        entities.update(self._extract_verb_subjects(words, text))
        entities.update(self._extract_verb_objects(words))
        entities.update(self._extract_genitive_modifiers(words))
        entities.update(self._extract_nested_relationships(words, text))

        return entities

    def _extract_verb_subjects(
        self,
        words: List[Any],
        text: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract subjects of main verbs using dependency relations.

        Looks for:
        - FECIT/POSUIT with nsubj (nominal subject)
        - Subject is typically the dedicator
        """
        entities = {}

        # Find dedication verbs in text
        dedication_verbs = ['FECIT', 'FECERUNT', 'POSUIT', 'POSUERUNT',
                           'CURAVIT', 'CURAVERUNT']
        text_upper = text.upper()
        main_verb_found = None
        for verb in dedication_verbs:
            if verb in text_upper:
                main_verb_found = verb
                break

        if not main_verb_found:
            return entities

        # Find the verb word and its subjects using dependencies
        subjects = []
        verb_index = -1

        for i, word in enumerate(words):
            # Find the main verb
            if (hasattr(word, 'string') and
                word.string.upper() in dedication_verbs):
                verb_index = i

            # Look for words with nsubj (nominal subject) dependency
            if hasattr(word, 'dependency_relation'):
                dep_rel = word.dependency_relation
                if dep_rel in ['nsubj', 'nsubj:pass']:
                    # Check if this is subject of our verb
                    if hasattr(word, 'governor'):
                        # In some parsers, governor points to head
                        subjects.append(word.string)
                    else:
                        # Fallback: assume subjects come before verb
                        if i < verb_index or verb_index == -1:
                            if hasattr(word, 'pos') and word.pos in ['PROPN', 'NOUN']:
                                subjects.append(word.string)

        if subjects:
            dedicator_name = ' '.join(subjects)
            entities['dedicator_dependency'] = {
                'value': dedicator_name,
                'confidence': 0.88,
                'source': 'dependency',
                'relation': 'subject_of_' + main_verb_found.lower()
            }

        return entities

    def _extract_verb_objects(self, words: List[Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract objects of verbs using dependency relations.

        Looks for:
        - obj (direct object)
        - iobj (indirect object) - typically dative relationships
        """
        entities = {}

        indirect_objects = []

        for word in words:
            if not hasattr(word, 'dependency_relation'):
                continue

            dep_rel = word.dependency_relation

            # Indirect object (dative) - recipient of dedication
            if dep_rel in ['iobj', 'obl']:
                if hasattr(word, 'lemma'):
                    lemma = word.lemma.lower()
                    # Check if it's a relationship word
                    relationship_map = {
                        'pater': 'father',
                        'mater': 'mother',
                        'filius': 'son',
                        'filia': 'daughter',
                        'coniunx': 'spouse',
                        'uxor': 'wife',
                    }
                    if lemma in relationship_map:
                        entities['relationship_dependency'] = {
                            'value': relationship_map[lemma],
                            'confidence': 0.90,
                            'source': 'dependency',
                            'relation': 'indirect_object'
                        }

                # Also store the word itself
                if hasattr(word, 'string'):
                    indirect_objects.append(word.string)

        return entities

    def _extract_genitive_modifiers(self, words: List[Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract genitive modifiers using dependency relations.

        Looks for:
        - nmod (nominal modifier) with genitive case
        - Indicates possession or relationship
        """
        entities = {}
        genitive_chains = []

        for word in words:
            if not hasattr(word, 'dependency_relation'):
                continue

            dep_rel = word.dependency_relation

            # Nominal modifier (often genitive)
            if dep_rel in ['nmod', 'nmod:poss']:
                if hasattr(word, 'features') and word.features:
                    if word.features.get('Case') == 'Gen':
                        if hasattr(word, 'string'):
                            genitive_chains.append(word.string)

        if genitive_chains:
            # Genitive modifiers typically refer to the deceased
            deceased_name = ' '.join(genitive_chains)
            entities['deceased_name_dependency'] = {
                'value': deceased_name,
                'confidence': 0.86,
                'source': 'dependency',
                'relation': 'genitive_modifier'
            }

        return entities

    def _extract_nested_relationships(
        self,
        words: List[Any],
        text: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract nested relationships from complex inscriptions.

        Handles patterns like:
        - Multiple dedicators (ET pattern)
        - Multiple relationships
        - Nested genitive chains
        """
        entities = {}

        # Look for coordination (ET = and)
        text_upper = text.upper()
        if ' ET ' in text_upper:
            entities['has_coordination'] = {
                'value': 'true',
                'confidence': 0.95,
                'source': 'dependency'
            }

            # Find coordinated subjects
            coordinated_subjects = []
            for word in words:
                if hasattr(word, 'dependency_relation'):
                    # Look for conj (conjunction) relation
                    if word.dependency_relation == 'conj':
                        if hasattr(word, 'pos') and word.pos in ['PROPN', 'NOUN']:
                            if hasattr(word, 'string'):
                                coordinated_subjects.append(word.string)

            if coordinated_subjects:
                entities['coordinated_dedicators'] = {
                    'value': ', '.join(coordinated_subjects),
                    'confidence': 0.82,
                    'source': 'dependency',
                    'relation': 'coordination'
                }

        return entities

    def get_dependency_tree(self, text: str) -> List[Dict[str, Any]]:
        """
        Get full dependency tree for visualization/debugging.

        Returns:
            List of dictionaries with word, lemma, pos, dependency relation, head
        """
        parse_result = self.parse_dependencies(text)
        result = []

        if 'error' in parse_result or not parse_result['words']:
            return result

        for i, word in enumerate(parse_result['words']):
            word_info = {
                'index': i,
                'word': word.string if hasattr(word, 'string') else str(word),
                'lemma': word.lemma if hasattr(word, 'lemma') else None,
                'pos': word.pos if hasattr(word, 'pos') else None,
                'dependency_relation': None,
                'head': None,
            }

            if hasattr(word, 'dependency_relation'):
                word_info['dependency_relation'] = word.dependency_relation

            if hasattr(word, 'governor'):
                word_info['head'] = word.governor

            result.append(word_info)

        return result

    def analyze_inscription_structure(self, text: str) -> Dict[str, Any]:
        """
        Provide high-level structural analysis of inscription.

        Returns:
            Dictionary with analysis including:
            - Main verb identified
            - Subject count
            - Object count
            - Complexity score
            - Inscription type (simple dedication, epitaph, etc.)
        """
        parse_result = self.parse_dependencies(text)

        if 'error' in parse_result:
            return {'error': parse_result['error']}

        words = parse_result['words']
        text_upper = text.upper()

        analysis = {
            'word_count': len(words),
            'has_main_verb': False,
            'main_verb': None,
            'subject_count': 0,
            'has_genitive': False,
            'has_dative': False,
            'has_coordination': ' ET ' in text_upper,
            'complexity': 'simple'
        }

        # Find main verb
        dedication_verbs = ['FECIT', 'FECERUNT', 'POSUIT', 'POSUERUNT']
        for verb in dedication_verbs:
            if verb in text_upper:
                analysis['has_main_verb'] = True
                analysis['main_verb'] = verb
                break

        # Count subjects, genitives, datives
        for word in words:
            if hasattr(word, 'dependency_relation'):
                if word.dependency_relation in ['nsubj', 'nsubj:pass']:
                    analysis['subject_count'] += 1

            if hasattr(word, 'features') and word.features:
                case = word.features.get('Case')
                if case == 'Gen':
                    analysis['has_genitive'] = True
                if case == 'Dat':
                    analysis['has_dative'] = True

        # Determine complexity
        complexity_score = 0
        if analysis['subject_count'] > 1:
            complexity_score += 2
        if analysis['has_coordination']:
            complexity_score += 2
        if analysis['has_genitive'] and analysis['has_dative']:
            complexity_score += 1

        if complexity_score >= 4:
            analysis['complexity'] = 'complex'
        elif complexity_score >= 2:
            analysis['complexity'] = 'moderate'

        # Determine inscription type
        if analysis['has_main_verb']:
            analysis['inscription_type'] = 'dedication'
        elif analysis['has_genitive'] and analysis['has_dative']:
            analysis['inscription_type'] = 'epitaph'
        else:
            analysis['inscription_type'] = 'unknown'

        return analysis


def get_dependency_parser() -> LatinDependencyParser:
    """
    Get a singleton instance of the dependency parser.

    This avoids reloading CLTK models multiple times.
    """
    global _DEPENDENCY_PARSER
    if '_DEPENDENCY_PARSER' not in globals():
        _DEPENDENCY_PARSER = LatinDependencyParser()
    return _DEPENDENCY_PARSER
