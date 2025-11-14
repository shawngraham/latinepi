"""
Tests for the parser module.
"""
import json
import tempfile
import unittest
from pathlib import Path

from latinepi.parser import read_inscriptions, extract_entities


class TestParser(unittest.TestCase):
    """Test cases for the parser functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)

    def test_read_csv_single_row(self):
        """Test reading a CSV file with a single inscription."""
        csv_file = self.temp_path / "test.csv"
        csv_content = """id,text,location
1,D M GAIVS IVLIVS CAESAR,Rome"""
        csv_file.write_text(csv_content)

        result = read_inscriptions(str(csv_file))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], '1')
        self.assertEqual(result[0]['text'], 'D M GAIVS IVLIVS CAESAR')
        self.assertEqual(result[0]['location'], 'Rome')

    def test_read_csv_multiple_rows(self):
        """Test reading a CSV file with multiple inscriptions."""
        csv_file = self.temp_path / "test.csv"
        csv_content = """id,text,location
1,D M GAIVS IVLIVS CAESAR,Rome
2,D M MARCIA TVRPILIA,Pompeii
3,HIC SITUS EST,Ostia"""
        csv_file.write_text(csv_content)

        result = read_inscriptions(str(csv_file))

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['id'], '1')
        self.assertEqual(result[1]['text'], 'D M MARCIA TVRPILIA')
        self.assertEqual(result[2]['location'], 'Ostia')

    def test_read_json_list_of_objects(self):
        """Test reading a JSON file with a list of inscription objects."""
        json_file = self.temp_path / "test.json"
        json_content = [
            {"id": 1, "text": "D M GAIVS IVLIVS CAESAR", "location": "Rome"},
            {"id": 2, "text": "D M MARCIA TVRPILIA", "location": "Pompeii"}
        ]
        json_file.write_text(json.dumps(json_content))

        result = read_inscriptions(str(json_file))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 1)
        self.assertEqual(result[0]['text'], 'D M GAIVS IVLIVS CAESAR')
        self.assertEqual(result[1]['location'], 'Pompeii')

    def test_read_json_single_object(self):
        """Test reading a JSON file with a single inscription object."""
        json_file = self.temp_path / "test.json"
        json_content = {"id": 1, "text": "D M GAIVS IVLIVS CAESAR", "location": "Rome"}
        json_file.write_text(json.dumps(json_content))

        result = read_inscriptions(str(json_file))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 1)
        self.assertEqual(result[0]['text'], 'D M GAIVS IVLIVS CAESAR')

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        with self.assertRaises(FileNotFoundError) as context:
            read_inscriptions("/nonexistent/file.csv")
        self.assertIn("File not found", str(context.exception))

    def test_unsupported_file_format(self):
        """Test that ValueError is raised for unsupported file formats."""
        txt_file = self.temp_path / "test.txt"
        txt_file.write_text("some text")

        with self.assertRaises(ValueError) as context:
            read_inscriptions(str(txt_file))
        self.assertIn("Unsupported file format", str(context.exception))

    def test_malformed_json(self):
        """Test that ValueError is raised for malformed JSON."""
        json_file = self.temp_path / "bad.json"
        json_file.write_text('{"id": 1, "text": "incomplete"')  # Missing closing brace

        with self.assertRaises(ValueError) as context:
            read_inscriptions(str(json_file))
        self.assertIn("JSON parsing error", str(context.exception))

    def test_json_with_invalid_structure(self):
        """Test that ValueError is raised for JSON with wrong structure."""
        json_file = self.temp_path / "bad.json"
        json_file.write_text('"just a string"')  # Not a dict or list

        with self.assertRaises(ValueError) as context:
            read_inscriptions(str(json_file))
        self.assertIn("JSON must be a list of objects or a single object", str(context.exception))

    def test_json_list_with_non_dict_items(self):
        """Test that ValueError is raised for JSON list containing non-dict items."""
        json_file = self.temp_path / "bad.json"
        json_content = [{"id": 1}, "string", {"id": 2}]  # Contains a string
        json_file.write_text(json.dumps(json_content))

        with self.assertRaises(ValueError) as context:
            read_inscriptions(str(json_file))
        self.assertIn("JSON list must contain only dictionaries", str(context.exception))

    def test_empty_csv(self):
        """Test that ValueError is raised for empty CSV file."""
        csv_file = self.temp_path / "empty.csv"
        csv_file.write_text("id,text,location\n")  # Header only, no data

        with self.assertRaises(ValueError) as context:
            read_inscriptions(str(csv_file))
        self.assertIn("empty or contains no data rows", str(context.exception))

    def test_csv_with_special_characters(self):
        """Test reading CSV with special characters and quotes."""
        csv_file = self.temp_path / "special.csv"
        csv_content = '''id,text,location
1,"D M, GAIVS ""IULIUS"" CAESAR","Rome, Italy"'''
        csv_file.write_text(csv_content)

        result = read_inscriptions(str(csv_file))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], 'D M, GAIVS "IULIUS" CAESAR')
        self.assertEqual(result[0]['location'], 'Rome, Italy')

    def test_json_with_nested_fields(self):
        """Test reading JSON with various field types."""
        json_file = self.temp_path / "test.json"
        json_content = {
            "id": 1,
            "text": "D M GAIVS IVLIVS CAESAR",
            "age": 57,
            "location": "Rome",
            "verified": True
        }
        json_file.write_text(json.dumps(json_content))

        result = read_inscriptions(str(json_file))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 1)
        self.assertEqual(result[0]['age'], 57)
        self.assertEqual(result[0]['verified'], True)

    def test_extract_entities_returns_dict(self):
        """Test that extract_entities returns a dictionary."""
        text = "D M GAIVS IVLIVS CAESAR"
        result = extract_entities(text)

        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

    def test_extract_entities_format(self):
        """Test that extract_entities returns the correct format."""
        text = "D M GAIVS IVLIVS CAESAR"
        result = extract_entities(text)

        # Check that each entity has the expected structure
        for entity_name, entity_data in result.items():
            self.assertIsInstance(entity_data, dict)
            self.assertIn('value', entity_data)
            self.assertIn('confidence', entity_data)
            self.assertIsInstance(entity_data['value'], str)
            self.assertIsInstance(entity_data['confidence'], float)
            self.assertGreaterEqual(entity_data['confidence'], 0.0)
            self.assertLessEqual(entity_data['confidence'], 1.0)

    def test_extract_entities_gaius_iulius_caesar(self):
        """Test extraction from a known inscription pattern."""
        text = "D M GAIVS IVLIVS CAESAR"
        result = extract_entities(text)

        # Should extract at least these entities
        self.assertIn('praenomen', result)
        self.assertEqual(result['praenomen']['value'], 'Gaius')

        self.assertIn('nomen', result)
        self.assertEqual(result['nomen']['value'], 'Iulius')

        self.assertIn('cognomen', result)
        self.assertEqual(result['cognomen']['value'], 'Caesar')

        self.assertIn('status', result)
        self.assertEqual(result['status']['value'], 'dis manibus')

    def test_extract_entities_marcus_antonius(self):
        """Test extraction from another name pattern."""
        text = "MARCVS ANTONIVS"
        result = extract_entities(text)

        self.assertIn('praenomen', result)
        self.assertEqual(result['praenomen']['value'], 'Marcus')

        self.assertIn('nomen', result)
        self.assertEqual(result['nomen']['value'], 'Antonius')

    def test_extract_entities_with_location(self):
        """Test extraction including location."""
        text = "GAIVS IVLIVS CAESAR ROMAE"
        result = extract_entities(text)

        self.assertIn('location', result)
        self.assertIn('Rom', result['location']['value'])

    def test_extract_entities_empty_text(self):
        """Test extraction from empty text."""
        text = ""
        result = extract_entities(text)

        # Should return at least something (fallback entity)
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

    def test_extract_entities_unknown_text(self):
        """Test extraction from text with no recognized patterns."""
        text = "UNKNOWN TEXT WITH NO NAMES"
        result = extract_entities(text)

        # Should return fallback entity
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)
        self.assertIn('text', result)

    def test_extract_entities_with_stub_explicit(self):
        """Test that extract_entities works with pattern matching."""
        text = "D M GAIVS IVLIVS CAESAR"

        # Should use pattern matching
        result = extract_entities(text)

        # Should extract all expected entities
        self.assertIsInstance(result, dict)
        self.assertIn('praenomen', result)
        self.assertEqual(result['praenomen']['value'], 'Gaius')

    def test_extract_tribe_abbreviated(self):
        """Test extraction of tribe in abbreviated form."""
        text = "C. IVLIVS CAESAR FAB."
        result = extract_entities(text)

        self.assertIn('tribe', result)
        self.assertEqual(result['tribe']['value'], 'Fabia')
        self.assertEqual(result['tribe']['confidence'], 0.85)

    def test_extract_tribe_full_form(self):
        """Test extraction of tribe in full form."""
        text = "C. IVLIVS CAESAR FABIA"
        result = extract_entities(text)

        self.assertIn('tribe', result)
        self.assertEqual(result['tribe']['value'], 'Fabia')
        self.assertEqual(result['tribe']['confidence'], 0.88)

    def test_extract_urban_tribe_esquilina(self):
        """Test extraction of urban tribe Esquilina."""
        text = "M. ANTONIVS FELIX ESQ."
        result = extract_entities(text)

        self.assertIn('tribe', result)
        self.assertEqual(result['tribe']['value'], 'Esquilina')

    def test_extract_urban_tribe_suburana(self):
        """Test extraction of urban tribe Suburana."""
        text = "L. CORNELIVS SCIPIO SVBVRANA"
        result = extract_entities(text)

        self.assertIn('tribe', result)
        self.assertEqual(result['tribe']['value'], 'Suburana')

    def test_extract_rural_tribe_galeria(self):
        """Test extraction of rural tribe Galeria."""
        text = "T. FLAVIVS ALEXANDER GALERIA"
        result = extract_entities(text)

        self.assertIn('tribe', result)
        self.assertEqual(result['tribe']['value'], 'Galeria')

    def test_extract_rural_tribe_velina_abbreviated(self):
        """Test extraction of rural tribe Velina in abbreviated form."""
        text = "P. AELIVS MAXIMVS VEL."
        result = extract_entities(text)

        self.assertIn('tribe', result)
        self.assertEqual(result['tribe']['value'], 'Velina')

    def test_extract_rural_tribe_scaptia(self):
        """Test extraction of rural tribe Scaptia."""
        text = "Q. SEMPRONIVS RVFVS SCAPTIA"
        result = extract_entities(text)

        self.assertIn('tribe', result)
        self.assertEqual(result['tribe']['value'], 'Scaptia')

    def test_extract_rural_tribe_lemonia(self):
        """Test extraction of rural tribe Lemonia."""
        text = "D M SEX. IVLIVS CAESAR LEM."
        result = extract_entities(text)

        self.assertIn('tribe', result)
        self.assertEqual(result['tribe']['value'], 'Lemonia')


if __name__ == "__main__":
    unittest.main()
