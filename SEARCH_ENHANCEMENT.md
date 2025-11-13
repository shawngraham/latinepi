# EDH Search Functionality Enhancement

## Overview

This document outlines the design for adding comprehensive search functionality to the latinepi tool, enabling users to search and download multiple inscriptions from the Epigraphic Database Heidelberg (EDH) API based on various criteria.

## Current State

**Implemented (Prompt 10):**
- `download_edh_inscription(inscription_id, out_dir)` - Downloads single inscription by ID
- CLI flags: `--download-edh <id>` and `--download-dir <directory>`
- Endpoint used: `https://edh-www.adw.uni-heidelberg.de/data/api/inscriptions/{id}`

**Limitation:**
- Only supports individual inscription downloads by ID
- No batch search or filtering capabilities

## Proposed Enhancement

Add search functionality to download multiple inscriptions based on geographic, temporal, and other search criteria.

## API Endpoint

Based on the EDH_ETL repository analysis, the correct search endpoint is:

```
https://edh.ub.uni-heidelberg.de/data/api/inschrift/suche?
```

**Note:** This is different from the individual inscription endpoint. The search endpoint uses German (`inschrift/suche` = inscription/search) while individual lookups may use English paths.

## API Response Structure

```json
{
  "items": [
    {
      "inscription_id": "HD000001",
      "text": "...",
      "country": "...",
      "province": "...",
      // ... ~27 fields per inscription
    }
  ],
  "limit": 20,
  "offset": 0,
  "total": 1543
}
```

**Pagination:**
- Default page size: 20 items
- Use `offset` parameter to retrieve additional pages
- `total` indicates total matching results

## Search Parameters

Based on EDH API documentation and EDH_ETL examples:

### Geographic Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `province` | string | Roman province (case-insensitive) | `Dalmatia`, `Germania Superior` |
| `country` | string | Modern country (case-insensitive) | `Italy`, `Germany` |
| `fo_modern` | string | Modern findspot with wildcards | `rome*`, `köln*` |
| `fo_antik` | string | Ancient findspot with wildcards | `aquae*`, `colonia*` |
| `bbox` | string | Bounding box coordinates | `minLong,minLat,maxLong,maxLat` |

### Temporal Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `dat_jahr_a` | integer | Year not before (BC = negative) | `1`, `-50` (50 BC) |
| `dat_jahr_e` | integer | Year not after | `200`, `100` |

### Pagination Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `offset` | integer | Starting position for results | `0`, `20`, `40` |
| `limit` | integer | Results per page (max ~20) | `20` |

### Inscription Lookup

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `hd_nr` | string/integer | Specific inscription number | `1` (returns HD000001) |

## Implementation Design

### 1. New Function: `search_edh_inscriptions()`

**Location:** `latinepi/edh_utils.py`

```python
def search_edh_inscriptions(
    out_dir: str,
    province: str = None,
    country: str = None,
    fo_modern: str = None,
    fo_antik: str = None,
    bbox: str = None,
    year_from: int = None,
    year_to: int = None,
    max_results: int = 100,
    workers: int = 10,
    resume: bool = True
) -> List[str]:
    """
    Search EDH API and download matching inscriptions.

    Args:
        out_dir: Output directory for downloaded files
        province: Roman province name (case-insensitive)
        country: Modern country name (case-insensitive)
        fo_modern: Modern findspot with wildcards (e.g., "rome*")
        fo_antik: Ancient findspot with wildcards (e.g., "aquae*")
        bbox: Bounding box "minLong,minLat,maxLong,maxLat"
        year_from: Year not before (negative for BC)
        year_to: Year not after
        max_results: Maximum inscriptions to download (default: 100)
        workers: Parallel download workers (default: 10, max: 50)
        resume: Skip already-downloaded files (default: True)

    Returns:
        List of paths to downloaded JSON files

    Raises:
        ValueError: If no search parameters provided or invalid bbox format
        requests.HTTPError: If API requests fail
        OSError: If output directory cannot be created
    """
```

### 2. Search Implementation Strategy

#### Phase 1: Build Search Query
```python
search_params = {}
if province:
    search_params['province'] = province
if country:
    search_params['country'] = country
if fo_modern:
    search_params['fo_modern'] = fo_modern
if fo_antik:
    search_params['fo_antik'] = fo_antik
if bbox:
    # Validate bbox format
    if not re.match(r'^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$', bbox):
        raise ValueError("Invalid bbox format. Expected: minLong,minLat,maxLong,maxLat")
    search_params['bbox'] = bbox
if year_from is not None:
    search_params['dat_jahr_a'] = year_from
if year_to is not None:
    search_params['dat_jahr_e'] = year_to

if not search_params:
    raise ValueError("At least one search parameter must be provided")
```

