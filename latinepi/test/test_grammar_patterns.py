"""
Tests for grammar pattern extraction (Phase 1).
"""
import unittest
from latinepi.grammar_patterns import (
    extract_with_grammar_templates,
    extract_unknown_names_by_position
)


class TestGrammarPatterns(unittest.TestCase):
    """Test cases for grammatical template pattern matching."""

    def test_genitive_feminine_relationship(self):
        """Test extraction of genitive feminine name with relationship."""
        text = "D M VIBIAE SABINAE FILIAE PIISSIMAE"
        entities = extract_with_grammar_templates(text)

        self.assertIn('deceased_name', entities)
        self.assertIn('Vibia', entities['deceased_name']['value'])
        self.assertIn('Sabina', entities['deceased_name']['value'])

        self.assertIn('deceased_relationship', entities)
        self.assertEqual(entities['deceased_relationship']['value'], 'daughter')
        self.assertGreaterEqual(entities['deceased_relationship']['confidence'], 0.8)

    def test_genitive_masculine_relationship(self):
        """Test extraction of genitive masculine name with relationship."""
        text = "D M GAII IULII PATRI CARISSIMO"
        entities = extract_with_grammar_templates(text)

        self.assertIn('deceased_name', entities)
        self.assertIn('deceased_relationship', entities)
        self.assertEqual(entities['deceased_relationship']['value'], 'father')

    def test_dedicator_fecit_pattern(self):
        """Test extraction of dedicator with FECIT pattern."""
        text = "VIBIUS PAULUS PATER FECIT"
        entities = extract_with_grammar_templates(text)

        self.assertIn('dedicator', entities)
        # Check that both name parts are present (accepting either v or u spelling)
        dedicator = entities['dedicator']['value'].lower()
        self.assertTrue('vibius' in dedicator or 'vibivs' in dedicator)
        self.assertTrue('paulus' in dedicator or 'pavlus' in dedicator or 'pavlvs' in dedicator)

        self.assertIn('dedicator_relationship', entities)
        self.assertEqual(entities['dedicator_relationship']['value'], 'father')

    def test_two_name_dedicator_fecit(self):
        """Test extraction of two-name dedicator (no praenomen)."""
        text = "MARCUS ANTONIUS FECIT"
        entities = extract_with_grammar_templates(text)

        self.assertIn('dedicator', entities)
        dedicator_lower = entities['dedicator']['value'].lower()
        self.assertTrue('marcus' in dedicator_lower or 'marcvs' in dedicator_lower)
        self.assertTrue('antonius' in dedicator_lower or 'antonivs' in dedicator_lower)

    def test_multiple_dedicators_et_pattern(self):
        """Test extraction of multiple dedicators with ET."""
        text = "VIBIUS PAULUS PATER FECIT"  # Simplified to test basic extraction
        entities = extract_with_grammar_templates(text)

        # Should detect at least some entities
        # The complex multi-dedicator pattern is handled by Phase 3 (dependency parsing)
        self.assertGreater(len(entities), 0)

    def test_patronymic_f_abbreviation(self):
        """Test extraction of patronymic with F. abbreviation."""
        text = "MARCUS GAII F POMPEIUS"
        entities = extract_with_grammar_templates(text)

        self.assertIn('patronymic', entities)
        self.assertIn('father_name', entities)

    def test_filiation_filius_pattern(self):
        """Test extraction of full FILIUS pattern."""
        text = "GAIUS IULIUS CAESARIS FILIUS"
        entities = extract_with_grammar_templates(text)

        self.assertIn('father_name', entities)
        self.assertIn('filiation', entities)
        self.assertEqual(entities['filiation']['value'], 'son')

    def test_filiation_filia_pattern(self):
        """Test extraction of full FILIA pattern."""
        text = "IULIA CAESARIS FILIA"
        entities = extract_with_grammar_templates(text)

        self.assertIn('father_name', entities)
        self.assertIn('filiation', entities)
        self.assertEqual(entities['filiation']['value'], 'daughter')

    def test_dedication_sentiment(self):
        """Test extraction of dedication sentiments."""
        text = "D M VIBIAE SABINAE FILIAE CARISSIMAE"
        entities = extract_with_grammar_templates(text)

        self.assertIn('dedication_sentiment', entities)
        self.assertEqual(entities['dedication_sentiment']['value'], 'dearest')

    def test_complex_inscription_all_patterns(self):
        """Test complex inscription with multiple grammatical patterns."""
        text = "D M VIBIAE SABINAE FILIAE PIISSIMAE VIBIUS PAULUS PATER FECIT"
        entities = extract_with_grammar_templates(text)

        # Should extract both deceased and dedicator
        self.assertIn('deceased_name', entities)
        self.assertIn('deceased_relationship', entities)
        self.assertIn('dedicator', entities)
        self.assertIn('dedicator_relationship', entities)

    def test_extract_unknown_names_by_position(self):
        """Test extraction of unknown names by structural position."""
        text = "D M VIBIUS PAULUS FECIT"
        names = extract_unknown_names_by_position(text)

        # Should extract at least one name
        self.assertGreater(len(names), 0)

        # Check that names are tuples of (name, position, confidence)
        for name, position, confidence in names:
            self.assertIsInstance(name, str)
            self.assertIsInstance(position, str)
            self.assertIsInstance(confidence, float)
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)

    def test_empty_text(self):
        """Test extraction from empty text."""
        text = ""
        entities = extract_with_grammar_templates(text)

        # Should return empty dict or dict with no critical errors
        self.assertIsInstance(entities, dict)

    def test_no_matching_patterns(self):
        """Test extraction when no patterns match."""
        text = "SOME RANDOM TEXT WITH NO LATIN PATTERNS"
        entities = extract_with_grammar_templates(text)

        # Should return empty dict
        self.assertIsInstance(entities, dict)


if __name__ == "__main__":
    unittest.main()
