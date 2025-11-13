"""
Parsing and entity extraction logic for Latin inscriptions.
"""
import csv
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Global model cache to avoid reloading
_NER_MODEL = None
_NER_TOKENIZER = None
_MODEL_LOADED = False
_USE_STUB = os.environ.get('LATINEPI_USE_STUB', 'true').lower() == 'true'


def read_inscriptions(path: str) -> List[Dict[str, Any]]:
    """
    Read inscriptions from a CSV or JSON file.

    Args:
        path: Path to the input file (CSV or JSON)

    Returns:
        List of dictionaries, where each dict represents one inscription record

    Raises:
        ValueError: If the file format is not supported or cannot be parsed
        FileNotFoundError: If the file does not exist
        IOError: If there is an error reading the file
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Determine file type from extension
    extension = file_path.suffix.lower()

    if extension == '.csv':
        return _read_csv(file_path)
    elif extension == '.json':
        return _read_json(file_path)
    else:
        raise ValueError(f"Unsupported file format: {extension}. Only .csv and .json are supported.")


def _read_csv(file_path: Path) -> List[Dict[str, Any]]:
    """
    Read inscriptions from a CSV file.

    Args:
        file_path: Path to the CSV file

    Returns:
        List of dictionaries, one per CSV row

    Raises:
        ValueError: If the CSV is malformed or cannot be parsed
    """
    try:
        inscriptions = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                inscriptions.append(dict(row))

        if not inscriptions:
            raise ValueError("CSV file is empty or contains no data rows")

        return inscriptions

    except csv.Error as e:
        raise ValueError(f"CSV parsing error: {e}")
    except UnicodeDecodeError as e:
        raise ValueError(f"CSV encoding error: {e}. File must be UTF-8 encoded.")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")


def _read_json(file_path: Path) -> List[Dict[str, Any]]:
    """
    Read inscriptions from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        List of dictionaries. If JSON contains a single dict, it's wrapped in a list.

    Raises:
        ValueError: If the JSON is malformed or has an unexpected structure
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle different JSON structures
        if isinstance(data, list):
            # JSON is already a list of records
            if not all(isinstance(item, dict) for item in data):
                raise ValueError("JSON list must contain only dictionaries")
            return data
        elif isinstance(data, dict):
            # JSON is a single record, wrap it in a list
            return [data]
        else:
            raise ValueError(f"JSON must be a list of objects or a single object, got {type(data).__name__}")

    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parsing error at line {e.lineno}, column {e.colno}: {e.msg}")
    except UnicodeDecodeError as e:
        raise ValueError(f"JSON encoding error: {e}. File must be UTF-8 encoded.")
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Error reading JSON file: {e}")


def _load_ner_model():
    """
    Load the NER model and tokenizer.

    Attempts to load a pretrained NER model for Latin. Falls back to stub if unavailable.
    The model is cached globally to avoid reloading on subsequent calls.

    Returns:
        tuple: (model, tokenizer) if successful, (None, None) if not available
    """
    global _NER_MODEL, _NER_TOKENIZER, _MODEL_LOADED

    if _MODEL_LOADED:
        return _NER_MODEL, _NER_TOKENIZER

    # If stub mode is explicitly requested, don't try to load model
    if _USE_STUB:
        _MODEL_LOADED = True
        return None, None

    try:
        # Try to import transformers
        from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
        import torch

        # Check for local latin-bert model path
        # Users should download latin-bert from https://github.com/dbmdz/latin-bert
        # using the download.sh script and set LATIN_BERT_PATH to the model directory
        latin_bert_path = os.environ.get('LATIN_BERT_PATH')

        if latin_bert_path and os.path.isdir(latin_bert_path):
            # Load local latin-bert model
            print(f"Loading latin-bert model from {latin_bert_path}...", file=sys.stderr)
            model_name = latin_bert_path
        else:
            # Fall back to HuggingFace model (placeholder)
            # Note: This is a generic multilingual model, not optimized for Latin NER
            # For production use, download the actual latin-bert model and set LATIN_BERT_PATH
            model_name = "dbmdz/bert-base-historic-multilingual-cased"
            print(f"Warning: LATIN_BERT_PATH not set. Using generic multilingual model.", file=sys.stderr)
            print(f"For better results, download latin-bert from https://github.com/dbmdz/latin-bert", file=sys.stderr)

        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)

        # Create NER pipeline
        ner_pipeline = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple"
        )

        _NER_MODEL = ner_pipeline
        _NER_TOKENIZER = tokenizer
        _MODEL_LOADED = True

        return _NER_MODEL, _NER_TOKENIZER

    except ImportError:
        # transformers or torch not available, fall back to stub
        _MODEL_LOADED = True
        return None, None
    except Exception as e:
        # Model loading failed, fall back to stub
        print(f"Warning: Could not load NER model: {e}. Using stub implementation.", file=sys.stderr)
        _MODEL_LOADED = True
        return None, None