#### Phase 2: Paginated Search
```python
SEARCH_URL = "https://edh.ub.uni-heidelberg.de/data/api/inschrift/suche"
offset = 0
page_size = 20  # EDH API default/max
all_items = []

print(f"Searching EDH API with parameters: {search_params}", file=sys.stderr)

while len(all_items) < max_results:
    # Add pagination params
    params = {**search_params, 'offset': offset, 'limit': page_size}

    try:
        response = requests.get(SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        total = data.get('total', 0)
        items = data.get('items', [])

        if not items:
            break  # No more results

        all_items.extend(items)
        offset += page_size

        print(f"Retrieved {len(all_items)}/{min(total, max_results)} inscriptions...",
              file=sys.stderr)

        # Don't exceed user's limit
        if len(all_items) >= max_results:
            all_items = all_items[:max_results]
            break

        # Don't exceed available results
        if len(all_items) >= total:
            break

        # Small delay between pagination requests
        time.sleep(0.1)

    except requests.exceptions.RequestException as e:
        print(f"Warning: Search request failed: {e}", file=sys.stderr)
        time.sleep(1)
        # Retry once
        try:
            response = requests.get(SEARCH_URL, params=params, timeout=30)
            data = response.json()
            items = data.get('items', [])
            all_items.extend(items)
            offset += page_size
        except:
            break  # Give up on this page

print(f"Search complete. Found {len(all_items)} inscriptions.", file=sys.stderr)
```

#### Phase 3: Parallel Download with ThreadPoolExecutor
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def save_inscription(inscription_data, out_dir, resume):
    """Save a single inscription to JSON file."""
    # Extract ID from inscription data
    insc_id = inscription_data.get('inscription_id') or inscription_data.get('id')

    if not insc_id:
        # Generate ID from hd_nr if available
        hd_nr = inscription_data.get('hd_nr')
        if hd_nr:
            insc_id = f"HD{str(hd_nr).zfill(6)}"
        else:
            return None  # Can't save without ID

    output_file = Path(out_dir) / f"{insc_id}.json"

    # Skip if resume enabled and file exists
    if resume and output_file.exists():
        return str(output_file)

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(inscription_data, f, indent=2, ensure_ascii=False)
        return str(output_file)
    except Exception as e:
        print(f"Warning: Failed to save {insc_id}: {e}", file=sys.stderr)
        time.sleep(1)
        # Retry once
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(inscription_data, f, indent=2, ensure_ascii=False)
            return str(output_file)
        except:
            return None

# Create output directory
Path(out_dir).mkdir(parents=True, exist_ok=True)

# Parallel download with progress tracking
saved_files = []
workers_count = min(workers, 50)  # Cap at 50 workers

print(f"Downloading {len(all_items)} inscriptions with {workers_count} workers...",
      file=sys.stderr)

with ThreadPoolExecutor(max_workers=workers_count) as executor:
    # Submit all download tasks
    futures = {executor.submit(save_inscription, item, out_dir, resume): item
               for item in all_items}

    # Process completed downloads
    for i, future in enumerate(as_completed(futures), 1):
        result = future.result()
        if result:
            saved_files.append(result)

        # Progress update every 10 items or at end
        if i % 10 == 0 or i == len(all_items):
            print(f"Saved {i}/{len(all_items)} inscriptions", file=sys.stderr)

print(f"Download complete. Saved {len(saved_files)} files to {out_dir}", file=sys.stderr)
return saved_files
```

### 3. CLI Arguments

Add to `latinepi/cli.py` in `create_parser()`:

```python
# EDH search arguments
search_group = parser.add_argument_group('EDH search options')

search_group.add_argument(
    '--search-edh',
    action='store_true',
    help='Search and download multiple inscriptions from EDH API'
)

search_group.add_argument(
    '--search-province',
    metavar='<province>',
    help='Roman province (e.g., Dalmatia, "Germania Superior")'
)

search_group.add_argument(
    '--search-country',
    metavar='<country>',
    help='Modern country name (e.g., Italy, Germany)'
)

search_group.add_argument(
    '--search-findspot-modern',
    metavar='<location>',
    help='Modern findspot with wildcards (e.g., rome*, köln*)'
)

search_group.add_argument(
    '--search-findspot-ancient',
    metavar='<location>',
    help='Ancient findspot with wildcards (e.g., aquae*, colonia*)'
)

