"""
Tests for EDH download utility.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

try:
    from latinepi.edh_utils import download_edh_inscription, EDH_API_BASE
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from edh_utils import download_edh_inscription, EDH_API_BASE


class TestEDHUtils(unittest.TestCase):
    """Test cases for EDH download functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Sample EDH API response
        self.sample_response = {
            "inscriptions": [
                {
                    "id": "HD000001",
                    "text": "D M GAIVS IVLIVS CAESAR",
                    "location": "Rome",
                    "material": "marble",
                    "dating": "1st century AD"
                }
            ]
        }

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('requests.get')
    def test_download_inscription_success(self, mock_get):
        """Test successful download of an inscription."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_response
        mock_get.return_value = mock_response

        # Download inscription
        output_file = download_edh_inscription("HD000001", self.temp_dir)

        # Verify API was called correctly
        mock_get.assert_called_once_with(
            f"{EDH_API_BASE}/inscriptions/HD000001",
            timeout=30
        )

        # Verify file was created
        self.assertTrue(Path(output_file).exists())
        self.assertEqual(output_file, str(self.temp_path / "HD000001.json"))

        # Verify file contents
        with open(output_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(data, self.sample_response)

    @patch('requests.get')
    def test_download_with_numeric_id(self, mock_get):
        """Test downloading with numeric ID (should add HD prefix)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_response
        mock_get.return_value = mock_response

        # Download with numeric ID
        output_file = download_edh_inscription("123", self.temp_dir)

        # Verify HD prefix was added with zero-padding
        mock_get.assert_called_once_with(
            f"{EDH_API_BASE}/inscriptions/HD000123",
            timeout=30
        )

        # Verify file name has HD prefix
        self.assertTrue(output_file.endswith("HD000123.json"))

    @patch('requests.get')
    def test_download_creates_directory(self, mock_get):
        """Test that download creates output directory if it doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_response
        mock_get.return_value = mock_response

        # Use non-existent nested directory
        nested_dir = self.temp_path / "subdir" / "nested"

        # Download inscription
        output_file = download_edh_inscription("HD000001", str(nested_dir))

        # Verify directory was created
        self.assertTrue(nested_dir.exists())
        self.assertTrue(Path(output_file).exists())

    def test_download_empty_id_raises_error(self):
        """Test that empty inscription ID raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            download_edh_inscription("", self.temp_dir)

        self.assertIn("cannot be empty", str(cm.exception))

    def test_download_invalid_id_format_raises_error(self):
        """Test that invalid ID format raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            download_edh_inscription("INVALID", self.temp_dir)

        self.assertIn("Invalid inscription ID format", str(cm.exception))

    @patch('requests.get')
    def test_download_http_404_raises_error(self, mock_get):
        """Test that HTTP 404 raises error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            download_edh_inscription("HD999999", self.temp_dir)

    @patch('requests.get')
    def test_download_connection_error(self, mock_get):
        """Test that connection error is handled."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        with self.assertRaises(requests.HTTPError) as cm:
            download_edh_inscription("HD000001", self.temp_dir)

        self.assertIn("Connection error", str(cm.exception))

    @patch('requests.get')
    def test_download_timeout_error(self, mock_get):
        """Test that timeout error is handled."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        with self.assertRaises(requests.HTTPError) as cm:
            download_edh_inscription("HD000001", self.temp_dir)

        self.assertIn("timed out", str(cm.exception))

    @patch('requests.get')
    def test_download_invalid_json_response(self, mock_get):
        """Test that invalid JSON response raises error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as cm:
            download_edh_inscription("HD000001", self.temp_dir)

        self.assertIn("Invalid JSON", str(cm.exception))

    @patch('requests.get')
    def test_download_api_error_response(self, mock_get):
        """Test that API error response is handled."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Inscription not found"}
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as cm:
            download_edh_inscription("HD000001", self.temp_dir)

        self.assertIn("EDH API error", str(cm.exception))

    @patch('requests.get')
    def test_download_empty_inscriptions_response(self, mock_get):
        """Test that empty inscriptions response raises error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"inscriptions": []}
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as cm:
            download_edh_inscription("HD000001", self.temp_dir)

        self.assertIn("No inscription found", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
