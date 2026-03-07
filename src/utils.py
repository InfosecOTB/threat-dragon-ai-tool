"""Helpers for JSON I/O and threat model updates."""

import json
import uuid
import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def load_json(path: Union[str, Path]) -> dict:
    """Load JSON from disk."""
    logger.info(f"Loading JSON from {path}")
    with open(str(path), 'r') as f:
        return json.load(f)


def update_threats_in_file(file_path: Union[str, Path], threats_data: dict) -> None:
    """Write generated threats into the Threat Dragon model file."""
    logger.info(f"Updating threats in file: {file_path}")
    
    with open(str(file_path), 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    updated_count = 0
    
    for diagram in data.get('detail', {}).get('diagrams', []):
        for cell in diagram.get('cells', []):
            cell_id = cell.get('id')
            if cell_id in threats_data:
                # Skip out-of-scope cells and trust boundaries.
                if (cell.get('data', {}).get('outOfScope') or \
                   cell.get('shape', '') in ['trust-boundary-box', 'trust-boundary-curve']):
                    continue

                # Some cell types do not include a data section by default.
                if 'data' not in cell:
                    cell['data'] = {}
                
                # Add missing IDs to threats before saving.
                threats_with_ids = []
                for threat in threats_data[cell_id]:
                    if 'id' not in threat:
                        threat['id'] = str(uuid.uuid4())
                    threats_with_ids.append(threat)

                cell['data']['threats'] = threats_with_ids
                
                # Refresh the hasOpenThreats flag when present.
                if 'hasOpenThreats' in cell['data']:
                    cell['data']['hasOpenThreats'] = any(
                        t.get('status', 'Open') == 'Open' for t in threats_data[cell_id]
                    )
                
                # Mark updated cells with a red stroke.
                _add_red_stroke(cell)
                updated_count += 1
    
    # Save the updated model file.
    with open(str(file_path), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, separators=(',', ': '), ensure_ascii=False)

    logger.info(f"Updated {updated_count} cells with threats")


def _add_red_stroke(cell: dict) -> None:
    """Apply a red stroke to a diagram cell."""
    if 'attrs' not in cell:
        cell['attrs'] = {'stroke': 'red'}
        return
    
    attrs = cell['attrs']
    
    # Different cell shapes store stroke color in different places.
    if 'line' in attrs:
        attrs['line']['stroke'] = 'red'
    elif 'body' in attrs:
        attrs['body']['stroke'] = 'red'
    elif 'topLine' in attrs:
        attrs['topLine']['stroke'] = 'red'
        if 'bottomLine' in attrs:
            attrs['bottomLine']['stroke'] = 'red'
    else:
        attrs['stroke'] = 'red'