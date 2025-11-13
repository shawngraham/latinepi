"""
Tests for the CLI module.
"""
import json
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
        self.assertIn('File not found', result.stderr)
        self.assertIn('nonexistent_file.csv', result.stderr)

    def test_successful_file_io(self):
        """Test that valid input and output files work correctly."""
        # Create a temporary input file with inscription data
        input_path = self.temp_path / "input.csv"
        csv_content = """id,text,location
1,D M GAIVS IVLIVS CAESAR,Rome"""
        input_path.write_text(csv_content)

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

        # Check progress messages in stdout
        self.assertIn('Processing', result.stdout)
        self.assertIn('Processed inscription', result.stdout)
        self.assertIn('Successfully processed', result.stdout)

        # Check output file exists and contains valid JSON
        self.assertTrue(output_path.exists())
        output_content = output_path.read_text()
        output_data = json.loads(output_content)

        # Should be a list with one result
        self.assertIsInstance(output_data, list)
        self.assertEqual(len(output_data), 1)

        # Check that entities were extracted
        record = output_data[0]
        self.assertIn('inscription_id', record)
        self.assertEqual(record['inscription_id'], '1')

        # Check for expected entities from the stub
        self.assertIn('praenomen', record)
        self.assertIn('praenomen_confidence', record)

    def test_output_format_argument(self):
        """Test that --output-format argument works correctly."""
        # Create a temporary input file with inscription data
        input_path = self.temp_path / "input.csv"
        csv_content = """id,text
1,D M GAIVS IVLIVS CAESAR"""
        input_path.write_text(csv_content)

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

        # Verify output file was created with CSV format
        self.assertTrue(output_path.exists())
        output_content = output_path.read_text()

        # Should have a CSV header row
        lines = output_content.strip().split('\n')
        self.assertGreater(len(lines), 1)
        # First line is header
        self.assertIn('inscription_id', lines[0])

    def test_entity_extraction_end_to_end(self):
        """Test complete entity extraction workflow with multiple inscriptions."""
        # Create input file with multiple inscriptions
        input_path = self.temp_path / "inscriptions.json"
        input_data = [
            {"id": 1, "text": "D M GAIVS IVLIVS CAESAR", "location": "Rome"},
            {"id": 2, "text": "MARCVS ANTONIVS", "location": "Alexandria"},
            {"id": 3, "text": "D M MARCIA TVRPILIA", "location": "Pompeii"}
        ]
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "entities.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )

        # Should succeed
        self.assertEqual(result.returncode, 0)

        # Check that all inscriptions were processed
        self.assertIn('Processing 3 inscription(s)', result.stdout)
        self.assertIn('Processed inscription 1/3', result.stdout)
        self.assertIn('Processed inscription 2/3', result.stdout)
        self.assertIn('Processed inscription 3/3', result.stdout)

        # Read and validate output
        output_data = json.loads(output_path.read_text())
        self.assertEqual(len(output_data), 3)

        # Verify first inscription
        first = output_data[0]
        self.assertEqual(first['inscription_id'], 1)
        self.assertIn('praenomen', first)
        self.assertEqual(first['praenomen'], 'Gaius')
        self.assertIn('nomen', first)
        self.assertEqual(first['nomen'], 'Iulius')
        self.assertIn('cognomen', first)
        self.assertEqual(first['cognomen'], 'Caesar')

        # Verify confidence scores are present
        self.assertIn('praenomen_confidence', first)
        self.assertIsInstance(first['praenomen_confidence'], float)
        self.assertGreaterEqual(first['praenomen_confidence'], 0.0)
        self.assertLessEqual(first['praenomen_confidence'], 1.0)


if __name__ == "__main__":
    unittest.main()
