"""
Threat Model Validation Module

Validates AI-generated threat models against original specifications.
Categories: INFO (missing elements), WARNINGS (quality issues), ERRORS (no overlap).
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass
import logging

# Define absolute paths
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGGER_NAME = "threat_modeling"


@dataclass
class ValidationResult:
    """Validation result container for threat model validation."""
    is_valid: bool
    missing_elements: List[str]
    invalid_ids: List[str]
    warnings: List[str]
    info: List[str]
    stats: Dict[str, int]


class ThreatValidator:
    """Validates AI-generated threat models against original specifications."""
    
    def __init__(self, logs_dir: Path = LOGS_DIR):
        """Initialize the threat validator."""
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir = logs_dir
    
    def validate_ai_response(self, model: dict, ai_response: List[dict], filename: str) -> ValidationResult:
        """Validate AI response against the original threat model."""
        # Extract in-scope elements that should have threats
        in_scope_elements = self._get_in_scope_elements(model)
        ai_element_ids = {item['id'] for item in ai_response}
        
        # Identify missing and out-of-scope elements
        missing_elements = [elem_id for elem_id in in_scope_elements if elem_id not in ai_element_ids]
        out_of_scope_elements = [elem_id for elem_id in ai_element_ids if elem_id not in in_scope_elements]
        
        # Check for completely unrelated responses (no overlap with any model elements)
        all_model_elements = self._get_all_model_elements(model)
        has_overlap = len(ai_element_ids.intersection(all_model_elements)) > 0
        completely_unrelated = not has_overlap and len(ai_element_ids) > 0
        
        # Collect quality warnings
        warnings = self._check_threat_quality(ai_response)
        warnings.extend([f"Element {elem_id} is not in scope but has threats" for elem_id in out_of_scope_elements])
        
        # Collect informational messages
        info = [f"Element {elem_id} is in scope but has no threats" for elem_id in missing_elements]
        
        # Calculate validation statistics
        stats = self._calculate_stats(in_scope_elements, ai_element_ids, ai_response)
        
        result = ValidationResult(
            is_valid=not completely_unrelated,
            missing_elements=missing_elements,
            invalid_ids=out_of_scope_elements,
            warnings=warnings,
            info=info,
            stats=stats
        )
        
        self._write_log(result, filename, ai_response)
        return result
    
    def _get_in_scope_elements(self, model: dict) -> List[str]:
        """Extract element IDs that should have threats generated."""
        elements = []
        for diagram in model.get('detail', {}).get('diagrams', []):
            for cell in diagram.get('cells', []):
                cell_id = cell.get('id')
                cell_data = cell.get('data', {})
                cell_shape = cell.get('shape', '')
                
                # Include if: in scope, not trust boundary, has ID
                if (cell_id and 
                    not cell_data.get('outOfScope', False) and 
                    cell_shape not in ['trust-boundary-box', 'trust-boundary-curve']):
                    elements.append(cell_id)
        
        return elements
    
    def _get_all_model_elements(self, model: dict) -> set:
        """Extract all element IDs from the model (including out-of-scope elements)."""
        all_elements = set()
        for diagram in model.get('detail', {}).get('diagrams', []):
            for cell in diagram.get('cells', []):
                if cell.get('id'):
                    all_elements.add(cell.get('id'))
        return all_elements
    
    def _check_threat_quality(self, ai_response: List[dict]) -> List[str]:
        """Check threat quality and return warnings for issues."""
        warnings = []
        for item in ai_response:
            for i, threat in enumerate(item.get('threats', [])):
                if not threat.get('mitigation', '').strip():
                    warnings.append(f"Element {item['id']} threat {i+1} has empty mitigation")
        return warnings
    
    def _calculate_stats(self, in_scope_elements: List[str], ai_element_ids: set, ai_response: List[dict]) -> Dict[str, int]:
        """Calculate validation statistics."""
        total_threats = sum(len(item.get('threats', [])) for item in ai_response)
        coverage = (len(ai_element_ids) / len(in_scope_elements) * 100) if in_scope_elements else 0
        
        return {
            'in_scope_elements': len(in_scope_elements),
            'elements_with_threats': len(ai_element_ids),
            'total_threats': total_threats,
            'coverage_percent': round(coverage, 1)
        }
    
    def _write_log(self, result: ValidationResult, filename: str, ai_response: List[dict]):
        """Write detailed validation log to file."""
        logger = logging.getLogger(LOGGER_NAME)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = self.logs_dir / f"validation_log_{filename.replace('.json', '')}_{timestamp}.log"
        
        content = f"""THREAT VALIDATION LOG
{'='*60}
Timestamp: {timestamp}
Model File: {filename}

VALIDATION NOTES:
- Trust boundary boxes and curves are excluded from validation
- Missing elements are informational, not errors
- Invalid IDs (out of scope) are warnings, not errors
- Only completely different IDs (no overlap with model) are validation errors

VALIDATION SUMMARY:
Overall Status: {'✅ VALID' if result.is_valid else '❌ INVALID'}
Elements in Scope: {result.stats['in_scope_elements']}
Elements with Threats: {result.stats['elements_with_threats']}
Total Threats Generated: {result.stats['total_threats']}
Coverage: {result.stats['coverage_percent']}%

VALIDATION RESULTS:
"""
        
        if not result.is_valid:
            content += f"\n❌ VALIDATION ERRORS:\n"
            content += f"  • AI response contains completely different IDs with no overlap to model elements\n"
        
        if result.warnings:
            content += f"\n⚠️  WARNINGS ({len(result.warnings)}):\n"
            for warning in result.warnings:
                content += f"  • {warning}\n"
        
        if result.info:
            content += f"\nℹ️  INFO ({len(result.info)}):\n"
            for info_item in result.info:
                content += f"  • {info_item}\n"
        
        content += f"\nAI RESPONSE PREVIEW:\n"
        content += f"Total Responses: {len(ai_response)}\n"
        content += f"Response IDs: {[item.get('id') for item in ai_response]}\n"
        
        try:
            with open(str(log_path), 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("Validation log saved to: %s", log_path)
        except Exception as e:
            logger.error("Failed to save validation log: %s", str(e))
    
    def print_summary(self, logger: logging.Logger, result: ValidationResult):
        """Print a formatted validation summary to console."""
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