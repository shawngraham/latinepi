"""
Tests for the CLI module.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestCLI(unittest.TestCase):
    """Test cases for the CLI functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cli_path = Path(__file__).parent.parent / "cli.py"
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)

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

    def test_nonexistent_input_file(self):
        """Test that supplying a non-existent input file returns error."""
        output_path = self.temp_path / "output.json"
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', 'nonexistent_file.csv',
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('does not exist', result.stderr)
        self.assertIn('nonexistent_file.csv', result.stderr)

    def test_successful_file_io(self):
        """Test that valid input and output files work correctly."""
        # Create a temporary input file
        input_path = self.temp_path / "input.csv"
        input_path.write_text("test data\n")

        output_path = self.temp_path / "output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )

        # Should succeed
        self.assertEqual(result.returncode, 0)

        # Check confirmation message in stdout
        self.assertIn('Successfully processed', result.stdout)
        self.assertIn(str(input_path), result.stdout)
        self.assertIn(str(output_path), result.stdout)

        # Check output file contains placeholder string
        self.assertTrue(output_path.exists())
        output_content = output_path.read_text()
        self.assertEqual(output_content, "latinepi: output placeholder\n")

    def test_output_format_argument(self):
        """Test that --output-format argument works correctly."""
        # Create a temporary input file
        input_path = self.temp_path / "input.csv"
        input_path.write_text("test data\n")

        output_path = self.temp_path / "output.csv"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--output-format', 'csv'],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('Successfully processed', result.stdout)

        # Verify output file was created with placeholder
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path.read_text(), "latinepi: output placeholder\n")


if __name__ == "__main__":
    unittest.main()
