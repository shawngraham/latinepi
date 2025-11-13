# latinepi

A command-line tool for extracting structured personal data from Roman Latin epigraphic inscriptions using Named Entity Recognition (NER).

## Features

- **Entity Extraction**: Extract prosopographical data (personal names, status, locations, etc.) from Latin inscriptions
- **Multiple Input Formats**: Process CSV or JSON files containing inscription data
- **Flexible Output**: Export results as JSON or CSV with confidence scores
- **Confidence Filtering**: Set minimum confidence thresholds and flag ambiguous entities
- **EDH Integration**: Download inscriptions directly from the Epigraphic Database Heidelberg (EDH) API
- **Two Extraction Modes**:
  - **Stub Mode** (default): Fast pattern-based extraction for testing and development
  - **Model Mode**: ML-based extraction using the latin-bert transformer model

## Installation

### Basic Installation (Stub Mode)

```bash
# Clone the repository
git clone https://github.com/shawngraham/latinitas.git
cd latinitas

# Install core dependencies
pip install -r requirements.txt
```

This installation runs in **stub mode** by default, using pattern-based entity extraction. This is sufficient for testing and basic usage.

### Advanced Installation (Model Mode)

For production use with the full latin-bert NER model:

```bash
# Install additional ML dependencies
pip install torch>=2.0.0 transformers>=4.30.0 cltk>=1.0.0

# Download the latin-bert model
git clone https://github.com/dbamman/latin-bert.git
cd latin-bert
bash download.sh
cd ..

# Configure environment variables
export LATINEPI_USE_STUB=false
export LATIN_BERT_PATH=/path/to/latin-bert/models/latin_bert
```

See [SETUP.md](SETUP.md) for detailed installation instructions and troubleshooting.

## Quick Start

### Example 1: Process a CSV file

```bash
python3 latinepi/cli.py --input inscriptions.csv --output results.json
```

**Input** (`inscriptions.csv`):
```csv
id,text,location
1,"D M GAIVS IVLIVS CAESAR",Rome
2,"MARCVS ANTONIVS FELIX",Pompeii
```

**Output** (`results.json`):
```json
[
  {
    "inscription_id": 1,
    "praenomen": "Gaius",
    "praenomen_confidence": 0.92,
    "nomen": "Iulius",
    "nomen_confidence": 0.88,
    "cognomen": "Caesar",
    "cognomen_confidence": 0.95
  },
  {
    "inscription_id": 2,
    "praenomen": "Marcus",
    "praenomen_confidence": 0.91,
    "nomen": "Antonius",
    "nomen_confidence": 0.87,
    "cognomen": "Felix",
    "cognomen_confidence": 0.89
  }
]
```

### Example 2: Download from EDH and process

```bash
# Download inscription HD000001 from EDH
python3 latinepi/cli.py --download-edh HD000001 --download-dir ./edh_data/

# Process the downloaded file
python3 latinepi/cli.py --input ./edh_data/HD000001.json --output results.json
```

### Example 3: CSV output with high confidence threshold

```bash
python3 latinepi/cli.py \
  --input inscriptions.json \
  --output results.csv \
  --output-format csv \
  --confidence-threshold 0.8
```

Only entities with confidence ≥ 0.8 will be included in the output.

### Example 4: Flag ambiguous entities

```bash
python3 latinepi/cli.py \
  --input inscriptions.json \
  --output results.json \
  --confidence-threshold 0.9 \
  --flag-ambiguous
```

Entities below the threshold will be included with an `{entity}_ambiguous: true` flag.

## Command-Line Reference

### Input/Output Options

| Argument | Description | Required |
|----------|-------------|----------|
| `--input <file>` | Input file (CSV or JSON) containing inscriptions | Yes* |
| `--output <file>` | Output file for extracted entities | Yes** |
| `--output-format {json,csv}` | Output format (default: json) | No |

\* Required when processing inscriptions
\** Required when `--input` is specified

### Entity Extraction Options

