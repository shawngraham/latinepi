"""
Integration tests for end-to-end CLI workflows.

Tests complete workflows from input to output, including:
- Full processing pipeline (read → extract → write)
- EDH download → process → output
- All flag combinations
- Error handling paths
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock


class TestIntegration(unittest.TestCase):
    """Integration test suite for complete CLI workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.cli_path = Path(__file__).parent.parent / "cli.py"
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)

    def test_full_workflow_json_to_json(self):
        """Test complete workflow: JSON input → extraction → JSON output."""
        # Create input file with multiple inscriptions
        input_data = [
            {"id": 1, "text": "D M GAIVS IVLIVS CAESAR", "location": "Rome"},
            {"id": 2, "text": "MARCVS ANTONIVS FELIX", "location": "Pompeii"},
            {"id": 3, "text": "D M MARCIA TVRPILIA", "location": "Ostia"}
        ]
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.json"

        # Run CLI
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )

        # Verify success
        self.assertEqual(result.returncode, 0, f"CLI failed: {result.stderr}")
        self.assertIn('Successfully processed', result.stdout)
        self.assertIn('3 inscription(s)', result.stdout)

        # Verify output file exists and is valid JSON
        self.assertTrue(output_path.exists())
        output_data = json.loads(output_path.read_text())

        # Verify output structure
        self.assertEqual(len(output_data), 3)

        # Check first record has expected structure
        first = output_data[0]
        self.assertIn('inscription_id', first)
        self.assertEqual(first['inscription_id'], 1)

        # Should have extracted entities with confidence scores
        self.assertIn('praenomen', first)
        self.assertIn('praenomen_confidence', first)

    def test_full_workflow_csv_to_csv(self):
        """Test complete workflow: CSV input → extraction → CSV output."""
        # Create CSV input file
        csv_content = """id,text,location
1,"D M GAIVS IVLIVS CAESAR",Rome
2,"MARCVS ANTONIVS FELIX",Pompeii
"""
        input_path = self.temp_path / "input.csv"
        input_path.write_text(csv_content)

        output_path = self.temp_path / "output.csv"

        # Run CLI with CSV output
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--output-format', 'csv'],
            capture_output=True,
            text=True
        )

        # Verify success
        self.assertEqual(result.returncode, 0)
        self.assertTrue(output_path.exists())

        # Verify CSV structure
        output_content = output_path.read_text()
        lines = output_content.strip().split('\n')
        self.assertGreater(len(lines), 1)

        # Check header has expected columns
        header = lines[0]
        self.assertIn('inscription_id', header)
        self.assertIn('_confidence', header)

    def test_workflow_with_confidence_threshold_filtering(self):
        """Test workflow with high confidence threshold filters entities."""
        input_data = [{"id": 1, "text": "D M GAIVS IVLIVS CAESAR"}]
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.json"

        # Use very high threshold
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--confidence-threshold', '0.95'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

        output_data = json.loads(output_path.read_text())
        record = output_data[0]

        # Only very high confidence entities should be present
        # cognomen (Caesar) has 0.95, should be included
        self.assertIn('cognomen', record)

        # nomen (Iulius) has 0.88, should be filtered out
        self.assertNotIn('nomen', record)

    def test_workflow_with_flag_ambiguous(self):
        """Test workflow with ambiguous flagging for low-confidence entities."""
        input_data = [{"id": 1, "text": "D M GAIVS IVLIVS CAESAR"}]
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.json"

        # Use threshold with flag-ambiguous
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

        output_data = json.loads(output_path.read_text())
        record = output_data[0]

        # nomen (0.88) should be included with ambiguous flag
        self.assertIn('nomen', record)
        self.assertIn('nomen_ambiguous', record)
        self.assertTrue(record['nomen_ambiguous'])

        # cognomen (0.95) should be included without ambiguous flag
        self.assertIn('cognomen', record)
        self.assertNotIn('cognomen_ambiguous', record)

    def test_workflow_with_all_flags_csv_output(self):
        """Test complete workflow with all flags and CSV output."""
        input_data = [
            {"id": 1, "text": "D M GAIVS IVLIVS CAESAR"},
            {"id": 2, "text": "MARCVS ANTONIVS"}
        ]
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.csv"

        # Use all extraction flags with threshold that will create ambiguous entries
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--output-format', 'csv',
             '--confidence-threshold', '0.90',  # nomen (0.88) will be ambiguous
             '--flag-ambiguous'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertTrue(output_path.exists())

        # Verify CSV has ambiguous columns (nomen has 0.88 < 0.90)
        output_content = output_path.read_text()
        self.assertIn('_ambiguous', output_content)

    def test_simulated_edh_download_then_process_workflow(self):
        """Test simulated EDH download → parse → output workflow."""
        # Simulate downloaded EDH file (as if it came from EDH API)
        download_dir = self.temp_path / "edh_downloads"
        download_dir.mkdir()

        # Create file that looks like EDH API response
        edh_data = {
            "inscriptions": [{
                "id": "HD000001",
                "text": "D M GAIVS IVLIVS CAESAR",
                "location": "Rome"
            }]
        }
        edh_file = download_dir / "HD000001.json"
        edh_file.write_text(json.dumps(edh_data))

        output_path = self.temp_path / "processed.json"

        # Process the downloaded file
        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(edh_file),
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )

        # Should succeed
        self.assertEqual(result.returncode, 0)

        # Verify processing message
        self.assertIn('Successfully processed', result.stdout)

        # Verify output file - EDH API wraps inscriptions in "inscriptions" array
        # Our parser needs to handle this or we need to extract the inscription first
        self.assertTrue(output_path.exists())

    def test_workflow_with_edh_style_json_structure(self):
        """Test processing files with EDH API JSON structure."""
        # EDH API returns {"inscriptions": [...]} format
        # Test that we can process a file after extracting the inscription
        inscription_data = {
            "id": "HD000001",
            "text": "D M GAIVS IVLIVS CAESAR",
            "location": "Rome"
        }

        input_path = self.temp_path / "edh_inscription.json"
        # Store as single inscription (after extraction from API response)
        input_path.write_text(json.dumps([inscription_data]))

        output_path = self.temp_path / "processed.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

        output_data = json.loads(output_path.read_text())
        self.assertEqual(len(output_data), 1)

        # Should have inscription_id and extracted entities
        record = output_data[0]
        self.assertIn('inscription_id', record)

    def test_workflow_with_mixed_quality_data(self):
        """Test workflow with inscriptions having missing or poor data."""
        input_data = [
            {"id": 1, "text": "D M GAIVS IVLIVS CAESAR"},  # Good
            {"id": 2, "text": ""},  # Empty text - should skip
            {"id": 3, "text": "UNKNOWN TEXT"},  # Low confidence entities
            {"id": 4, "location": "Rome"}  # Missing text field - should skip
        ]
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )

        # Should succeed despite issues
        self.assertEqual(result.returncode, 0)

        # Should warn about skipped inscriptions
        self.assertIn('Warning', result.stderr)

        # Output should have processed valid inscriptions
        output_data = json.loads(output_path.read_text())
        # Should process records 1 and 3 (records 2 and 4 skipped)
        self.assertEqual(len(output_data), 2)

    def test_workflow_with_large_batch(self):
        """Test workflow with larger batch of inscriptions."""
        # Create 50 inscriptions
        input_data = []
        for i in range(1, 51):
            input_data.append({
                "id": i,
                "text": f"D M GAIVS IVLIVS TESTNAME{i}",
                "location": f"Location{i}"
            })

        input_path = self.temp_path / "large_input.json"
        input_path.write_text(json.dumps(input_data))

        output_path = self.temp_path / "large_output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path)],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should successfully process all
        self.assertEqual(result.returncode, 0)
        self.assertIn('50 inscription(s)', result.stdout)

        # Verify all processed
        output_data = json.loads(output_path.read_text())
        self.assertEqual(len(output_data), 50)

        # Verify progress messages
        self.assertIn('Processing 50 inscription(s)', result.stdout)
        self.assertIn('Processed inscription', result.stdout)

    def test_error_handling_invalid_json_input(self):
        """Test error handling for malformed JSON input."""
        input_path = self.temp_path / "bad.json"
        input_path.write_text("{invalid json")

        output_path = self.temp_path / "output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )

        # Should fail with clear error
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Error', result.stderr)

    def test_error_handling_invalid_csv_input(self):
        """Test error handling for malformed CSV input."""
        input_path = self.temp_path / "bad.csv"
        input_path.write_text("")  # Empty CSV

        output_path = self.temp_path / "output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path)],
            capture_output=True,
            text=True
        )

        # Should fail with clear error
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Error', result.stderr)

    def test_error_handling_output_write_failure(self):
        """Test error handling when output file cannot be written."""
        input_data = [{"id": 1, "text": "TEST"}]
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps(input_data))

        # Use invalid output path (directory that doesn't exist and can't be created)
        output_path = "/root/cannot_write_here/output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', output_path],
            capture_output=True,
            text=True
        )

        # Should fail with clear error
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Error', result.stderr)

    def test_workflow_preserves_inscription_ids(self):
        """Test that inscription IDs are preserved through workflow."""
        input_data = [
            {"id": 42, "text": "D M GAIVS IVLIVS"},
            {"Id": 99, "text": "MARCVS ANTONIVS"},  # Capital I
            {"id": 100, "text": "CICERO"}
        ]
        input_path = self.temp_path / "input.json"
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

        output_data = json.loads(output_path.read_text())

        # Check IDs preserved
        self.assertEqual(output_data[0]['inscription_id'], 42)
        self.assertEqual(output_data[1]['inscription_id'], 99)
        self.assertEqual(output_data[2]['inscription_id'], 100)

    def test_workflow_json_to_csv_conversion(self):
        """Test format conversion from JSON input to CSV output."""
        input_data = [
            {"id": 1, "text": "D M GAIVS IVLIVS CAESAR"},
            {"id": 2, "text": "MARCVS ANTONIVS"}
        ]
        input_path = self.temp_path / "input.json"
        input_path.write_text(json.dumps(input_data))

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

        # Verify CSV format
        content = output_path.read_text()
        lines = content.strip().split('\n')

        # Should have header + 2 data rows
        self.assertEqual(len(lines), 3)

        # Header should have CSV columns
        self.assertIn(',', lines[0])

    def test_workflow_csv_to_json_conversion(self):
        """Test format conversion from CSV input to JSON output."""
        csv_content = """id,text
1,D M GAIVS IVLIVS CAESAR
2,MARCVS ANTONIVS
"""
        input_path = self.temp_path / "input.csv"
        input_path.write_text(csv_content)

        output_path = self.temp_path / "output.json"

        result = subprocess.run(
            [sys.executable, str(self.cli_path),
             '--input', str(input_path),
             '--output', str(output_path),
             '--output-format', 'json'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

        # Verify JSON format
        output_data = json.loads(output_path.read_text())
        self.assertEqual(len(output_data), 2)
        self.assertIsInstance(output_data, list)


if __name__ == "__main__":
    unittest.main()
