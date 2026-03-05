"""Validation helpers for AI-generated threat data."""

from typing import Dict, List
from dataclasses import dataclass
import logging

@dataclass
class ValidationResult:
    """Validation result payload."""
    is_valid: bool
    missing_elements: List[str]
    invalid_ids: List[str]
    warnings: List[str]
    info: List[str]
    stats: Dict[str, int]


class ThreatValidator:
    """Validate AI output against the Threat Dragon model."""
    
    def validate_ai_response(self, model: dict, ai_response: List[dict]) -> ValidationResult:
        """Validate AI response against the original model."""
        # Collect in-scope element IDs.
        in_scope_elements = self._get_in_scope_elements(model)
        ai_element_ids = {item['id'] for item in ai_response}
        
        # Split IDs into missing (in scope) and out-of-scope.
        missing_elements = [elem_id for elem_id in in_scope_elements if elem_id not in ai_element_ids]
        out_of_scope_elements = [elem_id for elem_id in ai_element_ids if elem_id not in in_scope_elements]
        
        # Mark response invalid only if IDs do not overlap at all.
        all_model_elements = self._get_all_model_elements(model)
        has_overlap = len(ai_element_ids.intersection(all_model_elements)) > 0
        completely_unrelated = not has_overlap and len(ai_element_ids) > 0
        
        # Add quality warnings (including out-of-scope IDs).
        warnings = self._check_threat_quality(ai_response)
        warnings.extend([f"Element {elem_id} is not in scope but has threats" for elem_id in out_of_scope_elements])
        
        # Missing threats are informational, not fatal.
        info = [f"Element {elem_id} is in scope but has no threats" for elem_id in missing_elements]
        
        # Compute report stats.
        stats = self._calculate_stats(in_scope_elements, ai_element_ids, ai_response)
        
        result = ValidationResult(
            is_valid=not completely_unrelated,
            missing_elements=missing_elements,
            invalid_ids=out_of_scope_elements,
            warnings=warnings,
            info=info,
            stats=stats
        )
        return result
    
    def _get_in_scope_elements(self, model: dict) -> List[str]:
        """Return IDs for in-scope, non-boundary elements."""
        elements = []
        for diagram in model.get('detail', {}).get('diagrams', []):
            for cell in diagram.get('cells', []):
                cell_id = cell.get('id')
                cell_data = cell.get('data', {})
                cell_shape = cell.get('shape', '')
                
                # Include only normal in-scope elements with an ID.
                if (cell_id and 
                    not cell_data.get('outOfScope', False) and 
                    cell_shape not in ['trust-boundary-box', 'trust-boundary-curve']):
                    elements.append(cell_id)
        
        return elements
    
    def _get_all_model_elements(self, model: dict) -> set:
        """Return all element IDs in the model."""
        all_elements = set()
        for diagram in model.get('detail', {}).get('diagrams', []):
            for cell in diagram.get('cells', []):
                if cell.get('id'):
                    all_elements.add(cell.get('id'))
        return all_elements
    
    def _check_threat_quality(self, ai_response: List[dict]) -> List[str]:
        """Return non-fatal quality warnings."""
        warnings = []
        for item in ai_response:
            for i, threat in enumerate(item.get('threats', [])):
                if not threat.get('mitigation', '').strip():
                    warnings.append(f"Element {item['id']} threat {i+1} has empty mitigation")
        return warnings
    
    def _calculate_stats(self, in_scope_elements: List[str], ai_element_ids: set, ai_response: List[dict]) -> Dict[str, int]:
        """Build validation summary statistics."""
        total_threats = sum(len(item.get('threats', [])) for item in ai_response)
        coverage = (len(ai_element_ids) / len(in_scope_elements) * 100) if in_scope_elements else 0
        
        return {
            'in_scope_elements': len(in_scope_elements),
            'elements_with_threats': len(ai_element_ids),
            'total_threats': total_threats,
            'coverage_percent': round(coverage, 1)
        }
    
    def print_summary(self, logger: logging.Logger, result: ValidationResult):
        """Print a validation summary to the logger."""
        logger.info("")
        logger.info("="*60)
        logger.info("THREAT VALIDATION SUMMARY")
        logger.info("="*60)
        logger.info("Note: Trust boundary boxes and curves are excluded from validation")
        logger.info("Note: Missing elements are informational, not errors")
        logger.info("Note: Invalid IDs (out of scope) are warnings, not errors")
        logger.info("Note: Only completely different IDs are validation errors")
        
        logger.info("Overall Status: %s", "✅ VALID" if result.is_valid else "❌ INVALID")
        logger.info("Elements in Scope: %s", result.stats['in_scope_elements'])
        logger.info("Elements with Threats: %s", result.stats['elements_with_threats'])
        logger.info("Coverage: %s%%", result.stats['coverage_percent'])
        logger.info("Total Threats Generated: %s", result.stats['total_threats'])
        
        if not result.is_valid:
            logger.error("")
            logger.error("❌ VALIDATION ERRORS:")
            logger.error("  • AI response contains completely different IDs with no overlap to model elements")
        
        if result.warnings:
            logger.warning("")
            logger.warning("⚠️  WARNINGS (%s):", len(result.warnings))
            for warning in result.warnings:
                logger.warning("  • %s", warning)
        
        if result.info:
            logger.info("")
            logger.info("ℹ️  INFO (%s):", len(result.info))
            for info_item in result.info:
                logger.info("  • %s", info_item)
        
        logger.info("="*60)