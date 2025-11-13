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
    Stub implementation for entity extraction (pattern-based).

    This simulates NER results using simple pattern matching.
    Used as fallback when real model is unavailable.

    Args:
        text: The inscription text to analyze

    Returns:
        Dictionary of extracted entities with values and confidence scores
    """
    # Generate mock entities based on text content patterns
    entities = {}

    text_upper = text.upper()

    # Mock praenomen extraction
    if 'GAIVS' in text_upper or 'GAIUS' in text_upper:
        entities['praenomen'] = {'value': 'Gaius', 'confidence': 0.91}
    elif 'MARCVS' in text_upper or 'MARCUS' in text_upper:
        entities['praenomen'] = {'value': 'Marcus', 'confidence': 0.89}
    elif 'LVCIVS' in text_upper or 'LUCIUS' in text_upper:
        entities['praenomen'] = {'value': 'Lucius', 'confidence': 0.87}

    # Mock nomen extraction
    if 'IVLIVS' in text_upper or 'IULIUS' in text_upper:
        entities['nomen'] = {'value': 'Iulius', 'confidence': 0.88}
    elif 'CORNELIVS' in text_upper or 'CORNELIUS' in text_upper:
        entities['nomen'] = {'value': 'Cornelius', 'confidence': 0.92}
    elif 'ANTONIVS' in text_upper or 'ANTONIUS' in text_upper:
        entities['nomen'] = {'value': 'Antonius', 'confidence': 0.90}

    # Mock cognomen extraction
    if 'CAESAR' in text_upper:
        entities['cognomen'] = {'value': 'Caesar', 'confidence': 0.95}
    elif 'TVRPILIA' in text_upper or 'TURPILIA' in text_upper:
        entities['cognomen'] = {'value': 'Turpilia', 'confidence': 0.86}
    elif 'CICERO' in text_upper:
        entities['cognomen'] = {'value': 'Cicero', 'confidence': 0.93}

    # Mock status/formula extraction
    if 'D M' in text_upper or 'DIS MANIBVS' in text_upper:
        entities['status'] = {'value': 'dis manibus', 'confidence': 0.98}

    # Mock location extraction
    if 'ROM' in text_upper:
        entities['location'] = {'value': 'Roma', 'confidence': 0.82}
    elif 'POMPEI' in text_upper:
        entities['location'] = {'value': 'Pompeii', 'confidence': 0.85}

    # If no entities were found, provide at least a basic extracted text entity
    if not entities:
        entities['text'] = {'value': text[:50], 'confidence': 0.50}

    return entities


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
