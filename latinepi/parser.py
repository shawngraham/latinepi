"""
Parsing and entity extraction logic for Latin inscriptions.
"""
import csv
import json
from pathlib import Path
from typing import List, Dict, Any


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


def extract_entities(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract named entities from Latin inscription text.

    This is a stub implementation that returns hardcoded mock data
    to simulate NER results. In a future version, this will use the
    latin-bert model for real entity extraction.

    Args:
        text: The inscription text to analyze

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
    """
    # Stub implementation: return mock entity data
    # This simulates what a real NER model would return

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
