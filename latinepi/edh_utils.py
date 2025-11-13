"""
Utility functions for downloading inscription data from the EDH API.

The Epigraphic Database Heidelberg (EDH) provides a public API for accessing
inscription data. This module provides utilities for downloading and saving
inscription metadata.
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

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
