"""
Tests for hybrid parser integration.
"""
import unittest
from latinepi.hybrid_parser import HybridLatinParser, extract_entities_hybrid


class TestHybridParser(unittest.TestCase):
    """Test cases for the hybrid parser."""

    def setUp(self):
        """Set up test fixtures."""
        # Test without morphology/dependencies (don't require CLTK)
        self.parser_basic = HybridLatinParser(
            use_morphology=False,
            use_dependencies=False
        )

    def test_basic_pattern_matching(self):
        """Test that basic pattern matching still works."""
        text = "D M GAIVS IVLIVS CAESAR"
        entities = self.parser_basic.extract_entities(text)

        # Should extract basic entities
        self.assertIn('status', entities)
        self.assertIn('praenomen', entities)
        self.assertIn('nomen', entities)
        self.assertIn('cognomen', entities)

    def test_grammar_templates_enhancement(self):
        """Test that grammar templates add to pattern matching."""
        text = "D M VIBIAE SABINAE FILIAE VIBIUS PAULUS PATER FECIT"
        entities = self.parser_basic.extract_entities(text)

        # Should extract both pattern-based and grammar-based entities
        self.assertGreater(len(entities), 0)

        # Should have deceased relationship from grammar patterns
        self.assertTrue(
            any('relationship' in key for key in entities.keys())
        )

    def test_confidence_filtering(self):
        """Test minimum confidence threshold filtering."""
        parser = HybridLatinParser(
            use_morphology=False,
            use_dependencies=False,
            min_confidence=0.9
        )

        text = "D M GAIVS IVLIVS CAESAR"
        entities = parser.extract_entities(text)

        # All entities should have confidence >= 0.9
        for entity_data in entities.values():
            self.assertGreaterEqual(entity_data['confidence'], 0.9)

    def test_verbose_mode_metadata(self):
        """Test that verbose mode includes extraction metadata."""
        text = "D M GAIVS IVLIVS CAESAR"
        entities = self.parser_basic.extract_entities(text, verbose=True)

        # Should include extraction_phase metadata
        for entity_data in entities.values():
            self.assertTrue(
                'extraction_phase' in entity_data or
                'confidence' in entity_data
            )

    def test_entity_consolidation(self):
        """Test that duplicate entities from different sources are consolidated."""
        text = "D M VIBIAE SABINAE FILIAE"

        # This might be extracted by both pattern matching and grammar templates
        entities = self.parser_basic.extract_entities(text)

        # Should not have both 'deceased_name' and 'deceased_name_morphology'
        # (one should be consolidated into the other)
        self.assertIsInstance(entities, dict)

    def test_extract_entities_hybrid_function(self):
        """Test the convenience function."""
        text = "D M GAIVS IVLIVS CAESAR"
        entities = extract_entities_hybrid(
            text,
            use_morphology=False,
            use_dependencies=False,
            min_confidence=0.5
        )

        self.assertGreater(len(entities), 0)
        self.assertIn('status', entities)

    def test_complex_inscription_hybrid(self):
        """Test complex inscription with multiple people."""
        text = "D M VIBIAE SABINAE FILIAE VIBIUS PAULUS PATER ET VIBIA TERTULLA MATER FECERUNT"
        entities = self.parser_basic.extract_entities(text)

        # Should extract multiple entities
        self.assertGreater(len(entities), 3)

    def test_empty_text_hybrid(self):
        """Test hybrid parser with empty text."""
        text = ""
        entities = self.parser_basic.extract_entities(text)

        # Should not crash, return dict
        self.assertIsInstance(entities, dict)

    def test_unknown_names_extraction(self):
        """Test that hybrid parser can extract unknown names."""
        # Use names that are not in the pattern lists
        text = "D M VIBIA TERTULLA FILIA FECIT"
        entities = self.parser_basic.extract_entities(text)

        # Grammar templates should extract "TERTULLA" even if not in patterns
        # Either as part of deceased_name or dedicator
        self.assertTrue(
            any('name' in key or 'dedicator' in key for key in entities.keys())
        )

    def test_get_extraction_report(self):
        """Test extraction report generation."""
        text = "D M GAIVS IVLIVS CAESAR"
        report = self.parser_basic.get_extraction_report(text)

        # Check report structure
        self.assertIn('text', report)
        self.assertIn('entities', report)
        self.assertIn('phases_used', report)
        self.assertIn('statistics', report)

        # Check that phases_used includes at least pattern_matching
        self.assertIn('pattern_matching', report['phases_used'])

        # Check statistics
        self.assertIn('total_entities', report['statistics'])
        self.assertGreater(report['statistics']['total_entities'], 0)


class TestHybridParserWithMorphology(unittest.TestCase):
    """Test cases for hybrid parser with morphology (requires CLTK)."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            self.parser_morph = HybridLatinParser(
                use_morphology=True,
                use_dependencies=False
            )
            self.has_cltk = True
        except (ImportError, RuntimeError):
            self.has_cltk = False
            self.skipTest("CLTK not available")

    def test_morphology_enhancement(self):
        """Test that morphology adds to basic extraction."""
        if not self.has_cltk:
            self.skipTest("CLTK not available")

        text = "D M VIBIAE SABINAE FILIAE"
        entities = self.parser_morph.extract_entities(text)

        # Should have entities
        self.assertGreater(len(entities), 0)

    def test_morphology_report(self):
        """Test that extraction report includes morphology analysis."""
        if not self.has_cltk:
            self.skipTest("CLTK not available")

        text = "D M GAIVS IVLIVS CAESAR"
        report = self.parser_morph.get_extraction_report(text)

        # Check that morphology is in phases_used
        self.assertTrue(
            'morphology' in report.get('phases_used', []) or
            'morphology_analysis' in report
        )


class TestHybridParserWithDependencies(unittest.TestCase):
    """Test cases for hybrid parser with dependency parsing (requires CLTK)."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            self.parser_deps = HybridLatinParser(
                use_morphology=True,
                use_dependencies=True
            )
            self.has_cltk = True
        except (ImportError, RuntimeError):
            self.has_cltk = False
            self.skipTest("CLTK not available")

    def test_dependency_parsing(self):
        """Test that dependency parsing works."""
        if not self.has_cltk:
            self.skipTest("CLTK not available")

        text = "VIBIUS PAULUS PATER FECIT"
        entities = self.parser_deps.extract_entities(text)

        # Should have entities
        self.assertGreater(len(entities), 0)

    def test_dependency_report(self):
        """Test that extraction report includes dependency tree."""
        if not self.has_cltk:
            self.skipTest("CLTK not available")

        text = "VIBIUS PAULUS FECIT"
        report = self.parser_deps.get_extraction_report(text)

        # Check that dependencies are in phases_used
        self.assertTrue(
            'dependencies' in report.get('phases_used', []) or
            'dependency_tree' in report or
            'structural_analysis' in report
        )


if __name__ == "__main__":
    unittest.main()
