"""
Hybrid parser combining pattern matching, grammatical templates,
morphological analysis, and dependency parsing.

This is the main orchestration module that intelligently combines:
- Phase 0: Original pattern matching (fast, high confidence for known names)
- Phase 1: Grammatical templates (handles unknown names in formulaic positions)
- Phase 2: Morphological analysis (case-based entity extraction)
- Phase 3: Dependency parsing (complex relationships)
"""

from typing import Dict, Any, List, Optional
from latinepi.parser import _extract_entities_stub
from latinepi.grammar_patterns import (
    extract_with_grammar_templates,
    extract_unknown_names_by_position
)


class HybridLatinParser:
    """
    Hybrid parser combining multiple extraction strategies.

    Extraction strategy (progressive enhancement):
    1. Pattern matching → high confidence known names
    2. Grammar templates → medium confidence formulaic positions
    3. Morphology → case-based extraction for unknowns
    4. Dependencies → complex relationships

    Each phase adds to or validates previous phases.
    """

    def __init__(
        self,
        use_morphology: bool = True,
        use_dependencies: bool = False,
        min_confidence: float = 0.5
    ):
        """
        Initialize the hybrid parser.

        Args:
            use_morphology: Enable Phase 2 (morphological analysis)
            use_dependencies: Enable Phase 3 (dependency parsing)
            min_confidence: Minimum confidence threshold for entities
        """
        self.use_morphology = use_morphology
        self.use_dependencies = use_dependencies
        self.min_confidence = min_confidence

        # Lazy-load analyzers
        self._morphology_analyzer = None
        self._dependency_parser = None

    def _get_morphology_analyzer(self):
        """Lazy-load morphology analyzer."""
        if self._morphology_analyzer is None and self.use_morphology:
            try:
                from latinepi.morphology import get_morphology_analyzer
                self._morphology_analyzer = get_morphology_analyzer()
            except ImportError:
                print("Warning: CLTK not available. Morphology analysis disabled.")
                self.use_morphology = False
        return self._morphology_analyzer

    def _get_dependency_parser(self):
        """Lazy-load dependency parser."""
        if self._dependency_parser is None and self.use_dependencies:
            try:
                from latinepi.dependency import get_dependency_parser
                self._dependency_parser = get_dependency_parser()
            except ImportError:
                print("Warning: CLTK not available. Dependency parsing disabled.")
                self.use_dependencies = False
        return self._dependency_parser

    def extract_entities(
        self,
        text: str,
        verbose: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract entities using hybrid approach.

        Args:
            text: The inscription text to analyze
            verbose: If True, include metadata about extraction sources

        Returns:
            Dictionary of extracted entities with confidence scores
        """
        entities = {}

        # Phase 0: Pattern matching (original stub)
        pattern_entities = _extract_entities_stub(text)
        if verbose:
            for key, value in pattern_entities.items():
                value['extraction_phase'] = 'pattern_matching'
        entities.update(pattern_entities)

        # Phase 1: Grammatical templates
        grammar_entities = extract_with_grammar_templates(text)
        entities = self._merge_entities(
            entities,
            grammar_entities,
            prefer_higher_confidence=True,
            verbose=verbose,
            phase_name='grammar_templates'
        )

        # Phase 2: Morphological analysis (if enabled and needed)
        if self.use_morphology:
            morphology_needed = self._needs_morphology(entities)
            if morphology_needed:
                analyzer = self._get_morphology_analyzer()
                if analyzer:
                    morph_entities = analyzer.extract_entities_by_morphology(text)
                    entities = self._merge_entities(
                        entities,
                        morph_entities,
                        prefer_higher_confidence=True,
                        verbose=verbose,
                        phase_name='morphology'
                    )

        # Phase 3: Dependency parsing (if enabled and needed)
        if self.use_dependencies:
            dependency_needed = self._needs_dependencies(entities)
            if dependency_needed:
                parser = self._get_dependency_parser()
                if parser:
                    dep_entities = parser.extract_entities_by_dependencies(text)
                    entities = self._merge_entities(
                        entities,
                        dep_entities,
                        prefer_higher_confidence=True,
                        verbose=verbose,
                        phase_name='dependencies'
                    )

        # Filter by minimum confidence
        entities = self._filter_by_confidence(entities, self.min_confidence)

        # Consolidate duplicate entities from different sources
        entities = self._consolidate_entities(entities)

        return entities

    def _merge_entities(
        self,
        existing: Dict[str, Dict[str, Any]],
        new: Dict[str, Dict[str, Any]],
        prefer_higher_confidence: bool = True,
        verbose: bool = False,
        phase_name: str = ''
    ) -> Dict[str, Dict[str, Any]]:
        """
        Merge entities from different extraction phases.

        Args:
            existing: Existing entities
            new: New entities to merge
            prefer_higher_confidence: If True, keep entity with higher confidence
            verbose: Add extraction metadata
            phase_name: Name of the extraction phase

        Returns:
            Merged entities
        """
        merged = existing.copy()

        for key, value in new.items():
            if verbose and phase_name:
                value['extraction_phase'] = phase_name

            if key not in merged:
                # New entity, add it
                merged[key] = value
            else:
                # Entity exists, decide which to keep
                if prefer_higher_confidence:
                    existing_conf = merged[key].get('confidence', 0)
                    new_conf = value.get('confidence', 0)
                    if new_conf > existing_conf:
                        merged[key] = value
                    elif new_conf == existing_conf:
                        # Same confidence, add both sources
                        if verbose:
                            if 'alternative_extraction' not in merged[key]:
                                merged[key]['alternative_extraction'] = []
                            merged[key]['alternative_extraction'].append({
                                'value': value['value'],
                                'phase': phase_name
                            })

        return merged

    def _needs_morphology(self, entities: Dict[str, Dict[str, Any]]) -> bool:
        """
        Determine if morphological analysis is needed.

        Returns True if:
        - No deceased_name found
        - No dedicator found
        - Low overall entity count
        """
        has_deceased = any(k.startswith('deceased') for k in entities.keys())
        has_dedicator = any(k.startswith('dedicator') for k in entities.keys())
        entity_count = len(entities)

        # Need morphology if missing key entities or sparse extraction
        return not has_deceased or not has_dedicator or entity_count < 3

    def _needs_dependencies(self, entities: Dict[str, Dict[str, Any]]) -> bool:
        """
        Determine if dependency parsing is needed.

        Returns True if:
        - Complex inscription (multiple people, coordination)
        - Unclear relationships
        """
        # Check for coordination indicators
        has_multiple_dedicators = any(
            'dedicator_1' in k or 'dedicator_2' in k
            for k in entities.keys()
        )

        # Dependency parsing needed for complex cases
        return has_multiple_dedicators or len(entities) > 8

    def _filter_by_confidence(
        self,
        entities: Dict[str, Dict[str, Any]],
        min_confidence: float
    ) -> Dict[str, Dict[str, Any]]:
        """Filter entities by minimum confidence threshold."""
        return {
            key: value
            for key, value in entities.items()
            if value.get('confidence', 0) >= min_confidence
        }

    def _consolidate_entities(
        self,
        entities: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Consolidate duplicate entities from different sources.

        For example, if we have both 'deceased_name' and 'deceased_name_morphology',
        merge them into a single entity with the highest confidence.
        """
        consolidated = {}
        processed_groups = set()

        # Define entity groups that should be consolidated
        entity_groups = [
            ['deceased_name', 'deceased_name_morphology', 'deceased_name_dependency'],
            ['dedicator', 'dedicator_morphology', 'dedicator_dependency'],
            ['relationship', 'relationship_morphology', 'relationship_dependency',
             'deceased_relationship'],
            ['location', 'location_morphology'],
        ]

        for group in entity_groups:
            # Find all entities in this group
            found = [(key, entities[key]) for key in group if key in entities]

            if not found:
                continue

            # Find the one with highest confidence
            best_key, best_entity = max(found, key=lambda x: x[1].get('confidence', 0))

            # Use base name (without suffix)
            base_name = group[0]

            # Store consolidated entity
            consolidated[base_name] = best_entity.copy()
            consolidated[base_name]['confidence_sources'] = [
                {
                    'source': key,
                    'confidence': entity['confidence'],
                    'value': entity['value']
                }
                for key, entity in found
            ]

            # Update confidence (boost if multiple sources agree)
            if len(found) > 1:
                # Check if values agree
                values = [e[1]['value'] for e in found]
                if len(set(values)) == 1:
                    # All sources agree, boost confidence
                    current_conf = consolidated[base_name]['confidence']
                    consolidated[base_name]['confidence'] = min(
                        0.98,
                        current_conf + 0.05 * (len(found) - 1)
                    )
                    consolidated[base_name]['agreement'] = 'high'
                else:
                    consolidated[base_name]['agreement'] = 'low'

            # Mark this group as processed
            for key in group:
                processed_groups.add(key)

        # Add entities that weren't part of any group
        for key, value in entities.items():
            if key not in processed_groups and key not in consolidated:
                consolidated[key] = value

        return consolidated

    def get_extraction_report(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        Get detailed report of the extraction process.

        Useful for debugging and understanding how entities were extracted.

        Returns:
            Dictionary with:
            - entities: Extracted entities
            - phases_used: List of phases that were executed
            - morphology_analysis: Detailed morphology (if used)
            - dependency_tree: Dependency tree (if used)
            - statistics: Extraction statistics
        """
        report = {
            'text': text,
            'entities': {},
            'phases_used': ['pattern_matching', 'grammar_templates'],
            'statistics': {}
        }

        # Extract with verbose mode
        entities = self.extract_entities(text, verbose=True)
        report['entities'] = entities

        # Count entities by extraction phase
        phase_counts = {}
        for entity_data in entities.values():
            phase = entity_data.get('extraction_phase', 'unknown')
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        report['statistics']['entities_by_phase'] = phase_counts
        report['statistics']['total_entities'] = len(entities)

        # Add morphology analysis if enabled
        if self.use_morphology:
            analyzer = self._get_morphology_analyzer()
            if analyzer:
                report['phases_used'].append('morphology')
                report['morphology_analysis'] = analyzer.get_case_analysis(text)

        # Add dependency tree if enabled
        if self.use_dependencies:
            parser = self._get_dependency_parser()
            if parser:
                report['phases_used'].append('dependencies')
                report['dependency_tree'] = parser.get_dependency_tree(text)
                report['structural_analysis'] = parser.analyze_inscription_structure(text)

        return report


def extract_entities_hybrid(
    text: str,
    use_morphology: bool = True,
    use_dependencies: bool = False,
    min_confidence: float = 0.5,
    verbose: bool = False
) -> Dict[str, Dict[str, Any]]:
    """
    Convenience function for hybrid entity extraction.

    Args:
        text: Inscription text to analyze
        use_morphology: Enable morphological analysis (requires CLTK)
        use_dependencies: Enable dependency parsing (requires CLTK)
        min_confidence: Minimum confidence threshold
        verbose: Include extraction metadata

    Returns:
        Dictionary of extracted entities
    """
    parser = HybridLatinParser(
        use_morphology=use_morphology,
        use_dependencies=use_dependencies,
        min_confidence=min_confidence
    )
    return parser.extract_entities(text, verbose=verbose)
