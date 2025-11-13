"""
Utility functions for downloading inscription data from the EDH API.

The Epigraphic Database Heidelberg (EDH) provides a public API for accessing
inscription data. This module provides utilities for downloading and saving
inscription metadata.
"""
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests


# EDH API base URL
EDH_API_BASE = "https://edh-www.adw.uni-heidelberg.de/data/api"


def download_edh_inscription(inscription_id: str, out_dir: str) -> str:
    """
    Download an inscription from the EDH API and save it as JSON.

    Args:
        inscription_id: The EDH inscription ID (e.g., "HD000001")
        out_dir: Directory to save the downloaded JSON file

    Returns:
        Path to the saved JSON file

    Raises:
        ValueError: If inscription_id is invalid or empty
        requests.HTTPError: If the API request fails
        OSError: If the output directory cannot be created or file cannot be written
    """
    # Validate inscription ID
    if not inscription_id or not inscription_id.strip():
        raise ValueError("Inscription ID cannot be empty")

    inscription_id = inscription_id.strip()

    # Ensure inscription ID has proper format (HDxxxxxx)
    if not inscription_id.upper().startswith('HD'):
        # Try to add HD prefix if it's just numbers
        if inscription_id.isdigit():
            inscription_id = f"HD{inscription_id.zfill(6)}"
        else:
            raise ValueError(f"Invalid inscription ID format: {inscription_id}. Expected format: HDxxxxxx")

    # Create output directory if it doesn't exist
    out_path = Path(out_dir)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Could not create output directory '{out_dir}': {e}")

    # Construct API URL
    # EDH API endpoint for individual inscriptions
    api_url = f"{EDH_API_BASE}/inscriptions/{inscription_id}"

    # Download inscription data
    try:
        print(f"Downloading inscription {inscription_id} from EDH API...", file=sys.stderr)
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx, 5xx)

        # Parse JSON response
        data = response.json()

        # Check if the response indicates the inscription was not found
        # EDH API may return 200 with an error message in some cases
        if isinstance(data, dict) and data.get('error'):
            raise ValueError(f"EDH API error: {data.get('error')}")

        if isinstance(data, dict) and not data.get('inscriptions'):
            # Empty or no inscriptions found
            raise ValueError(f"No inscription found with ID {inscription_id}")

    except requests.exceptions.Timeout:
        raise requests.HTTPError(f"Request timed out while fetching {inscription_id} from EDH API")
    except requests.exceptions.ConnectionError as e:
        raise requests.HTTPError(f"Connection error while fetching {inscription_id}: {e}")
    except requests.exceptions.RequestException as e:
        raise requests.HTTPError(f"Failed to download inscription {inscription_id}: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from EDH API: {e}")

    # Save to file
    output_file = out_path / f"{inscription_id}.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Saved inscription to {output_file}", file=sys.stderr)
        return str(output_file)

    except OSError as e:
        raise OSError(f"Could not write to file '{output_file}': {e}")


def search_edh_inscriptions(
    out_dir: str,
    province: Optional[str] = None,
    country: Optional[str] = None,
    fo_modern: Optional[str] = None,
    fo_antik: Optional[str] = None,
    bbox: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
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
    # Build search parameters
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
        # Validate bbox format: minLong,minLat,maxLong,maxLat
        if not re.match(r'^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$', bbox):
            raise ValueError("Invalid bbox format. Expected: minLong,minLat,maxLong,maxLat")
        search_params['bbox'] = bbox
    if year_from is not None:
        search_params['dat_jahr_a'] = year_from
    if year_to is not None:
        search_params['dat_jahr_e'] = year_to

    if not search_params:
        raise ValueError("At least one search parameter must be provided")

    # Create output directory
    out_path = Path(out_dir)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Could not create output directory '{out_dir}': {e}")

    # Phase 2: Paginated search
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
                response.raise_for_status()
                data = response.json()
                items = data.get('items', [])
                all_items.extend(items)
                offset += page_size
            except:
                break  # Give up on this page

    print(f"Search complete. Found {len(all_items)} inscriptions.", file=sys.stderr)

    if not all_items:
        print("No inscriptions found matching search criteria.", file=sys.stderr)
        return []

    # Phase 3: Parallel download
    def save_inscription(inscription_data):
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

        output_file = out_path / f"{insc_id}.json"

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

    # Parallel download with progress tracking
    saved_files = []
    workers_count = min(workers, 50)  # Cap at 50 workers

    print(f"Downloading {len(all_items)} inscriptions with {workers_count} workers...",
          file=sys.stderr)

    with ThreadPoolExecutor(max_workers=workers_count) as executor:
        # Submit all download tasks
        futures = {executor.submit(save_inscription, item): item
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
