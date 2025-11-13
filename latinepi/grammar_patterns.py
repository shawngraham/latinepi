"""
Phase 1: Grammatical template pattern matching for Latin inscriptions.

This module extracts entities based on grammatical structure patterns rather than
just known name patterns. It leverages the highly formulaic nature of Roman inscriptions.
"""

import re
from typing import Dict, Any, List, Tuple


def extract_with_grammar_templates(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract entities using grammatical template patterns.

    This handles unknown names by recognizing structural patterns:
    - Genitive + relationship word → deceased person
    - Nominative + FECIT → dedicator
    - Patronymic patterns (X Y F. = X son of Y)
    - Tria nomina structure

    Args:
        text: The inscription text to analyze

    Returns:
        Dictionary of extracted entities with values and confidence scores
    """
    entities = {}

    # Normalize text
    normalized_text = text.upper().replace('V', 'U').replace('<BR>', ' ').replace('<BR/>', ' ')
    normalized_text = re.sub(r'\s+', ' ', normalized_text.strip())

    # Extract using various grammatical templates
    entities.update(_extract_genitive_relationships(normalized_text))
    entities.update(_extract_dedicator_patterns(normalized_text))
    entities.update(_extract_patronymic_patterns(normalized_text))
    entities.update(_extract_filiation_patterns(normalized_text))
    entities.update(_extract_age_relationship_patterns(normalized_text))
    entities.update(_extract_multiple_dedicators(normalized_text))

    return entities


def _extract_genitive_relationships(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract relationships using genitive + dative patterns.

    Pattern: [Name in genitive] [relationship word in dative]
    Examples:
    - VIBIAE SABINAE FILIAE → Vibia Sabina (daughter)
    - GAII IULII PATRI → Gaius Iulius (father)
    """
    entities = {}

    # Genitive feminine + dative relationship word
    # Pattern: NAME-AE NAME-AE FILIAE/MATRI/CONIVGI/SORORI
    relationship_words = {
        'FILIAE': ('daughter', 0.90),
        'MATRI': ('mother', 0.90),
        'CONI[UU]GI': ('wife', 0.88),
        'SORORI': ('sister', 0.88),
        'A[UU]IAE': ('grandmother', 0.85),
        'NEPOTI': ('granddaughter', 0.85),
    }

    for rel_word, (rel_value, rel_conf) in relationship_words.items():
        # Two-name genitive pattern (nomen + cognomen in genitive)
        pattern = r'\b([A-Z]+AE)\s+([A-Z]+AE)\s+' + rel_word + r'\b'
        match = re.search(pattern, text)
        if match and 'deceased_name' not in entities:
            name1 = match.group(1).replace('U', 'V')  # Convert back to standard
            name2 = match.group(2).replace('U', 'V')
            # Remove -AE, add -a, and capitalize properly (first letter upper, rest lower)
            name1_nom = name1[:-2].capitalize() + "a"
            name2_nom = name2[:-2].capitalize() + "a"
            entities['deceased_name'] = {
                'value': f"{name1_nom} {name2_nom}",
                'confidence': 0.82
            }
            entities['deceased_relationship'] = {
                'value': rel_value,
                'confidence': rel_conf
            }
            break

    # Genitive masculine + dative relationship word
    # Pattern: NAME-I NAME-I PATRI/FILIO/FRATRI
    relationship_words_masc = {
        'PATRI': ('father', 0.90),
        'FILIO': ('son', 0.90),
        'FRATRI': ('brother', 0.88),
        'A[UU]O': ('grandfather', 0.85),
        'NEPOTI': ('grandson', 0.85),
    }

    for rel_word, (rel_value, rel_conf) in relationship_words_masc.items():
        # Two-name genitive pattern
        pattern = r'\b([A-Z]+I)\s+([A-Z]+I)\s+' + rel_word + r'\b'
        match = re.search(pattern, text)
        if match and 'deceased_name' not in entities:
            name1 = match.group(1).replace('U', 'V')
            name2 = match.group(2).replace('U', 'V')
            # Genitive -i could be from -ius or -us, assume -ius (more common for nomina)
            entities['deceased_name'] = {
                'value': f"{name1[:-1]}us {name2[:-1]}us",  # Remove -I, add -us
                'confidence': 0.80
            }
            entities['deceased_relationship'] = {
                'value': rel_value,
                'confidence': rel_conf
            }
            break

    return entities


def _extract_dedicator_patterns(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract dedicators using FECIT/POSUIT/CURAVIT patterns.

    Pattern: [Name in nominative] FECIT/POSUIT
    Examples:
    - VIBIUS PAULUS FECIT → Vibius Paulus (dedicator)
    - MARCUS ANTONIUS POSUIT → Marcus Antonius (dedicator)
    """
    entities = {}

    # Common dedication verbs
    dedication_verbs = ['FECIT', 'FECERVNT', 'POS[UU]IT', 'POS[UU]ERVNT',
                        'C[UU]RA[UU]IT', 'C[UU]RA[UU]ERVNT']

    for verb in dedication_verbs:
        # Pattern: Nomen + Cognomen + PATER/MATER + FECIT (relationship before verb)
        pattern = r'\b([A-Z]+[UU]S)\s+([A-Z]+[UU]S)\s+(PATER|MATER|FILI[UU]S|FILIA|FRATER|SOROR|HERES)\s+' + verb + r'\b'
        match = re.search(pattern, text)
        if match and 'dedicator' not in entities:
            # Convert to proper case: U→v (for consonant v), then capitalize
            nomen = match.group(1).replace('U', 'v').lower().capitalize()
            cogn = match.group(2).replace('U', 'v').lower().capitalize()
            entities['dedicator'] = {
                'value': f"{nomen} {cogn}",
                'confidence': 0.85
            }
            # Don't break, relationship will be handled separately

        # Pattern: Praenomen (abbrev or full) + Nomen + Cognomen + VERB
        # Three-name pattern
        pattern = r'\b([A-Z]{1,3}\.?)\s+([A-Z]+[UU]S)\s+([A-Z]+[UU]S)\s+' + verb + r'\b'
        match = re.search(pattern, text)
        if match and 'dedicator' not in entities:
            praen = match.group(1)  # Keep abbreviations as-is (already uppercase)
            nomen = match.group(2).replace('U', 'v').lower().capitalize()
            cogn = match.group(3).replace('U', 'v').lower().capitalize()
            entities['dedicator'] = {
                'value': f"{praen} {nomen} {cogn}",
                'confidence': 0.85
            }
            break

        # Two-name pattern (nomen + cognomen)
        pattern = r'\b([A-Z]+[UU]S)\s+([A-Z]+[UU]S)\s+' + verb + r'\b'
        match = re.search(pattern, text)
        if match and 'dedicator' not in entities:
            nomen = match.group(1).replace('U', 'v').lower().capitalize()
            cogn = match.group(2).replace('U', 'v').lower().capitalize()
            entities['dedicator'] = {
                'value': f"{nomen} {cogn}",
                'confidence': 0.82
            }
            break

    # Check for relationship word before FECIT (e.g., PATER FECIT)
    relationship_before_fecit = {
        'PATER': ('father', 0.88),
        'MATER': ('mother', 0.88),
        'FILI[UU]S': ('son', 0.88),
        'FILIA': ('daughter', 0.88),
        'CONI[UU]X': ('spouse', 0.85),
        'FRATER': ('brother', 0.85),
        'SOROR': ('sister', 0.85),
        'HERES': ('heir', 0.88),
    }

    for rel_pattern, (rel_value, rel_conf) in relationship_before_fecit.items():
        pattern = r'\b' + rel_pattern + r'\s+(?:FECIT|POS[UU]IT|C[UU]RA[UU]IT)\b'
        match = re.search(pattern, text)
        if match and 'dedicator_relationship' not in entities:
            entities['dedicator_relationship'] = {
                'value': rel_value,
                'confidence': rel_conf
            }
            break

    return entities


def _extract_patronymic_patterns(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract patronymic patterns (X Y F. = X son of Y).

    Pattern: [Name] [Father's name in genitive] F(ILIUS/ILIA)
    Examples:
    - MARCUS GAII F. → Marcus son of Gaius
    - IULIA MARCI F. → Iulia daughter of Marcus
    """
    entities = {}

    # Pattern: NAME NAME-I F. (son/daughter of)
    pattern = r'\b([A-Z]+[UU]S)\s+([A-Z]+I)\s+F\.?\b'
    match = re.search(pattern, text)
    if match and 'patronymic' not in entities:
        name = match.group(1).replace('U', 'V')
        father_gen = match.group(2).replace('U', 'V')
        # Convert genitive to nominative (rough approximation)
        father = father_gen[:-1] + 'us'
        entities['patronymic'] = {
            'value': f"child of {father}",
            'confidence': 0.90
        }
        entities['father_name'] = {
            'value': father,
            'confidence': 0.85
        }

    return entities


def _extract_filiation_patterns(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract full filiation patterns (FILIUS/FILIA + father's name).

    Examples:
    - GAIUS IULIUS CAESARIS FILIUS → Gaius Iulius, son of Caesar
    """
    entities = {}

    # Pattern: NAME-IS/I FILIUS/FILIA
    pattern = r'\b([A-Z]+I(?:S)?)\s+FILI[UU]S\b'
    match = re.search(pattern, text)
    if match and 'father_name' not in entities:
        father_gen = match.group(1).replace('U', 'V')
        # Convert genitive to nominative
        if father_gen.endswith('IS'):
            father = father_gen[:-2] + 'is'  # Keep -is ending
        else:
            father = father_gen[:-1] + 'us'
        entities['father_name'] = {
            'value': father,
            'confidence': 0.88
        }
        entities['filiation'] = {
            'value': 'son',
            'confidence': 0.92
        }

    pattern = r'\b([A-Z]+I(?:S)?)\s+FILIA\b'
    match = re.search(pattern, text)
    if match and 'father_name' not in entities:
        father_gen = match.group(1).replace('U', 'V')
        if father_gen.endswith('IS'):
            father = father_gen[:-2] + 'is'
        else:
            father = father_gen[:-1] + 'us'
        entities['father_name'] = {
            'value': father,
            'confidence': 0.88
        }
        entities['filiation'] = {
            'value': 'daughter',
            'confidence': 0.92
        }

    return entities


def _extract_age_relationship_patterns(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract patterns combining age with relationships.

    Examples:
    - VIXIT ANNIS XXV FILIO CARISSIMO
    """
    entities = {}

    # Pattern: relationship adjectives (carissimo/a/ae, piissimo/a/ae, dulcissimo/a/ae)
    relationship_adjectives = {
        'CARISSIM[AOE]+': ('dearest', 0.75),
        'PIISSIM[AOE]+': ('most devoted', 0.75),
        'D[UU]LCISSIM[AOE]+': ('sweetest', 0.75),
        'BENE\s+MERENTI': ('well-deserving', 0.75),
        'INCOMPARABILI': ('incomparable', 0.75),
    }

    for adj_pattern, (adj_value, adj_conf) in relationship_adjectives.items():
        pattern = r'\b' + adj_pattern + r'\b'
        match = re.search(pattern, text)
        if match and 'dedication_sentiment' not in entities:
            entities['dedication_sentiment'] = {
                'value': adj_value,
                'confidence': adj_conf
            }
            break

    return entities


def _extract_multiple_dedicators(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract patterns with multiple dedicators (ET pattern).

    Examples:
    - VIBIUS PAULUS PATER ET VIBIA TERTULLA MATER FECERUNT
    """
    entities = {}

    # Pattern: NAME ET NAME FECERUNT
    pattern = r'\b([A-Z]+[UU]S)\s+([A-Z]+[UU]S)\s+([A-Z]+)\s+ET\s+([A-Z]+)\s+([A-Z]+)\s+([A-Z]+)\s+FECERVNT\b'
    match = re.search(pattern, text)
    if match:
        name1_1 = match.group(1).replace('U', 'V')
        name1_2 = match.group(2).replace('U', 'V')
        rel1 = match.group(3).replace('U', 'V')
        name2_1 = match.group(4).replace('U', 'V')
        name2_2 = match.group(5).replace('U', 'V')
        rel2 = match.group(6).replace('U', 'V')

        entities['dedicator_1'] = {
            'value': f"{name1_1} {name1_2}",
            'confidence': 0.80
        }
        entities['dedicator_1_relationship'] = {
            'value': rel1.lower(),
            'confidence': 0.85
        }
        entities['dedicator_2'] = {
            'value': f"{name2_1} {name2_2}",
            'confidence': 0.80
        }
        entities['dedicator_2_relationship'] = {
            'value': rel2.lower(),
            'confidence': 0.85
        }
        entities['multiple_dedicators'] = {
            'value': 'true',
            'confidence': 0.90
        }

    return entities


def extract_unknown_names_by_position(text: str) -> List[Tuple[str, str, float]]:
    """
    Extract potential unknown names based on structural position.

    Returns list of (name, position_type, confidence) tuples.
    Position types: 'subject', 'object_genitive', 'dedicator', etc.
    """
    names = []
    normalized_text = text.upper().replace('V', 'U')

    # Extract capitalized word sequences that look like names
    # (2-3 consecutive capitalized words not matching known formula words)
    formula_words = {
        'D', 'M', 'S', 'FECIT', 'FECERVNT', 'POSUIT', 'POSUERUNT',
        'VIXIT', 'ANNIS', 'ANNOS', 'PATER', 'MATER', 'FILIUS', 'FILIA',
        'PATRI', 'MATRI', 'FILIO', 'FILIAE', 'CONIUGI', 'HERES',
        'LEG', 'LEGIONIS', 'MIL', 'MILES', 'CENTURIO', 'ET'
    }

    # Find sequences of 2-3 capitalized words
    words = re.findall(r'\b[A-Z]+\b', normalized_text)

    for i in range(len(words) - 1):
        # Two-word name pattern
        if words[i] not in formula_words and words[i+1] not in formula_words:
            # Check if they look like names (ending in typical name endings)
            if (re.search(r'[UU]S$|[AE]$|[UU]M$', words[i]) and
                re.search(r'[UU]S$|[AE]$|[UU]M$', words[i+1])):
                name = f"{words[i]} {words[i+1]}".replace('U', 'V')
                # Determine position type by context
                position = 'unknown'
                confidence = 0.60

                # Check if before FECIT → likely dedicator
                if i+2 < len(words) and words[i+2] in ['FECIT', 'FECERVNT', 'POSUIT']:
                    position = 'dedicator'
                    confidence = 0.75
                # Check if genitive ending → likely deceased
                elif words[i].endswith(('I', 'AE')) and words[i+1].endswith(('I', 'AE')):
                    position = 'deceased_genitive'
                    confidence = 0.70

                names.append((name, position, confidence))

    return names
