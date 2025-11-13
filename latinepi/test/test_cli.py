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

    def test_confidence_threshold_default(self):
        """Test that default confidence threshold (0.5) filters entities correctly."""
        # Create input with text that will produce mixed confidence entities
        input_path = self.temp_path / "input.json"
        input_data = [{"id": 1, "text": "UNKNOWN TEXT WITH NO NAMES"}]
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

        # Read output
        output_data = json.loads(output_path.read_text())
        self.assertEqual(len(output_data), 1)

        # The stub returns 'text' entity with confidence 0.50 for unknown text
        # With default threshold of 0.5, entities with exactly 0.5 should be included
        record = output_data[0]
        self.assertIn('text', record)
        self.assertEqual(record['text_confidence'], 0.50)

    def test_confidence_threshold_high(self):
        """Test that high confidence threshold filters out more entities."""
        # Create input with known inscription
        input_path = self.temp_path / "input.json"
        input_data = [{"id": 1, "text": "D M GAIVS IVLIVS CAESAR"}]
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.json"

        # Use a high threshold that will filter out some entities
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--confidence-threshold', '0.90'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

        # Read output
        output_data = json.loads(output_path.read_text())
        self.assertEqual(len(output_data), 1)

        record = output_data[0]
        # cognomen (Caesar) has confidence 0.95, should be included
        self.assertIn('cognomen', record)
        self.assertEqual(record['cognomen'], 'Caesar')
        self.assertEqual(record['cognomen_confidence'], 0.95)

        # nomen (Iulius) has confidence 0.88, should be excluded (< 0.90)
        self.assertNotIn('nomen', record)

        # praenomen (Gaius) has confidence 0.91, should be included
        self.assertIn('praenomen', record)

    def test_confidence_threshold_low(self):
        """Test that low confidence threshold includes more entities."""
        # Create input with known inscription
        input_path = self.temp_path / "input.json"
        input_data = [{"id": 1, "text": "D M GAIVS IVLIVS CAESAR"}]
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.json"

        # Use a low threshold that includes all entities
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--confidence-threshold', '0.10'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

        # Read output
        output_data = json.loads(output_path.read_text())
        record = output_data[0]

        # All entities should be included
        self.assertIn('praenomen', record)
        self.assertIn('nomen', record)
        self.assertIn('cognomen', record)
        self.assertIn('status', record)

    def test_flag_ambiguous(self):
        """Test that --flag-ambiguous includes low-confidence entities with ambiguous flag."""
        # Create input with known inscription
        input_path = self.temp_path / "input.json"
        input_data = [{"id": 1, "text": "D M GAIVS IVLIVS CAESAR"}]
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.json"

        # Use high threshold with flag-ambiguous
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--confidence-threshold', '0.90',
             '--flag-ambiguous'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

        # Read output
        output_data = json.loads(output_path.read_text())
        record = output_data[0]

        # cognomen (Caesar) has confidence 0.95, should be included without ambiguous flag
        self.assertIn('cognomen', record)
        self.assertEqual(record['cognomen'], 'Caesar')
        self.assertNotIn('cognomen_ambiguous', record)

        # nomen (Iulius) has confidence 0.88 (< 0.90), should be included with ambiguous flag
        self.assertIn('nomen', record)
        self.assertEqual(record['nomen'], 'Iulius')
        self.assertEqual(record['nomen_confidence'], 0.88)
        self.assertIn('nomen_ambiguous', record)
        self.assertTrue(record['nomen_ambiguous'])

    def test_flag_ambiguous_with_csv(self):
        """Test that --flag-ambiguous works correctly with CSV output."""
        # Create input
        input_path = self.temp_path / "input.json"
        input_data = [{"id": 1, "text": "D M GAIVS IVLIVS CAESAR"}]
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.csv"

        # Use threshold with flag-ambiguous and CSV output
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--output-format', 'csv',
             '--confidence-threshold', '0.90',
             '--flag-ambiguous'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

        # Read CSV output
        output_content = output_path.read_text()
        lines = output_content.strip().split('\n')
        self.assertGreater(len(lines), 1)

        # Check that ambiguous column exists in header
        header = lines[0]
        self.assertIn('_ambiguous', header)

    def test_no_entities_meet_threshold(self):
        """Test behavior when no entities meet the confidence threshold."""
        # Create input with unknown text (low confidence)
        input_path = self.temp_path / "input.json"
        input_data = [{"id": 1, "text": "UNKNOWN TEXT"}]
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.json"

        # Use very high threshold
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--confidence-threshold', '0.99'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

        # Read output - should have record with only inscription_id (no entities)
        output_data = json.loads(output_path.read_text())
        self.assertEqual(len(output_data), 1)

        record = output_data[0]
        self.assertIn('inscription_id', record)
        # Should only have inscription_id, no entity fields
        self.assertEqual(len(record), 1)

    def test_edh_download_missing_download_dir(self):
        """Test that --download-edh without --download-dir prints error."""
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--download-edh', 'HD000001'],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--download-dir is required', result.stderr)

    def test_missing_input_with_output(self):
        """Test that --output without --input (and no --download-edh) prints error."""
        output_path = self.temp_path / "output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Either --download-edh, --search-edh, or --input must be specified', result.stderr)

    def test_missing_output_with_input(self):
        """Test that --input without --output prints error."""
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps([{"id": 1, "text": "test"}]))

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path)],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--output is required', result.stderr)

    def test_confidence_threshold_out_of_range_high(self):
        """Test that confidence threshold > 1.0 is rejected."""
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps([{"id": 1, "text": "test"}]))
        output_path = self.temp_path / "output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--confidence-threshold', '1.5'],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('must be between 0.0 and 1.0', result.stderr)
        self.assertIn('1.5', result.stderr)

    def test_confidence_threshold_out_of_range_low(self):
        """Test that confidence threshold < 0.0 is rejected."""
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps([{"id": 1, "text": "test"}]))
        output_path = self.temp_path / "output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--confidence-threshold', '-0.5'],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('must be between 0.0 and 1.0', result.stderr)

    def test_download_dir_without_download_edh(self):
        """Test that --download-dir without --download-edh shows warning."""
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps([{"id": 1, "text": "test"}]))
        output_path = self.temp_path / "output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--download-dir', './somedir/'],
            capture_output=True,
            text=True
        )

        # Should succeed but show warning
        self.assertEqual(result.returncode, 0)
        self.assertIn('Warning', result.stderr)
        self.assertIn('--download-dir', result.stderr)

    def test_help_shows_argument_groups(self):
        """Test that --help displays organized argument groups."""
        result = subprocess.run(
            [sys.executable, str(self.cli_path), '--help'],
            capture_output=True,
            text=True
        )

        # Check for argument group headers
        self.assertIn('Input/Output', result.stdout)
        self.assertIn('Entity Extraction Options', result.stdout)
        self.assertIn('EDH API Download', result.stdout)

    def test_no_arguments_shows_help_and_error(self):
        """Test that no arguments shows help and error message."""
        result = subprocess.run(
            [sys.executable, str(self.cli_path)],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0)
        # Should show help text
        self.assertIn('usage:', result.stderr.lower())
        # Should show error message
        self.assertIn('Either --download-edh, --search-edh, or --input must be specified', result.stderr)


if __name__ == "__main__":
    unittest.main()