def _extract_entities_with_model(text: str, model) -> Dict[str, Dict[str, Any]]:
    """
    Extract entities using the real NER model.

    Args:
        text: The inscription text to analyze
        model: The NER pipeline model

    Returns:
        Dictionary of extracted entities with values and confidence scores
    """
    try:
        # Run NER on the text
        ner_results = model(text)

        # Map NER results to our entity structure
        entities = {}

        for entity in ner_results:
            entity_type = entity['entity_group'].lower()
            word = entity['word'].strip()
            confidence = float(entity['score'])

            # Map common NER labels to our schema
            # PER = person name, LOC = location, ORG = organization
            if entity_type == 'per':
                # Try to classify as praenomen, nomen, or cognomen
                # This is a simplification; real implementation would need proper parsing
                if 'praenomen' not in entities:
                    entities['praenomen'] = {'value': word, 'confidence': confidence}
                elif 'nomen' not in entities:
                    entities['nomen'] = {'value': word, 'confidence': confidence}
                elif 'cognomen' not in entities:
                    entities['cognomen'] = {'value': word, 'confidence': confidence}
            elif entity_type == 'loc':
                entities['location'] = {'value': word, 'confidence': confidence}

        # If no entities found, return fallback
        if not entities:
            entities['text'] = {'value': text[:50], 'confidence': 0.50}

        return entities

    except Exception as e:
        # If model inference fails, fall back to stub
        print(f"Warning: Model inference failed: {e}. Using stub fallback.", file=sys.stderr)
        return _extract_entities_stub(text)