| Argument | Description | Default |
|----------|-------------|---------|
| `--confidence-threshold <0.0-1.0>` | Minimum confidence score for entities | 0.5 |
| `--flag-ambiguous` | Include low-confidence entities with "ambiguous" flag | Off |

### EDH API Download

| Argument | Description | Required |
|----------|-------------|----------|
| `--download-edh <id>` | Download inscription from EDH (e.g., HD000001 or 123) | No |
| `--download-dir <directory>` | Directory for downloaded files | Yes with `--download-edh` |

### Help

| Argument | Description |
|----------|-------------|
| `--help` | Show help message with all options and examples |

## Input File Formats

### CSV Format

```csv
id,text,location
1,"D M GAIVS IVLIVS CAESAR",Rome
2,"MARCVS ANTONIVS FELIX",Pompeii
```

**Requirements**:
- Must have a `text` column containing the inscription text
- Optional `id` or `Id` column for tracking inscriptions
- Other columns are ignored but preserved in context

### JSON Format

```json
[
  {
    "id": 1,
    "text": "D M GAIVS IVLIVS CAESAR",
    "location": "Rome"
  },
  {
    "id": 2,
    "text": "MARCVS ANTONIVS FELIX",
    "location": "Pompeii"
  }
]
```

**Requirements**:
- Must be a JSON array of objects
- Each object must have a `text` field
- Optional `id` or `Id` field for tracking

## Output File Formats

### JSON Output (default)

```json
[
  {
    "inscription_id": 1,
    "praenomen": "Gaius",
    "praenomen_confidence": 0.92,
    "nomen": "Iulius",
    "nomen_confidence": 0.88,
    "cognomen": "Caesar",
    "cognomen_confidence": 0.95
  }
]
```

### CSV Output

```csv
inscription_id,cognomen,cognomen_confidence,nomen,nomen_confidence,praenomen,praenomen_confidence
1,Caesar,0.95,Iulius,0.88,Gaius,0.92
```

**Note**: When using `--flag-ambiguous`, additional `{entity}_ambiguous` columns will be added for entities below the confidence threshold.

## Entity Types

The tool extracts the following entity types from inscriptions:

| Entity | Description | Example |
|--------|-------------|---------|
| `praenomen` | Roman first name | Gaius, Marcus, Lucius |
| `nomen` | Roman family name (gens) | Iulius, Antonius, Cornelius |
| `cognomen` | Roman personal surname | Caesar, Cicero, Brutus |
| `status` | Social status markers | libertus, senator, eques |
| `location` | Place names | Rome, Pompeii, Ostia |
| `age_at_death` | Age at death | "30 years", "V annos" |
| `occupation` | Profession or role | centurion, merchant, priest |
| `gender` | Gender markers | male, female |
| `military_service` | Military unit or rank | legio X, veteran |
| `filiation` | Patronymic information | filius, filia, libertus |

Each extracted entity includes:
- **value**: The extracted text (normalized)
- **confidence**: Confidence score (0.0-1.0)
- **ambiguous** (optional): Flag for entities below threshold (when using `--flag-ambiguous`)

## Usage Examples

### Example 1: Basic Processing

```bash
python3 latinepi/cli.py --input data.csv --output results.json
```

**Expected Output**:
```
Processing 10 inscription(s)...
Processed inscription 1/10
Processed inscription 2/10
...
Successfully processed 10 inscription(s) -> 'results.json'
```

### Example 2: High Confidence Filtering

```bash
python3 latinepi/cli.py \
  --input data.json \
  --output high_confidence.csv \
  --output-format csv \
  --confidence-threshold 0.95
```

Only extracts entities with ≥95% confidence. Useful for high-precision applications.

### Example 3: Include Ambiguous Entities

```bash
python3 latinepi/cli.py \
  --input data.json \
  --output all_entities.json \
  --confidence-threshold 0.7 \
  --flag-ambiguous
```

