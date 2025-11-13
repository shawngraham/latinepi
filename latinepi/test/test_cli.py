"""
Tests for the CLI module.
"""
import subprocess
import sys
import unittest
from pathlib import Path


class TestCLI(unittest.TestCase):
    """Test cases for the CLI functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cli_path = Path(__file__).parent.parent / "cli.py"

    def test_help_flag(self):
        """Test that running with --help prints usage message."""
        result = subprocess.run(
            [sys.executable, str(self.cli_path), '--help'],
            capture_output=True,
            text=True
        )
        # --help should print to stdout and exit with 0
        self.assertIn('usage:', result.stdout.lower())
        self.assertIn('latinepi', result.stdout)
        self.assertIn('--input', result.stdout)
        self.assertIn('--output', result.stdout)
        self.assertIn('--output-format', result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_missing_required_arguments(self):
        """Test that missing required arguments prints error to stderr."""
        # Test with no arguments
        result = subprocess.run(
            [sys.executable, str(self.cli_path)],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('required', result.stderr.lower())
        self.assertIn('--input', result.stderr)

    def test_missing_output_argument(self):
        """Test that missing --output argument prints error to stderr."""
        result = subprocess.run(
            [sys.executable, str(self.cli_path), '--input', 'test.csv'],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('required', result.stderr.lower())
        self.assertIn('--output', result.stderr)

    def test_missing_input_argument(self):
        """Test that missing --input argument prints error to stderr."""
        result = subprocess.run(
            [sys.executable, str(self.cli_path), '--output', 'test.json'],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('required', result.stderr.lower())
        self.assertIn('--input', result.stderr)

    def test_valid_arguments(self):
        """Test that valid arguments are accepted."""
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', 'test.csv',
             '--output', 'test.json'],
            capture_output=True,
            text=True
        )
        # Should succeed (even if files don't exist yet - we'll handle that in Prompt 3)
        self.assertEqual(result.returncode, 0)
        self.assertIn('Input: test.csv', result.stdout)
        self.assertIn('Output: test.json', result.stdout)
        self.assertIn('Format: json', result.stdout)

    def test_output_format_argument(self):
        """Test that --output-format argument works correctly."""
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', 'test.csv',
             '--output', 'test.csv',
             '--output-format', 'csv'],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('Format: csv', result.stdout)


if __name__ == "__main__":
    unittest.main()