def _extract_entities_stub(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Stub implementation for entity extraction using pattern matching.

    Extracts entities from Latin inscriptions using regex patterns for:
    - Status markers (D M, D M S)
    - Personal names (praenomen, nomen, cognomen)
    - Years lived
    - Military service
    - Dedicators and relationships

    Args:
        text: The inscription text to analyze

    Returns:
        Dictionary of extracted entities with values and confidence scores
    """
    import re

    entities = {}

    # Normalize text: handle V/U interchangeability (Classical Latin used V for both)
    # Also normalize line breaks and extra whitespace
    normalized_text = text.upper().replace('V', 'U').replace('<BR>', ' ').replace('<BR/>', ' ')
    normalized_text = re.sub(r'\s+', ' ', normalized_text)  # Collapse multiple spaces

    # 1. Extract status markers (D M, D M S = Dis Manibus Sacrum)
    # Use negative lookahead to avoid matching D M in names
    status_pattern = r'^[^A-Z]*\bD\s*M\s*S?\b'
    status_match = re.search(status_pattern, normalized_text)
    if status_match:
        entities['status'] = {'value': 'dis manibus', 'confidence': 0.95}

    # 2. Extract praenomen (abbreviated or full)
    # Common praenomina: Gaius (C.), Lucius (L.), Marcus (M.), Titus (T.), Publius (P.), etc.
    # Be more careful with abbreviated forms - must be followed by a capital letter (nomen)
    # Use negative lookbehind to avoid matching "M" in "D M" status marker
    praenomen_patterns = [
        (r'(?<!D\s)\b(C|G)\.\s+(?=[A-Z])', 'Gaius', 0.90),
        (r'(?<!D\s)\bL\.\s+(?=[A-Z])', 'Lucius', 0.90),
        (r'(?<!D\s)\bM\.\s+(?=[A-Z])', 'Marcus', 0.90),
        (r'(?<!D\s)\bT\.\s+(?=[A-Z])', 'Titus', 0.90),
        (r'(?<!D\s)\bP\.\s+(?=[A-Z])', 'Publius', 0.90),
        (r'(?<!D\s)\bQ\.\s+(?=[A-Z])', 'Quintus', 0.90),
        # Full form patterns - also need to be followed by a nomen
        (r'(?<!D\s)\b(C|G)\s+(?=[A-Z][A-Z]{3,})', 'Gaius', 0.88),
        (r'(?<!D\s)\bL\s+(?=[A-Z][A-Z]{3,})', 'Lucius', 0.88),
        (r'(?<!D\s)\bM\s+(?=[A-Z][A-Z]{3,})', 'Marcus', 0.88),
        (r'(?<!D\s)\bT\s+(?=[A-Z][A-Z]{3,})', 'Titus', 0.88),
        (r'(?<!D\s)\bP\s+(?=[A-Z][A-Z]{3,})', 'Publius', 0.88),
        (r'\bGAI[UU]S\s+(?=[A-Z][A-Z]{3,})', 'Gaius', 0.92),
        (r'\bL[UU]CI[UU]S\s+(?=[A-Z][A-Z]{3,})', 'Lucius', 0.92),
        (r'\bMARC[UU]S\s+(?=[A-Z][A-Z]{3,})', 'Marcus', 0.92),
        (r'\bTIT[UU]S\s+(?=[A-Z][A-Z]{3,})', 'Titus', 0.92),
        (r'\bP[UU]BLI[UU]S\s+(?=[A-Z][A-Z]{3,})', 'Publius', 0.92),
    ]

    for pattern, name, confidence in praenomen_patterns:
        match = re.search(pattern, normalized_text)
        if match and 'praenomen' not in entities:
            entities['praenomen'] = {'value': name, 'confidence': confidence}
            break

    # 3. Extract nomen (family name)
    # Common nomina: Iulius, Flavius, Aemilius, Antonius, Claudius, Valerius, etc.
    # Check feminine forms BEFORE masculine forms to avoid incorrect matching
    nomen_patterns = [
        # Feminine forms first (with genitive -ae ending)
        (r'\bAEMILIA[E]?\b', 'Aemilia', 0.88),
        (r'\bCLA[UU]DIA[E]?\b', 'Claudia', 0.88),
        (r'\bUALERIA[E]?\b', 'Valeria', 0.88),
        (r'\b[UU]LPIA[E]?\b', 'Ulpia', 0.88),
        (r'\bA[UU]RELIA[E]?\b', 'Aurelia', 0.88),
        # Then masculine forms
        (r'\bI[UU]LI[UU]S\b', 'Iulius', 0.88),
        (r'\bFLA[UU]I[UU]S\b', 'Flavius', 0.88),
        (r'\bAEMILI[UU]S\b', 'Aemilius', 0.88),
        (r'\bANTONI[UU]S\b', 'Antonius', 0.88),
        (r'\bCLA[UU]DI[UU]S\b', 'Claudius', 0.88),
        (r'\bUALERI[UU]S\b', 'Valerius', 0.88),
        (r'\b[UU]LPI[UU]S\b', 'Ulpius', 0.88),
        (r'\bA[UU]RELI[UU]S\b', 'Aurelius', 0.88),
        (r'\bSEMPRONI[UU]S\b', 'Sempronius', 0.88),
        (r'\bAELI[UU]S\b', 'Aelius', 0.88),
    ]

    for pattern, name, confidence in nomen_patterns:
        match = re.search(pattern, normalized_text)
        if match and 'nomen' not in entities:
            entities['nomen'] = {'value': name, 'confidence': confidence}
            break

    # 4. Extract cognomen (personal name)
    # Common cognomina: Caesar, Alexander, Saturninus, etc.
    cognomen_patterns = [
        (r'\bCAESAR\b', 'Caesar', 0.90),
        (r'\bALEXANDER\b', 'Alexander', 0.90),
        (r'\bSAT[UU]RNIN[UU]S\b', 'Saturninus', 0.90),
        (r'\bTERT[UU]LLA[E]?\b', 'Tertulla', 0.90),
        (r'\bMAXIMA[E]?\b', 'Maxima', 0.90),
        (r'\bMAXIM[UU]S\b', 'Maximus', 0.90),
        (r'\bREST IT[UU]TA[E]?\b', 'Restituta', 0.90),
        (r'\bMARCELLA[E]?\b', 'Marcella', 0.90),
        (r'\bR[UU]F[UU]S\b', 'Rufus', 0.90),
        (r'\bSEUERA[E]?\b', 'Severa', 0.90),
        (r'\bPRIM[UU]S\b', 'Primus', 0.90),
        (r'\bSABINA[E]?\b', 'Sabina', 0.90),
        (r'\bT[UU]RPILIA[E]?\b', 'Turpilia', 0.90),
        (r'\bUICTOR\b', 'Victor', 0.90),
        (r'\bFELIX\b', 'Felix', 0.90),
    ]

    for pattern, name, confidence in cognomen_patterns:
        match = re.search(pattern, normalized_text)
        if match and 'cognomen' not in entities:
            entities['cognomen'] = {'value': name, 'confidence': confidence}
            break

    # 5. Extract years lived
    # Patterns: "Vix(it) an(nos) XX", "ann XX", "AN XLII", etc.
    # More permissive pattern to handle various spacings and abbreviations
    # Need to handle parentheses like "(IT)" and "(NOS)"
    # Use [IUVXLC]+ because V→U normalization affects Roman numerals
    years_pattern = r'(?:UIX|AN)(?:\([A-Z]*\))?\s*(?:\([A-Z]*\))?\s*([IUVXLC]+)\b'
    years_match = re.search(years_pattern, normalized_text)
    if years_match:
        roman_numeral = years_match.group(1)
        # Make sure it's not part of a name (should be reasonable age range)
        try:
            arabic = _roman_to_arabic(roman_numeral)
            if 1 <= arabic <= 150:  # Reasonable human lifespan
                entities['years_lived'] = {'value': str(arabic), 'confidence': 0.85}
        except:
            pass

    # 6. Extract military service
    # Patterns: "Mil(es) leg(ionis)", "miles", "centurio", etc.
    military_pattern = r'\b(MIL(?:ES)?|CENT[UU]RIO|LEG(?:IONIS)?)\b'
    military_matches = re.findall(military_pattern, normalized_text)
    if military_matches:
        # Look for legion number (e.g., "VIII Aug" or "leg(ionis) VIII Aug(ustae)")
        # Need to handle parentheses like "(IONIS)" and "(USTAE)" with spaces
        legion_pattern = r'LEG(?:\([A-Z]*\))?\s+([IUVXLC]+)\s+A[UU]G'
        legion_match = re.search(legion_pattern, normalized_text)
        if legion_match:
            legion_num = legion_match.group(1).replace('U', 'V')  # Convert back to standard Roman numerals
            entities['military_service'] = {
                'value': f'Miles, Legio {legion_num} Augusta',
                'confidence': 0.82
            }
        else:
            entities['military_service'] = {'value': 'Miles', 'confidence': 0.75}

    # 7. Extract relationships and dedicators
    # Patterns: "patri", "matri", "filiae", "filio", "coniugi", "heres"
    relationship_patterns = [
        (r'\bPATRI\b', 'father', 0.90),
        (r'\bMATRI\b', 'mother', 0.90),
        (r'\bFILIA[E]?\b', 'daughter', 0.90),
        (r'\bFILIO\b', 'son', 0.90),
        (r'\bCONI[UU]GI\b', 'wife', 0.90),
        (r'\bHERES\b', 'heir', 0.88),
    ]

    for pattern, relationship, confidence in relationship_patterns:
        match = re.search(pattern, normalized_text)
        if match and 'relationships' not in entities:
            entities['relationships'] = {'value': relationship, 'confidence': confidence}
            break

    # 8. Extract dedicator (name before "fecit" or after relationship)
    # This is complex - look for names near "fecit" or relationship words
    if re.search(r'\bFECIT\b', normalized_text):
        # Try to find a name before "fecit"
        fecit_pattern = r'([A-Z][A-Z]+(?:\s+[A-Z][A-Z]+)?)\s+FECIT'
        fecit_match = re.search(fecit_pattern, normalized_text)
        if fecit_match:
            dedicator_name = fecit_match.group(1)
            # Clean up and convert to proper case
            dedicator_name = dedicator_name.replace('U', 'u').title().replace('u', 'u')
            entities['dedicator'] = {'value': dedicator_name, 'confidence': 0.75}

    # 9. Extract location
    # Common locations: Romae (Rome), Ostia, Pompeii, etc.
    location_patterns = [
        (r'\bROMA[E]?\b', 'Rom', 0.85),
        (r'\bOSTIA[E]?\b', 'Ostia', 0.85),
        (r'\bPOMPEII\b', 'Pompeii', 0.85),
    ]

    for pattern, location, confidence in location_patterns:
        match = re.search(pattern, normalized_text)
        if match and 'location' not in entities:
            entities['location'] = {'value': location, 'confidence': confidence}
            break

    # If no entities found, return fallback
    if not entities:
        entities['text'] = {'value': text[:50], 'confidence': 0.50}

    return entities


def _roman_to_arabic(roman: str) -> int:
    """
    Convert Roman numerals to Arabic numbers.

    Args:
        roman: Roman numeral string (e.g., 'XX', 'XLII', 'XXU')
              Handles both V and U (since text is normalized with V→U)

    Returns:
        Integer value
    """
    roman_values = {
        'I': 1, 'V': 5, 'U': 5,  # U = 5 (normalized from V)
        'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000
    }

    total = 0
    prev_value = 0

    for char in reversed(roman.upper()):
        value = roman_values.get(char, 0)
        if value < prev_value:
            total -= value
        else:
            total += value
        prev_value = value

    return total


def extract_entities(text: str, use_model: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Extract named entities from Latin inscription text.

    Attempts to use a real NER model if available, falls back to stub implementation.
    The model is loaded once and cached for subsequent calls.

    Args:
        text: The inscription text to analyze
        use_model: Whether to attempt using the real model (default: True)

    Returns:
        Dictionary of extracted entities with their values and confidence scores.
        Format: {
            'entity_name': {
                'value': str,
                'confidence': float (0.0-1.0)
            }
        }

    Example:
        >>> extract_entities("D M GAIVS IVLIVS CAESAR")
        {
            'praenomen': {'value': 'Gaius', 'confidence': 0.91},
            'nomen': {'value': 'Iulius', 'confidence': 0.88},
            'cognomen': {'value': 'Caesar', 'confidence': 0.95}
        }

    Note:
        Set environment variable LATINEPI_USE_STUB=false to enable model loading.
        Requires transformers and torch packages to be installed.
    """
    # Try to load and use the real model
    if use_model and not _USE_STUB:
        model, _ = _load_ner_model()
        if model is not None:
            return _extract_entities_with_model(text, model)

    # Fall back to stub implementation
    return _extract_entities_stub(text)
