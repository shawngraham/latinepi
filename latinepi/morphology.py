"""
Phase 2: Morphological analysis using CLTK for Latin inscriptions.

This module uses the Classical Language Toolkit to analyze Latin morphology,
identifying grammatical cases, genders, and numbers to extract entities even
when names are unknown.
"""

import re
from typing import Dict, Any, List, Tuple, Optional


class LatinMorphologyAnalyzer:
    """
    Morphological analyzer using CLTK for Latin inscriptions.

    Uses part-of-speech tagging and morphological features to identify:
    - Case (nominative, genitive, dative, accusative, ablative)
    - Gender (masculine, feminine, neuter)
    - Number (singular, plural)
    - Proper nouns vs common nouns
    """

    def __init__(self):
        """Initialize the CLTK analyzer."""
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
                "CLTK is required for morphological analysis. "
                "Install with: pip install cltk"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize CLTK: {e}")

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze inscription text using morphological features.

        Args:
            text: The inscription text to analyze

        Returns:
            Dictionary containing morphological analysis results
        """
        self._ensure_initialized()

        # Normalize text for CLTK
        normalized_text = text.replace('<BR>', ' ').replace('<BR/>', ' ')
        normalized_text = re.sub(r'\s+', ' ', normalized_text.strip())

        try:
            doc = self._nlp.analyze(text=normalized_text)
            return {
                'words': doc.words,
                'sentences': doc.sentences,
                'raw': doc
            }
        except Exception as e:
            # Return empty analysis if CLTK fails
            return {
                'words': [],
                'sentences': [],
                'error': str(e)
            }

    def extract_entities_by_morphology(self, text: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract entities based on morphological analysis.

        Uses grammatical features to identify:
        - Genitive proper nouns → deceased persons
        - Nominative proper nouns before FECIT → dedicators
        - Dative common nouns → relationships
        - etc.

        Args:
            text: The inscription text to analyze

        Returns:
            Dictionary of extracted entities with confidence scores
        """
        entities = {}
        analysis = self.analyze_text(text)

        if 'error' in analysis or not analysis['words']:
            return entities

        words = analysis['words']

        # Extract entities using morphological rules
        entities.update(self._extract_genitive_proper_nouns(words))
        entities.update(self._extract_nominative_subjects(words, text))
        entities.update(self._extract_dative_relationships(words))
        entities.update(self._extract_ablative_locations(words))

        return entities

    def _extract_genitive_proper_nouns(self, words: List[Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract genitive proper nouns (likely deceased persons).

        Genitive case typically indicates possession or relationship.
        In inscriptions, genitive proper nouns usually refer to the deceased.
        """
        entities = {}
        genitive_names = []

        for word in words:
            # Check if word has morphological features
            if not hasattr(word, 'features') or not word.features:
                continue

            features = word.features

            # Look for genitive case proper nouns
            if (features.get('Case') == 'Gen' and
                hasattr(word, 'pos') and word.pos in ['PROPN', 'NOUN']):

                # Store genitive name
                genitive_names.append(word.string)

        # If we found genitive proper nouns, combine them
        if genitive_names:
            deceased_name = ' '.join(genitive_names[:3])  # Max 3 names (tria nomina)
            entities['deceased_name_morphology'] = {
                'value': deceased_name,
                'confidence': 0.85,
                'source': 'morphology',
                'case': 'genitive'
            }

        return entities

    def _extract_nominative_subjects(self, words: List[Any], text: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract nominative subjects (likely dedicators if before FECIT).

        Nominative case indicates the subject. In dedications, nominative
        proper nouns before FECIT/POSUIT are the dedicators.
        """
        entities = {}
        nominative_names = []
        found_dedication_verb = False

        # Check if text contains dedication verbs
        dedication_verbs = ['FECIT', 'FECERUNT', 'POSUIT', 'POSUERUNT',
                           'CURAVIT', 'CURAVERUNT']
        text_upper = text.upper()
        for verb in dedication_verbs:
            if verb in text_upper:
                found_dedication_verb = True
                break

        if not found_dedication_verb:
            return entities

        for word in words:
            if not hasattr(word, 'features') or not word.features:
                continue

            features = word.features

            # Look for nominative case proper nouns
            if (features.get('Case') == 'Nom' and
                hasattr(word, 'pos') and word.pos in ['PROPN', 'NOUN']):

                nominative_names.append(word.string)

        # If we found nominative proper nouns and a dedication verb
        if nominative_names and found_dedication_verb:
            dedicator_name = ' '.join(nominative_names[:3])
            entities['dedicator_morphology'] = {
                'value': dedicator_name,
                'confidence': 0.82,
                'source': 'morphology',
                'case': 'nominative'
            }

        return entities

    def _extract_dative_relationships(self, words: List[Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract dative relationship words.

        Dative case indicates the indirect object (to/for whom).
        Common in inscriptions: PATRI (to father), FILIAE (to daughter), etc.
        """
        entities = {}

        # Map lemmas to relationship values
        relationship_lemmas = {
            'pater': ('father', 0.92),
            'mater': ('mother', 0.92),
            'filius': ('son', 0.92),
            'filia': ('daughter', 0.92),
            'coniunx': ('spouse', 0.90),
            'uxor': ('wife', 0.90),
            'maritus': ('husband', 0.90),
            'frater': ('brother', 0.88),
            'soror': ('sister', 0.88),
            'avus': ('grandfather', 0.88),
            'avia': ('grandmother', 0.88),
            'nepos': ('grandson', 0.88),
            'neptis': ('granddaughter', 0.88),
            'heres': ('heir', 0.90),
        }

        for word in words:
            if not hasattr(word, 'features') or not word.features:
                continue

            features = word.features

            # Look for dative case
            if features.get('Case') == 'Dat':
                # Check if lemma matches known relationships
                if hasattr(word, 'lemma') and word.lemma:
                    lemma = word.lemma.lower()
                    if lemma in relationship_lemmas:
                        rel_value, confidence = relationship_lemmas[lemma]
                        entities['relationship_morphology'] = {
                            'value': rel_value,
                            'confidence': confidence,
                            'source': 'morphology',
                            'case': 'dative',
                            'lemma': lemma
                        }
                        break

        return entities

    def _extract_ablative_locations(self, words: List[Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract ablative locations.

        Ablative case can indicate location (where something happened).
        Often used for place names in inscriptions.
        """
        entities = {}
        ablative_places = []

        for word in words:
            if not hasattr(word, 'features') or not word.features:
                continue

            features = word.features

            # Look for ablative case proper nouns (places)
            if (features.get('Case') == 'Abl' and
                hasattr(word, 'pos') and word.pos == 'PROPN'):

                ablative_places.append(word.string)

        if ablative_places:
            location = ' '.join(ablative_places)
            entities['location_morphology'] = {
                'value': location,
                'confidence': 0.75,
                'source': 'morphology',
                'case': 'ablative'
            }

        return entities

    def get_case_analysis(self, text: str) -> List[Dict[str, Any]]:
        """
        Get detailed case analysis for each word.

        Returns:
            List of dictionaries with word, lemma, pos, case, gender, number
        """
        analysis = self.analyze_text(text)
        result = []

        if 'error' in analysis or not analysis['words']:
            return result

        for word in analysis['words']:
            word_info = {
                'word': word.string if hasattr(word, 'string') else str(word),
                'lemma': word.lemma if hasattr(word, 'lemma') else None,
                'pos': word.pos if hasattr(word, 'pos') else None,
                'case': None,
                'gender': None,
                'number': None,
            }

            if hasattr(word, 'features') and word.features:
                features = word.features
                word_info['case'] = features.get('Case')
                word_info['gender'] = features.get('Gender')
                word_info['number'] = features.get('Number')

            result.append(word_info)

        return result

    def validate_entity_with_morphology(
        self,
        entity_text: str,
        expected_case: str
    ) -> Tuple[bool, float]:
        """
        Validate an extracted entity against expected morphological features.

        Args:
            entity_text: The entity text to validate
            expected_case: Expected grammatical case (Nom, Gen, Dat, Acc, Abl)

        Returns:
            Tuple of (is_valid, confidence_adjustment)
        """
        analysis = self.analyze_text(entity_text)

        if 'error' in analysis or not analysis['words']:
            return (False, 0.0)

        # Check if any word matches expected case
        for word in analysis['words']:
            if not hasattr(word, 'features') or not word.features:
                continue

            if word.features.get('Case') == expected_case:
                return (True, 0.10)  # Boost confidence by 10%

        return (False, -0.10)  # Reduce confidence by 10%


def get_morphology_analyzer() -> LatinMorphologyAnalyzer:
    """
    Get a singleton instance of the morphology analyzer.

    This avoids reloading CLTK models multiple times.
    """
    global _MORPHOLOGY_ANALYZER
    if '_MORPHOLOGY_ANALYZER' not in globals():
        _MORPHOLOGY_ANALYZER = LatinMorphologyAnalyzer()
    return _MORPHOLOGY_ANALYZER