search_group.add_argument(
    '--search-bbox',
    metavar='<minLong,minLat,maxLong,maxLat>',
    help='Geographic bounding box (e.g., 11,47,12,48 for Alpine region)'
)

search_group.add_argument(
    '--search-year-from',
    type=int,
    metavar='<year>',
    help='Year not before (use negative for BC, e.g., -50 for 50 BC)'
)

search_group.add_argument(
    '--search-year-to',
    type=int,
    metavar='<year>',
    help='Year not after (e.g., 200 for 200 AD)'
)

search_group.add_argument(
    '--search-limit',
    type=int,
    default=100,
    metavar='<n>',
    help='Maximum inscriptions to download (default: 100)'
)

search_group.add_argument(
    '--search-workers',
    type=int,
    default=10,
    metavar='<n>',
    help='Parallel download workers (default: 10, max: 50)'
)

search_group.add_argument(
    '--no-resume',
    action='store_true',
    help='Re-download files that already exist (default: skip existing)'
)
```

### 4. CLI Integration Logic

Add to `main()` in `latinepi/cli.py` after EDH single download handling:

```python
# Handle EDH search if requested
if args.search_edh:
    if not args.download_dir:
        print("Error: --download-dir is required when using --search-edh", file=sys.stderr)
        sys.exit(1)

    # Collect search parameters
    search_params = {
        'out_dir': args.download_dir,
        'province': args.search_province,
        'country': args.search_country,
        'fo_modern': args.search_findspot_modern,
        'fo_antik': args.search_findspot_ancient,
        'bbox': args.search_bbox,
        'year_from': args.search_year_from,
        'year_to': args.search_year_to,
        'max_results': args.search_limit,
        'workers': args.search_workers,
        'resume': not args.no_resume
    }

    try:
        downloaded_files = search_edh_inscriptions(**search_params)
        print(f"Successfully downloaded {len(downloaded_files)} inscriptions to {args.download_dir}")

        # If no input/output specified, we're done after download
        if not args.input:
            sys.exit(0)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Search failed: {e}", file=sys.stderr)
        sys.exit(1)
```

## Performance Considerations

### Rate Limiting Strategy

**Based on EDH_ETL findings:**
- EDH API successfully handled 300 parallel workers in production use
- 90,000 inscriptions downloaded in ~18 minutes
- This suggests robust API infrastructure

**Conservative defaults for latinepi:**
- Default workers: 10 (safe for most users)
- Maximum workers: 50 (good balance)
- Users can increase with `--search-workers` if needed

**Implementation details:**
- 0.1s delay between pagination requests
- 1s delay on errors before retry
- Single retry attempt on failure
- ThreadPoolExecutor for parallel downloads

### Resume Functionality

- **Default behavior**: Skip files that already exist (resume mode)
- **Rationale**: Large downloads may be interrupted; resuming saves time and bandwidth
- **Override**: Use `--no-resume` to force re-download

### Memory Efficiency

- Process search results in pages (20 items at a time from API)
- Accumulate metadata in memory until `max_results` reached
- Download files in parallel chunks
- Don't load file contents into memory during parallel save

## Example Usage

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
# Search, download, and immediately process
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

## Testing Strategy

### Unit Tests (test_edh_utils.py)

Add comprehensive tests for `search_edh_inscriptions()`:

1. **Parameter validation:**
   - Test with no parameters (should raise ValueError)
   - Test invalid bbox format (should raise ValueError)
   - Test with valid single parameter (province, country, etc.)

2. **API mocking:**
   - Mock paginated responses (simulate 3 pages of 20 items each)
   - Mock empty results
   - Mock API errors and verify retry logic
   - Mock timeout scenarios

3. **Parallel download:**
   - Test ThreadPoolExecutor with mocked save operations
   - Verify progress tracking
   - Test resume functionality (skip existing files)

4. **Search parameter combinations:**
   - Test geographic + temporal filters
   - Test wildcard findspots
   - Test bbox parsing and formatting

### CLI Tests (test_cli.py)

Add integration tests for search CLI:

1. **Argument validation:**
   - Test `--search-edh` without `--download-dir`
   - Test search parameter combinations
   - Test `--search-limit` and `--search-workers` validation

2. **Mocked end-to-end:**
   - Mock `search_edh_inscriptions()` and verify CLI calls it correctly
   - Verify output messages and exit codes
   - Test standalone search (no `--input`/`--output`)

### Example Test Code

```python
@patch('requests.get')
def test_search_with_pagination(self, mock_get):
    """Test search with paginated results."""
    # Mock 3 pages of results
    page1 = Mock()
    page1.json.return_value = {
        'items': [{'id': f'HD{i:06d}'} for i in range(1, 21)],
        'total': 50,
        'offset': 0,
        'limit': 20
    }
    page2 = Mock()
    page2.json.return_value = {
        'items': [{'id': f'HD{i:06d}'} for i in range(21, 41)],
        'total': 50,
        'offset': 20,
        'limit': 20
    }
    page3 = Mock()
    page3.json.return_value = {
        'items': [{'id': f'HD{i:06d}'} for i in range(41, 51)],
        'total': 50,
        'offset': 40,
        'limit': 20
    }

    mock_get.side_effect = [page1, page2, page3]

    # Search with max_results=50
    files = search_edh_inscriptions(
        out_dir=self.temp_dir,
        province="Dalmatia",
        max_results=50,
        workers=1
    )

    # Verify 3 API calls made
    self.assertEqual(mock_get.call_count, 3)

    # Verify 50 files returned
    self.assertEqual(len(files), 50)