**Output includes ambiguous flags**:
```json
{
  "inscription_id": 1,
  "praenomen": "Gaius",
  "praenomen_confidence": 0.92,
  "nomen": "Iulius",
  "nomen_confidence": 0.65,
  "nomen_ambiguous": true
}
```

The `nomen` entity has confidence 0.65 (below 0.7 threshold), so it's flagged as ambiguous.

### Example 4: Download and Process EDH Inscription

```bash
# Download single inscription
python3 latinepi/cli.py --download-edh HD000001 --download-dir ./edh/

# Process downloaded file
python3 latinepi/cli.py --input ./edh/HD000001.json --output results.json
```

### Example 5: Batch Processing from EDH

```bash
# Download multiple inscriptions
for id in HD000001 HD000002 HD000003; do
  python3 latinepi/cli.py --download-edh $id --download-dir ./edh/
done

# Process all downloaded files
python3 latinepi/cli.py --input ./edh/HD000001.json --output results1.json
python3 latinepi/cli.py --input ./edh/HD000002.json --output results2.json
python3 latinepi/cli.py --input ./edh/HD000003.json --output results3.json
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LATINEPI_USE_STUB` | Use stub/pattern-based extraction instead of ML model | `true` |
| `LATIN_BERT_PATH` | Path to latin-bert model directory | None |

**Example**:
```bash
export LATINEPI_USE_STUB=false
export LATIN_BERT_PATH=/home/user/latin-bert/models/latin_bert
python3 latinepi/cli.py --input data.csv --output results.json
```

## Error Handling

### Missing Input File

```bash
python3 latinepi/cli.py --input missing.csv --output results.json
```

**Output**:
```
Error: Input file not found: 'missing.csv'
```

**Exit Code**: 1

### Invalid Confidence Threshold

```bash
python3 latinepi/cli.py --input data.csv --output results.json --confidence-threshold 1.5
```

**Output**:
```
Error: --confidence-threshold must be between 0.0 and 1.0
       Got: 1.5
```

**Exit Code**: 1

### Missing Required Arguments

```bash
python3 latinepi/cli.py --input data.csv
```

**Output**:
```
Error: --output is required when processing inscriptions with --input
```

**Exit Code**: 1

### Empty or Invalid Inscriptions

```bash
python3 latinepi/cli.py --input data_with_empty_text.json --output results.json
```

**Output**:
```
Processing 3 inscription(s)...
Processed inscription 1/3
Warning: Inscription 2 has no 'text' field, skipping
Processed inscription 3/3
Successfully processed 2 inscription(s) -> 'results.json'
```

**Exit Code**: 0 (warnings are non-fatal)

## Testing

### Run All Tests

```bash
# Run complete test suite
python3 -m unittest discover -s latinepi/test -p "test_*.py" -v
```

**Expected Output**:
```
test_cli_basic_execution (test_cli.TestCLI) ... ok
test_csv_output_format (test_cli.TestCLI) ... ok
...
----------------------------------------------------------------------
Ran 69 tests in 5.234s

OK
```

### Run Specific Test Modules

```bash
# CLI tests only
python3 -m unittest latinepi.test.test_cli

# Parser tests only
python3 -m unittest latinepi.test.test_parser

# Integration tests only
python3 -m unittest latinepi.test.test_integration

# EDH utility tests
python3 -m unittest latinepi.test.test_edh_utils
```

### Run Individual Tests

```bash
python3 -m unittest latinepi.test.test_integration.TestIntegration.test_full_workflow_json_to_json
```

## Project Structure

```
latinitas/
├── latinepi/
│   ├── __init__.py
│   ├── cli.py              # Main CLI entry point
│   ├── parser.py           # Entity extraction logic
│   ├── edh_utils.py        # EDH API integration
│   └── test/
│       ├── test_cli.py     # CLI unit tests (22 tests)
│       ├── test_parser.py  # Parser unit tests (21 tests)
│       ├── test_edh_utils.py  # EDH utility tests (11 tests)
│       └── test_integration.py  # Integration tests (15 tests)
├── requirements.txt        # Python dependencies
├── SETUP.md               # Detailed setup guide
├── SEARCH_ENHANCEMENT.md  # Future EDH search feature design
├── plan.md                # Development plan
└── README.md              # This file
```

