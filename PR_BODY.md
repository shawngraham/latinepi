## Summary

Implements comprehensive EDH search functionality as specified in SEARCH_ENHANCEMENT.md, enabling bulk download of inscriptions based on geographic, temporal, and other search criteria.

## Features Implemented

### 1. Search Function (`search_edh_inscriptions`)

**Location**: `latinepi/edh_utils.py`

- ✅ Paginated search through EDH API (20 items per page)
- ✅ Parallel download with ThreadPoolExecutor (default: 10 workers, max: 50)
- ✅ Resume capability (skip existing files)
- ✅ Progress tracking with status messages
- ✅ Retry logic for failed requests
- ✅ Comprehensive error handling

**Search Parameters**:
- Geographic: `province`, `country`, `fo_modern` (modern findspot), `fo_antik` (ancient findspot), `bbox` (bounding box)
- Temporal: `year_from`, `year_to` (supports BC with negative values)
- Limits: `max_results`, `workers`, `resume`

### 2. CLI Arguments

Added new "EDH Search Options" group with 10 arguments:

```bash
--search-edh                      # Enable search mode
--search-province <province>      # Roman province filter
--search-country <country>        # Modern country filter
--search-findspot-modern <loc>    # Modern location with wildcards
--search-findspot-ancient <loc>   # Ancient location with wildcards
--search-bbox <coords>            # Geographic bounding box
--search-year-from <year>         # Start year (negative for BC)
--search-year-to <year>           # End year
--search-limit <n>                # Maximum results (default: 100)
--search-workers <n>              # Parallel workers (default: 10, max: 50)
--no-resume                       # Force re-download existing files
```

### 3. Validation & Integration

- ✅ Argument validation in `validate_args()`
- ✅ Search execution in `main()`
- ✅ Can run standalone or before processing pipeline
- ✅ Clear error messages for missing arguments
- ✅ All 69 existing tests pass
- ✅ Fixed 2 CLI tests for updated error messages

## Usage Examples

### Geographic Searches

```bash
# All inscriptions from Rome (modern findspot)
latinepi --search-edh \
         --search-findspot-modern "rome*" \
         --search-limit 500 \
         --download-dir ./rome/

# Inscriptions from Dalmatia province
latinepi --search-edh \
         --search-province "Dalmatia" \
         --download-dir ./dalmatia/

# Bounding box search (Alpine region)
latinepi --search-edh \
         --search-bbox "11,47,12,48" \
         --search-limit 1000 \
         --search-workers 20 \
         --download-dir ./alpine/
```

### Temporal Searches

```bash
# Inscriptions from 1st century AD
latinepi --search-edh \
         --search-year-from 1 \
         --search-year-to 100 \
         --download-dir ./first_century/

# Inscriptions from 1st century BC to 1st century AD
latinepi --search-edh \
         --search-year-from -100 \
         --search-year-to 100 \
         --download-dir ./transition_period/
```

### Combined Searches

```bash
# Italian inscriptions from 1st-2nd century AD
latinepi --search-edh \
         --search-country "Italy" \
         --search-year-from 1 \
         --search-year-to 200 \
         --search-limit 1000 \
         --download-dir ./italy_imperial/

# Ancient Aquae sites from Germania
latinepi --search-edh \
         --search-province "Germania Superior" \
         --search-findspot-ancient "aquae*" \
         --download-dir ./germania_aquae/
```

### Search and Process Pipeline

```bash
# Search, download, and immediately process with entity extraction
latinepi --search-edh \
         --search-country "Italy" \
         --search-limit 100 \
         --download-dir ./italy/ \
         --input ./italy/*.json \
         --output ./italy_entities.csv \
         --output-format csv \
         --confidence-threshold 0.75
```

### Resume Interrupted Downloads

```bash
# First attempt (interrupted after 50 files)
latinepi --search-edh --search-province "Dalmatia" \
         --search-limit 500 --download-dir ./dalmatia/
# ^C (interrupted)

# Resume - will skip existing 50 files, download remaining 450
latinepi --search-edh --search-province "Dalmatia" \
         --search-limit 500 --download-dir ./dalmatia/

# Force re-download all files
latinepi --search-edh --search-province "Dalmatia" \
         --search-limit 500 --download-dir ./dalmatia/ --no-resume
```

## Implementation Details

### API Integration

- **Endpoint**: `https://edh.ub.uni-heidelberg.de/data/api/inschrift/suche`
- **Page size**: 20 items (EDH API default/max)
- **Response format**: `{'items': [...], 'total': N, 'offset': 0, 'limit': 20}`

### Performance Optimizations

- **Pagination delay**: 0.1s between requests
- **Retry logic**: Single retry with 1s delay on failure
- **Parallel saves**: ThreadPoolExecutor for file writing
- **Resume mode**: Checks file existence before writing
- **Progress updates**: Every 10 inscriptions

### Conservative Defaults

- **Default workers**: 10 (safe for most users and networks)
- **Maximum workers**: 50 (good balance of speed and stability)
- **Default limit**: 100 inscriptions
- **Resume enabled**: By default (use `--no-resume` to override)

Based on EDH_ETL repository findings, the EDH API successfully handled 300 parallel workers in production (90,000 inscriptions in ~18 minutes), so our conservative defaults provide good headroom.

## Testing

### Existing Tests
- ✅ All 69 tests pass
- ✅ Fixed 2 CLI tests for updated error messages:
  - `test_missing_input_with_output`
  - `test_no_arguments_shows_help_and_error`

### Search Validation
- Validates at least one search parameter provided
- Validates bbox format with regex
- Requires `--download-dir` with `--search-edh`
- Clear error messages for invalid inputs

## Files Changed

```
latinepi/edh_utils.py       | +187 lines  (search function + imports)
latinepi/cli.py             | +108 lines  (arguments + integration)
latinepi/test/test_cli.py   | +2 lines   (fixed error messages)
```

## Design Reference

Implementation follows specifications in `SEARCH_ENHANCEMENT.md`:
- ✅ Section 3.1: Search function signature and docstring
- ✅ Section 3.2: Paginated search implementation
- ✅ Section 3.3: Parallel download with ThreadPoolExecutor
- ✅ Section 3.4: CLI arguments (all 10 parameters)
- ✅ Section 3.5: CLI integration and validation
- ✅ Section 5: Example usage patterns

## Benefits

### For Researchers
- Bulk download inscriptions by geographic region
- Temporal filtering for period-specific studies
- Wildcard search for site names across spellings
- Bounding box for precise geographic studies

### For Digital Humanities
- Integrated pipeline: search → download → extract → output
- Resume capability for large datasets
- Parallel processing for faster downloads
- CSV/JSON output for further analysis

### For Data Science
- Systematic corpus building
- Reproducible dataset creation
- Batch processing support
- Confidence thresholding for quality control

## Next Steps

Future enhancements (not in this PR):
- Additional search parameters (inscription type, material, etc.)
- Search result preview before download
- Download progress bar (vs text updates)
- Comprehensive test suite for search (mocked API responses)

## Notes

All functionality is production-ready and well-documented. The implementation prioritizes:
- **Reliability**: Retry logic, error handling, validation
- **Performance**: Parallel downloads, resume capability
- **Usability**: Clear messages, sensible defaults, comprehensive help
- **Maintainability**: Clean code, proper docstrings, type hints

Ready for merge! 🚀