```

## Documentation Updates

### 1. Update SETUP.md

Add section on EDH search:

```markdown
## Downloading Inscriptions from EDH

### Individual Download
latinepi --download-edh HD000001 --download-dir ./edh/

### Bulk Search and Download
latinepi --search-edh --search-province "Dalmatia" \
         --search-limit 500 --download-dir ./dalmatia/
```

### 2. Update spec.md

Update command-line options section to include all search parameters.

### 3. Update README (if exists)

Add examples of search workflows for common research scenarios.

## Migration Path

### Phase 1: Implementation
1. Implement `search_edh_inscriptions()` in `edh_utils.py`
2. Add CLI arguments in `cli.py`
3. Integrate search logic into `main()`
4. Write comprehensive tests

### Phase 2: Testing
1. Test with small result sets (limit 10-20)
2. Test pagination with moderate sets (limit 100)
3. Test parallel downloads with larger sets (limit 500-1000)
4. Test error handling and resume functionality

### Phase 3: Documentation
1. Update all relevant documentation
2. Add examples to help text
3. Create usage guide with common research scenarios

## Open Questions

1. **API Rate Limits**: What are the actual rate limits? (Unknown - EDH_ETL used 300 workers successfully)
2. **Result Ordering**: How are search results ordered? By ID, by date, by findspot?
3. **Text Search**: Does the API support full-text search of inscription content?
4. **Material/Type Filters**: Are there additional filter parameters we haven't discovered?

## Future Enhancements

### Potential Additional Features

1. **Bulk ID Download**: Accept file with list of IDs
   ```bash
   latinepi --download-edh-list ids.txt --download-dir ./bulk/
   ```

2. **Export Metadata Only**: Download without full JSON
   ```bash
   latinepi --search-edh --search-province "Dalmatia" \
            --metadata-only --output metadata.csv
   ```

3. **Geographic Visualization**: Generate map of search results
   ```bash
   latinepi --search-edh --search-country "Italy" \
            --generate-map --map-output italy_map.html
   ```

4. **Search Result Preview**: Show count without downloading
   ```bash
   latinepi --search-edh --search-province "Dalmatia" \
            --count-only
   # Output: Found 1,234 inscriptions matching criteria
   ```

## References

- **EDH API Base**: https://edh.ub.uni-heidelberg.de/data/api
- **EDH_ETL Repository**: https://github.com/sdam-au/EDH_ETL
- **EDH_ETL Search Script**: scripts/1_1_py_EXTRACTION_edh-inscriptions-from-web-api.ipynb
- **EDH_ETL Geography Script**: scripts/1_0_py_EXTRACTING-GEOGRAPHIES.ipynb
- **EDH Web Interface**: https://edh.ub.uni-heidelberg.de/
- **SDAM R Package**: https://sdam-au.github.io/sdam/reference/get.edh.html

## Implementation Checklist

- [ ] Implement `search_edh_inscriptions()` function
- [ ] Add CLI arguments for search parameters
- [ ] Integrate search logic into main CLI flow
- [ ] Add pagination handling
- [ ] Implement parallel downloads with ThreadPoolExecutor
- [ ] Add resume functionality
- [ ] Implement retry logic with delays
- [ ] Write unit tests for search function
- [ ] Write CLI integration tests
- [ ] Update documentation (SETUP.md, spec.md)
- [ ] Add usage examples to help text
- [ ] Test with real EDH API (small datasets)
- [ ] Performance testing with larger datasets
- [ ] Update plan.md with new prompt for search feature
