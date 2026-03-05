"""Simplified AI client for LLM-powered threat generation."""

import json
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import litellm
from models import AIThreatsResponseList

logger = logging.getLogger(__name__)

# Define absolute path to prompt file
PROJECT_ROOT = Path(__file__).parent.parent
PROMPT_FILE = PROJECT_ROOT / "prompt.txt"


@dataclass
class AIClientOptions:
    """Runtime options used for LiteLLM completion requests."""

    temperature: float = 0.1
    response_format: bool = True
    api_base: Optional[str] = None
    timeout: int = 14400
    max_tokens: int = 24000
    enable_json_schema_validation: bool = True


def generate_threats(
    schema: Dict,
    model: Dict,
    model_name: str,
    options: Optional[AIClientOptions] = None,
) -> Dict[str, List[Dict]]:
    """Generate AI-powered threats for all in-scope components."""
    logger = logging.getLogger("threat_modeling.ai_client")
    logger.info("Starting threat generation...")
    options = options or AIClientOptions()
    
  
    # Prepare prompt
    prompt_template = PROMPT_FILE.read_text(encoding='utf-8')
    
    system_prompt = prompt_template.format(
        schema_json=json.dumps(schema, indent=2),
        model_json=json.dumps(model, indent=2),
    )
    
    try:
        logger.info(f"Calling LLM: {model_name}")

        # ============================================================================
        # CONFIGURATION: Adjust these settings based on your LLM provider
        # See README.md "Tested LLM Providers" section for recommended configurations
        # ============================================================================
        
        # JSON Schema Validation: Enable for OpenAI, xAI (comment out for Anthropic, Gemini, and some Novita models)
        litellm.enable_json_schema_validation = options.enable_json_schema_validation
        litellm.drop_params = True

        completion_kwargs = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "Analyze provided Threat Dragon model, generate threats and mitigations for elements and return a valid JSON following the rules.",
                },
            ],
            "temperature": options.temperature,
            "timeout": options.timeout,
            "max_tokens": options.max_tokens,
        }
        if options.response_format:
            # Requires JSON schema validation support from the LLM provider.
            completion_kwargs["response_format"] = AIThreatsResponseList
        if options.api_base:
            completion_kwargs["api_base"] = options.api_base

        response = litellm.completion(**completion_kwargs)
        
        # Parse response
        logger.debug(f"/\n\nResponse: {response}")
        try:
            ai_response = AIThreatsResponseList.model_validate_json(response.choices[0].message.content)
        except Exception:
            logger.warning("LLM returned invalid JSON. Trying to extract JSON...")
            # Try to find JSON substring
            match = re.search(r"\{.*\}", response.choices[0].message.content, re.S)
            if match:
                ai_response = AIThreatsResponseList.model_validate_json(match.group())
            else:
                raise

        
        logger.debug(f"/\n\nAI Response: {ai_response}")
        
        # Convert to expected format
        threats_data = {
            item.id: [threat.model_dump() for threat in item.threats] 
            for item in ai_response.items
        }
        
        total_threats = sum(len(threats) for threats in threats_data.values())
        logger.info(f"Generated {total_threats} threats for {len(threats_data)} elements")
        
        return threats_data
        
    except Exception as e:
        logger.error(f"LLM error: {str(e)}")
        raise ValueError(f"Error calling LLM: {str(e)}")