## Dependencies

### Core Dependencies (Always Required)

- **Python 3.8+**
- **pandas** (≥1.5.0): CSV/JSON parsing and data manipulation
- **requests** (≥2.28.0): HTTP requests for EDH API

### Optional Dependencies (Model Mode Only)

- **torch** (≥2.0.0): PyTorch deep learning framework
- **transformers** (≥4.30.0): HuggingFace transformers library
- **cltk** (≥1.0.0): Classical Language Toolkit (alternative tokenizer)

See [requirements.txt](requirements.txt) for detailed dependency information.

## Performance

### Stub Mode (Pattern-Based)

- **Processing Speed**: ~100-200 inscriptions/second
- **Memory Usage**: Minimal (<100 MB)
- **Accuracy**: Moderate (pattern-based heuristics)

### Model Mode (ML-Based)

- **Processing Speed**: ~5-10 inscriptions/second (CPU), ~50-100/second (GPU)
- **Memory Usage**: ~2-4 GB (model loaded in memory)
- **Accuracy**: High (transformer-based NER)
- **Model Load Time**: ~3-5 seconds (one-time initialization)

**Note**: Model is loaded once and cached for the entire processing run.

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pandas'"

**Solution**: Install core dependencies:
```bash
pip install -r requirements.txt
```

### Issue: "Warning: LATIN_BERT_PATH not set. Using generic multilingual model."

**Cause**: Model mode is enabled but latin-bert model path is not configured.

**Solution**: Either:
1. Set `LATIN_BERT_PATH` environment variable to point to latin-bert model, or
2. Use stub mode: `export LATINEPI_USE_STUB=true`

See [SETUP.md](SETUP.md) for detailed configuration instructions.

### Issue: EDH download fails with "HTTP Error 404"

**Cause**: Invalid or non-existent inscription ID.

**Solution**: Verify the inscription ID exists in EDH database at https://edh.ub.uni-heidelberg.de/

### Issue: CSV output has missing columns for some records

**Cause**: Different inscriptions may have different entities extracted based on content and confidence threshold.

**Behavior**: This is expected. The tool collects all unique fieldnames from all records and creates columns for all possible fields. Records without certain entities will have empty values in those columns.

### Issue: Tests fail with "FileNotFoundError"

**Cause**: Running tests from wrong directory.

**Solution**: Run tests from project root:
```bash
cd /path/to/latinitas
python3 -m unittest discover -s latinepi/test
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Future Enhancements

- **EDH Search API**: Bulk download inscriptions by search criteria (province, date range, location). See [SEARCH_ENHANCEMENT.md](SEARCH_ENHANCEMENT.md) for design.
- **Web Interface**: Browser-based UI for non-technical users
- **Additional Output Formats**: XML, RDF/Linked Data
- **Batch Processing Optimization**: Parallel processing for large datasets
- **Model Fine-tuning**: Train on domain-specific inscription corpora

## License

See repository license file for details.

## References

- **latin-bert Model**: https://github.com/dbamman/latin-bert
- **EDH Database**: https://edh.ub.uni-heidelberg.de/
- **EDH API**: https://edh.ub.uni-heidelberg.de/data/api
- **CLTK**: https://github.com/cltk/cltk

## Citation

If you use this tool in research, please cite:

```bibtex
@software{latinepi,
  title = {latinepi: Latin Epigraphic Inscription Parser},
  author = {Graham, Shawn},
  year = {2025},
  url = {https://github.com/shawngraham/latinitas}
}
```

## Contact

For questions, issues, or suggestions:
- Open an issue: https://github.com/shawngraham/latinitas/issues
- Repository: https://github.com/shawngraham/latinitas
