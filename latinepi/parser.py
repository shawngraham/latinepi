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


def _extract_entities_stub(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Pattern-based entity extraction for Latin inscriptions.

    Extracts entities using comprehensive regex patterns for:
    - Status markers (D M, D M S = Dis Manibus Sacrum)
    - Personal names:
      * Praenomina: Gaius, Marcus, Lucius, Titus, Publius, Quintus, Sextus, etc.
      * Nomina: Iulius, Flavius, Cornelius, Aemilius, Antonius, etc. (40+ families)
      * Cognomina: Caesar, Maximus, Primus, Secundus, Felix, etc. (50+ names)
    - Years lived (Roman numeral to Arabic conversion)
    - Military service (Miles, Centurio, Legion numbers)
    - Relationships (father, mother, daughter, son, wife, heir)
    - Dedicators (names before "fecit")
    - Cities (Rome, Pompeii, Ostia, Aquincum, etc.)
    - Tribes (Fabia, Cornelia, Palatina, Quirina, etc.)

    Handles:
    - V/U interchangeability in Classical Latin
    - HTML line breaks (<br>)
    - Parenthetical abbreviations (e.g., "Vix(it) an(nos) XX")
    - Masculine and feminine declensions
    - Abbreviated and full forms of names

    Args:
        text: The inscription text to analyze

    Returns:
        Dictionary of extracted entities with values and confidence scores (0.75-0.95)
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
        (r'(?<!D\s)\bSEX\.\s+(?=[A-Z])', 'Sextus', 0.90),
        (r'(?<!D\s)\bA\.\s+(?=[A-Z])', 'Aulus', 0.88),
        (r'(?<!D\s)\bD\.\s+(?=[A-Z])', 'Decimus', 0.88),
        (r'(?<!D\s)\bCN\.\s+(?=[A-Z])', 'Gnaeus', 0.90),
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
        (r'\bQ[UU]INT[UU]S\s+(?=[A-Z][A-Z]{3,})', 'Quintus', 0.92),
        (r'\bSEXT[UU]S\s+(?=[A-Z][A-Z]{3,})', 'Sextus', 0.92),
        (r'\bA[UU]L[UU]S\s+(?=[A-Z][A-Z]{3,})', 'Aulus', 0.90),
        (r'\bDECIM[UU]S\s+(?=[A-Z][A-Z]{3,})', 'Decimus', 0.90),
        (r'\bGNAE[UU]S\s+(?=[A-Z][A-Z]{3,})', 'Gnaeus', 0.92),
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
        (r'\bCORNELIA[E]?\b', 'Cornelia', 0.88),
        (r'\bI[UU]LIA[E]?\b', 'Iulia', 0.88),
        (r'\bFLA[UU]IA[E]?\b', 'Flavia', 0.88),
        (r'\bFABIA[E]?\b', 'Fabia', 0.88),
        (r'\bDOMITIA[E]?\b', 'Domitia', 0.88),
        (r'\bLICINIA[E]?\b', 'Licinia', 0.88),
        (r'\bI[UU]NIA[E]?\b', 'Iunia', 0.88),
        (r'\bCAECILIA[E]?\b', 'Caecilia', 0.88),
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
        (r'\bCORNELI[UU]S\b', 'Cornelius', 0.88),
        (r'\bFABI[UU]S\b', 'Fabius', 0.88),
        (r'\bDOMITI[UU]S\b', 'Domitius', 0.88),
        (r'\bLICINI[UU]S\b', 'Licinius', 0.88),
        (r'\bI[UU]NI[UU]S\b', 'Iunius', 0.88),
        (r'\bCAECILI[UU]S\b', 'Caecilius', 0.88),
        (r'\bPOMPEI[UU]S\b', 'Pompeius', 0.88),
        (r'\bSERUILI[UU]S\b', 'Servilius', 0.88),
        (r'\bTEREHTI[UU]S\b', 'Terentius', 0.88),
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
        (r'\bMARCELL[UU]S\b', 'Marcellus', 0.90),
        (r'\bR[UU]F[UU]S\b', 'Rufus', 0.90),
        (r'\bR[UU]FA[E]?\b', 'Rufa', 0.90),
        (r'\bSEUERA[E]?\b', 'Severa', 0.90),
        (r'\bSEUER[UU]S\b', 'Severus', 0.90),
        (r'\bPRIM[UU]S\b', 'Primus', 0.90),
        (r'\bPRIMA[E]?\b', 'Prima', 0.90),
        (r'\bSEC[UU]ND[UU]S\b', 'Secundus', 0.90),
        (r'\bSEC[UU]NDA[E]?\b', 'Secunda', 0.90),
        (r'\bTERTI[UU]S\b', 'Tertius', 0.90),
        (r'\bTERTIA[E]?\b', 'Tertia', 0.90),
        (r'\bQ[UU]ART[UU]S\b', 'Quartus', 0.90),
        (r'\bQ[UU]ARTA[E]?\b', 'Quarta', 0.90),
        (r'\bQ[UU]INT[UU]S\b', 'Quintus', 0.90),
        (r'\bQ[UU]INTA[E]?\b', 'Quinta', 0.90),
        (r'\bSABINA[E]?\b', 'Sabina', 0.90),
        (r'\bSABIN[UU]S\b', 'Sabinus', 0.90),
        (r'\bT[UU]RPILIA[E]?\b', 'Turpilia', 0.90),
        (r'\bUICTOR\b', 'Victor', 0.90),
        (r'\bUICTORIA[E]?\b', 'Victoria', 0.90),
        (r'\bFELIX\b', 'Felix', 0.90),
        (r'\bFAUSTINA[E]?\b', 'Faustina', 0.90),
        (r'\bFA[UU]ST[UU]S\b', 'Faustus', 0.90),
        (r'\bCLEMENS\b', 'Clemens', 0.90),
        (r'\bCRISP[UU]S\b', 'Crispus', 0.90),
        (r'\bCRISPINA[E]?\b', 'Crispina', 0.90),
        (r'\bFRONTO\b', 'Fronto', 0.90),
        (r'\bGALL[UU]S\b', 'Gallus', 0.90),
        (r'\bLONG[UU]S\b', 'Longus', 0.90),
        (r'\bLONGINA[E]?\b', 'Longina', 0.90),
        (r'\bNIGER\b', 'Niger', 0.90),
        (r'\bPAUL[UU]S\b', 'Paulus', 0.90),
        (r'\bPA[UU]LA[E]?\b', 'Paula', 0.90),
        (r'\bPRISC[UU]S\b', 'Priscus', 0.90),
        (r'\bPRISCA[E]?\b', 'Prisca', 0.90),
        (r'\bREGINA[E]?\b', 'Regina', 0.90),
        (r'\bREGINO\b', 'Reginus', 0.90),
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

    # 9. Extract location/city
    # Common locations: Romae (Rome), Ostia, Pompeii, etc.
    location_patterns = [
        (r'\bROMA[E]?\b', 'Rom', 0.85),
        (r'\bOSTIA[E]?\b', 'Ostia', 0.85),
        (r'\bPOMPEII\b', 'Pompeii', 0.85),
        (r'\bNEAPOLI\b', 'Neapolis', 0.85),
        (r'\bAQ[UU]INCI\b', 'Aquincum', 0.85),
        (r'\bCART HAGINE\b', 'Carthage', 0.85),
        (r'\bL[UU]GD[UU]NI\b', 'Lugdunum', 0.85),
        (r'\bMEDIOLANI\b', 'Mediolanum', 0.85),
        (r'\bRAUENNA[E]?\b', 'Ravenna', 0.85),
        (r'\bTARRACO\b', 'Tarraco', 0.85),
    ]

    for pattern, location, confidence in location_patterns:
        match = re.search(pattern, normalized_text)
        if match and 'location' not in entities:
            entities['location'] = {'value': location, 'confidence': confidence}
            break

    # 10. Extract tribe (Roman voting tribes)
    # All 35 Roman voting tribes: 4 urban + 31 rural
    # Tribes are usually abbreviated, e.g., "Fab." for Fabia
    # Note: V→U normalization affects patterns (VEL→UEL, VET→UET, VOL→UOL)
    # Abbreviated patterns end with \. not \.\b (period is not a word char)
    tribe_patterns = [
        # Urban Tribes (4)
        (r'\bCOLL\.', 'Collina', 0.85),
        (r'\bCOLLINA\b', 'Collina', 0.88),
        (r'\bESQ\.', 'Esquilina', 0.85),
        (r'\bESQ[UU]ILINA\b', 'Esquilina', 0.88),
        (r'\bPAL\.', 'Palatina', 0.85),
        (r'\bPALATINA\b', 'Palatina', 0.88),
        (r'\bSUB\.', 'Suburana', 0.85),
        (r'\bS[UU]B[UU]RANA\b', 'Suburana', 0.88),

        # Rural Tribes (31)
        (r'\bAEM\.', 'Aemilia', 0.85),
        (r'\bAEMILIA\b', 'Aemilia', 0.88),
        (r'\bANI\.', 'Aniensis', 0.85),
        (r'\bANIENSIS\b', 'Aniensis', 0.88),
        (r'\bARN\.', 'Arnensis', 0.85),
        (r'\bARNENSIS\b', 'Arnensis', 0.88),
        (r'\bCAM\.', 'Camilia', 0.85),
        (r'\bCAMILIA\b', 'Camilia', 0.88),
        (r'\bCLA\.', 'Claudia', 0.85),
        (r'\bCLA[UU]DIA\b', 'Claudia', 0.88),
        (r'\bCL[UU]ST\.', 'Clustumina', 0.85),
        (r'\bCL[UU]ST[UU]MINA\b', 'Clustumina', 0.88),
        (r'\bCORN\.', 'Cornelia', 0.85),
        (r'\bCORNELIA\b', 'Cornelia', 0.88),
        (r'\bFAB\.', 'Fabia', 0.85),
        (r'\bFABIA\b', 'Fabia', 0.88),
        (r'\bGAL\.', 'Galeria', 0.85),
        (r'\bGALERIA\b', 'Galeria', 0.88),
        (r'\bHOR\.', 'Horatia', 0.85),
        (r'\bHORATIA\b', 'Horatia', 0.88),
        (r'\bLEM\.', 'Lemonia', 0.85),
        (r'\bLEMONIA\b', 'Lemonia', 0.88),
        (r'\bMAE\.', 'Maecia', 0.85),
        (r'\bMAECIA\b', 'Maecia', 0.88),
        (r'\bMEN\.', 'Menenia', 0.85),
        (r'\bMENENIA\b', 'Menenia', 0.88),
        (r'\bOUF\.', 'Oufentina', 0.85),
        (r'\bO[UU]FENTINA\b', 'Oufentina', 0.88),
        (r'\bUFE\.', 'Oufentina', 0.85),
        (r'\b[UU]FENTINA\b', 'Oufentina', 0.88),
        (r'\bPAP\.', 'Papiria', 0.85),
        (r'\bPAPIRIA\b', 'Papiria', 0.88),
        (r'\bPOL\.', 'Pollia', 0.85),
        (r'\bPOLLIA\b', 'Pollia', 0.88),
        (r'\bPOM\.', 'Pomptina', 0.85),
        (r'\bPOMPTINA\b', 'Pomptina', 0.88),
        (r'\bPUB\.', 'Publilia', 0.85),
        (r'\bP[UU]BLILIA\b', 'Publilia', 0.88),
        (r'\bPUP\.', 'Pupinia', 0.85),
        (r'\bP[UU]PINIA\b', 'Pupinia', 0.88),
        (r'\bQUIR\.', 'Quirina', 0.85),
        (r'\bQ[UU]IRINA\b', 'Quirina', 0.88),
        (r'\bROM\.', 'Romilia', 0.85),
        (r'\bROMILIA\b', 'Romilia', 0.88),
        (r'\bSAB\.', 'Sabatina', 0.85),
        (r'\bSABATINA\b', 'Sabatina', 0.88),
        (r'\bSABINA\b', 'Sabatina', 0.88),
        (r'\bSCA\.', 'Scaptia', 0.85),
        (r'\bSCAPTIA\b', 'Scaptia', 0.88),
        (r'\bSER\.', 'Sergia', 0.85),
        (r'\bSERGIA\b', 'Sergia', 0.88),
        (r'\bSTE\.', 'Stellatina', 0.85),
        (r'\bSTELLATINA\b', 'Stellatina', 0.88),
        (r'\bTER\.', 'Teretina', 0.85),
        (r'\bTERETINA\b', 'Teretina', 0.88),
        (r'\bTERENTINA\b', 'Teretina', 0.88),
        (r'\bTRO\.', 'Tromentina', 0.85),
        (r'\bTROMENTINA\b', 'Tromentina', 0.88),
        (r'\bUEL\.', 'Velina', 0.85),  # VEL→UEL due to V→U normalization
        (r'\bUELINA\b', 'Velina', 0.88),
        (r'\bUET\.', 'Veturia', 0.85),  # VET→UET due to V→U normalization
        (r'\bUET[UU]RIA\b', 'Veturia', 0.88),
        (r'\bUOL\.', 'Voltinia', 0.85),  # VOL→UOL due to V→U normalization
        (r'\bUOLTINIA\b', 'Voltinia', 0.88),
        (r'\bUOT[UU]RIA\b', 'Voltinia', 0.88),
    ]

    for pattern, tribe, confidence in tribe_patterns:
        match = re.search(pattern, normalized_text)
        if match and 'tribe' not in entities:
            entities['tribe'] = {'value': tribe, 'confidence': confidence}
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


def extract_entities(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract named entities from Latin inscription text using pattern matching.

    Uses comprehensive regex patterns to identify and extract entities including:
    - Personal names (praenomen, nomen, cognomen)
    - Status markers (D M, D M S)
    - Years lived
    - Military service and legion numbers
    - Relationships (father, mother, daughter, son, wife, heir)
    - Locations (Rome, Pompeii, Ostia)

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
            'status': {'value': 'dis manibus', 'confidence': 0.95},
            'praenomen': {'value': 'Gaius', 'confidence': 0.92},
            'nomen': {'value': 'Iulius', 'confidence': 0.88},
            'cognomen': {'value': 'Caesar', 'confidence': 0.90}
        }
    """
    return _extract_entities_stub(text)
