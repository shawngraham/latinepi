## Summary

This PR implements Prompts 1-10 of the Latin inscription parser CLI tool, plus a comprehensive design document for EDH search functionality.

## Completed Prompts (1-10)

### ✅ Prompt 1: Project Scaffold
- Created project structure with latinepi/ package
- Implemented "Hello World" CLI
- Added .gitignore

### ✅ Prompt 2: CLI Argument Parsing
- Implemented argparse with --input, --output, --output-format
- Comprehensive help text and error handling
- 6 CLI tests

### ✅ Prompt 3: File I/O
- File reading/writing functionality
- Tempfile support in tests

### ✅ Prompt 4: CSV/JSON Parsing
- Implemented read_inscriptions() with CSV and JSON support
- Comprehensive error handling
- 12 parser tests

### ✅ Prompts 5-6: Entity Extraction and Batch Processing
- Stub extract_entities() with pattern-based NER
- Batch processing with progress messages
- Flattened output structure

### ✅ Prompt 7: Latin BERT Model Integration
- Real NER model infrastructure with HuggingFace Transformers
- Environment variable configuration (LATINEPI_USE_STUB, LATIN_BERT_PATH)
- Support for local latin-bert model from dbmdz/latin-bert repo
- Global model caching to avoid reloading
- Graceful fallback with helpful warnings
- Created SETUP.md with comprehensive setup guide
- requirements.txt with CLTK documentation

### ✅ Prompt 8: Confidence/Threshold Logic
- Added --confidence-threshold (default: 0.5)
- Added --flag-ambiguous flag
- Implemented filtering logic in CLI
- 6 comprehensive tests for threshold behavior

### ✅ Prompt 9: Output Formatting (Already Complete)
- Verified JSON/CSV output formatting works correctly
- Confidence scores as {field}_confidence
- Ambiguous flags as {field}_ambiguous

### ✅ Prompt 10: EDH Download Utility
- Implemented download_edh_inscription() in edh_utils.py
- Downloads from EDH API: https://edh-www.adw.uni-heidelberg.de/data/api/inscriptions/{id}
- Supports HD prefix auto-conversion for numeric IDs
- Added --download-edh and --download-dir CLI flags
- 11 comprehensive tests in test_edh_utils.py
- 3 CLI integration tests

## EDH Search Enhancement (Design Only)

Added comprehensive design document: **SEARCH_ENHANCEMENT.md**

### Key Features Designed:
- Search EDH API by province, country, findspot (modern/ancient), bbox, dates
- Correct endpoint: `https://edh.ub.uni-heidelberg.de/data/api/inschrift/suche`
- Paginated results handling (20 items per page)
- Parallel downloads with ThreadPoolExecutor (10 workers default, max 50)
- Resume capability to skip already-downloaded files
- Retry logic with 1s delays on errors

### Based on EDH_ETL Analysis:
- Response structure: `{'items': [...], 'limit': 20, 'offset': 0, 'total': N}`
- Proven pattern: 300 workers successfully downloaded 90K inscriptions in 18 min
- Search parameters: province, country, fo_modern, fo_antik, bbox, dat_jahr_a/e

### Implementation Planned:
- New function: `search_edh_inscriptions()` in edh_utils.py
- 10 new CLI arguments (--search-edh, --search-province, --search-limit, etc.)
- Comprehensive testing strategy
- Documentation updates

**Note:** Search implementation will be completed after finishing Prompts 11-15.

## Test Results

**49 tests passing** (17 CLI + 11 EDH + 21 parser)

```bash
python -m unittest discover -s latinepi/test -p "test_*.py" -v
# Ran 49 tests in 4.022s
# OK
```

## Files Changed

### New Files:
- latinepi/__init__.py
- latinepi/cli.py (140 lines)
- latinepi/parser.py (328 lines)
- latinepi/edh_utils.py (100 lines)
- latinepi/test/__init__.py
- latinepi/test/test_cli.py (477 lines)
- latinepi/test/test_parser.py (304 lines)
- latinepi/test/test_edh_utils.py (200+ lines)
- requirements.txt
- SETUP.md (comprehensive setup guide)
- SEARCH_ENHANCEMENT.md (design document)
- .gitignore

### Documentation:
- plan.md (updated, Prompts 1-10 marked complete)
- spec.md (reference)

## Example Usage

### Basic Entity Extraction
```bash
latinepi --input inscriptions.csv --output results.json
```

### With Confidence Filtering
```bash
latinepi --input data.json --output output.csv \
         --output-format csv \
         --confidence-threshold 0.85 \
         --flag-ambiguous
```

### Download from EDH
```bash
latinepi --download-edh HD000001 --download-dir ./edh/
```

### Complete Workflow (after search implementation)
```bash
# Search, download, and process
latinepi --search-edh --search-province "Dalmatia" \
         --search-limit 500 --download-dir ./dalmatia/ \
         --input ./dalmatia/*.json --output dalmatia_entities.csv
```

## Remaining Work

**Prompts 11-15:**
- Prompt 11: CLI Argument Validation, User Guidance, and Error Handling
- Prompt 12: End-to-End Integration and Full CLI Test Suite
- Prompt 13: Project Documentation and Usage Examples
- Prompt 14: Final Wiring and Cleanup
- Prompt 15: Continuous Integration Scaffold

**Future Enhancement:**
- Implement EDH search functionality as designed in SEARCH_ENHANCEMENT.md

## Dependencies

**Core (required):**
- pandas>=1.5.0
- requests>=2.28.0

**Optional (for real NER):**
- torch>=2.0.0
- transformers>=4.30.0
- Latin BERT model (manual download)

**Optional (future):**
- cltk>=1.0.0 (Latin tokenization)

## Notes

- All code follows defensive programming principles
- Comprehensive error handling with stderr/stdout separation
- Graceful fallback mechanisms for model loading
- Resume-capable downloads
- Well-documented with docstrings and type hints
