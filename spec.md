# Latin Epigraphic CLI Specification

## Overview

A Python command-line tool for extracting structured personal data from Roman Latin epigraphic inscriptions (e.g., gravestones) in CSV or JSON format. Utilizes the pretrained `latin-bert` model to identify and extract various prosopographical entities, with confidence scores and ambiguity handling. Includes an optional utility for downloading inscription data and metadata from the EDH API.

---

## Features

- **Input:** Accept CSV or JSON files with inscription text.
- **Extraction:** Parse and extract:
  - Praenomen
  - Nomen
  - Cognomen
  - Tribe
  - Filiation (mother/father)
  - Occupation
  - Status (citizenship, social rank)
  - Gender
  - Age at death
  - Military service
  - Location
- **Confidence Scores:** Each extracted entity includes a model-generated confidence score.
- **Ambiguity Handling:** Entities below a user-specified confidence threshold can be *flagged* as ambiguous or *omitted*, as specified via CLI flag.
- **Output:** Structured, flat records in JSON or CSV format (matching input mode).
- **EDH Download Utility:** Download inscription text and metadata by ID from the EDH API into a user-specified folder.
- **Tests:** Comes with unit and CLI-level tests.
- **Error Handling:** All errors and warnings reported to stderr.
- **Help:** Usage help via `--help` flag.

---

## Command-Line Options

**Single-command entry point:** `latinepi`

### Input/Output
- `--input <input_file>`  
  (Required) Path to input file (CSV or JSON).
- `--output <output_file>`  
  (Required) Path to output file.
- `--output-format {csv,json}`  
  Output format (default matches input or is user-specified).

### Data Acquisition (from EDH)
- `--download-edh <inscription_id>`  
  Download EDH inscription and metadata by ID.
- `--download-dir <folder>`  
  Directory to store downloaded files (required with `--download-edh`).

### Entity Extraction & Confidence
- `--confidence-threshold <float>`  
  Minimum confidence score to accept entity (default: 0.5).
- `--flag-ambiguous`  
  If set, entities below threshold are flagged as `"ambiguous": true` rather than omitted.

### Other
- `--help`  
  Show all CLI options.

---

## Extraction/Parsing Details

- Input may contain single or multiple inscriptions.
- Tool dynamically detects/labels entities using the pretrained `latin-bert` NER model.
- Extracts all entity types listed above, subject to model output.
- Each output record includes:
  - All extracted entities and their confidence scores.
  - A marker for ambiguous entities if `--flag-ambiguous` is set.
- If an entity is not found or confidence is below threshold (and not flagged), it is omitted from the output for that inscription.

---

## Output Format

### JSON Example
```json
{
  "inscription_id": 12345,
  "praenomen": { "value": "Gaius", "confidence": 0.91 },
  "nomen": { "value": "Iulius", "confidence": 0.88 },
  "cognomen": { "value": "Caesar", "confidence": 0.95 },
  "age_at_death": { "value": "57", "confidence": 0.75, "ambiguous": true },
  "status": { "value": "civis Romanus", "confidence": 0.92 }
}

## Error Handling

    All errors, warnings, and progress messages are sent to stderr.
    If confidence threshold is invalid or files cannot be accessed, the tool exits with a nonzero status and an explanatory message.

## Requirements

    Python 3.8+
    Model dependencies: HuggingFace Transformers, PyTorch, latin-bert from github.com/dbamman/latin-bert
    Other libraries: requests (for downloads), pandas (for csv/json handling)

## Testing

    Includes unit tests and CLI-level tests covering:
        Entity extraction output
        Confidence threshold handling
        EDH download
        Input/output in both CSV/JSON

## Documentation

All command-line options and usage examples are included in the built-in --help or -h option.
No extra package distribution outside source repo.

## Example Usage
```
# Parse local data
latinepi --input inscriptions.csv --output structured_data.json --output-format json

# Download and parse an EDH inscription
latinepi --download-edh 12345 --download-dir ./edh/ --input ./edh/12345.json --output ./parsed/12345.json

# Parse with stricter threshold and flag ambiguous entities
latinepi --input batch.json --output results.csv --output-format csv --confidence-threshold 0.8 --flag-ambiguous
```

## Project Structure
```
latinepi/
  |- cli.py         # Main CLI entry
  |- parser.py      # Extraction logic and model wrappers
  |- edh_utils.py   # For EDH download/formatting
  |- test/
      |- test_parser.py
      |- test_cli.py
  |- README.md
  |- requirements.txt
  ```
