"""LLM client used to generate threats."""

import json
import re
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Tuple
import litellm
from models import AIThreatsResponseList

PROJECT_ROOT = Path(__file__).parent.parent
PROMPT_FILE = PROJECT_ROOT / "prompt.txt"


def generate_threats(schema: Dict, model: Dict, api_key: str, model_name: str, temperature: float = 0.1, response_format: bool = False, api_base: str = None, timeout: int = 900) -> Tuple[Dict[str, List[Dict]], float]:
    """Generate threats for in-scope elements and return cost."""
    logger = logging.getLogger("threat_modeling.ai_client")
    logger.info("Starting threat generation...")
    
    # Build the system prompt from template + input data.
    prompt_template = PROMPT_FILE.read_text(encoding='utf-8')
    
    system_prompt = prompt_template.format(
        schema_json=json.dumps(schema, indent=2, ensure_ascii=False),
        model_json=json.dumps(model, indent=2, ensure_ascii=False)
    )
    
    # Let LiteLLM validate JSON when response_format is enabled.
    litellm.enable_json_schema_validation = response_format
    litellm.drop_params = True

    # Create the chat messages sent to the model.
    messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Analyze provided Threat Dragon model, generate threats and mitigations for elements and return a valid JSON following the rules."}
        ]

    logger.info(f"System token count: {litellm.token_counter(model=model_name, messages=messages)}")

    try:
        max_tokens = int(litellm.get_max_tokens(model=model_name))
    except Exception as e:
        logger.error("Problem with getting max tokens: Using default value of 100000.")
        max_tokens = 100000

    # Build LiteLLM completion options.
    completion_params = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "timeout": timeout,
        "max_tokens": max_tokens,
        "response_format": AIThreatsResponseList if response_format else None
    }


    if api_key:
        completion_params["api_key"] = api_key

    if api_base:
        completion_params["api_base"] = api_base
    
    params_log = (
        "Completion parameters:\n"
        f'  "model": {model_name}\n'
        f'  "temperature": {temperature}\n'
        f'  "response_format": {response_format}\n'
        f'  "api_base": {api_base}\n'
        f'  "timeout": {timeout}'
    )
    logger.info(params_log)

    # Call the model and keep progress logs running while we wait.
    logger.info(f"Calling LLM: {model_name}")
    request_started_at = time.monotonic()
    progress_stop = threading.Event()
    def log_completion_progress() -> None:
        progress_chars = 0
        line_width = 60
        while not progress_stop.wait(1):
            elapsed_seconds = int(time.monotonic() - request_started_at)
            progress_chars += 1
            if progress_chars > line_width:
                progress_chars = 1
            dots = "." * progress_chars
            padding = " " * (line_width - progress_chars)
            logger.info(
                "\rGeneration in progress [%s%s] (%ss elapsed)",
                dots,
                padding,
                elapsed_seconds,
            )

    progress_thread = threading.Thread(target=log_completion_progress, daemon=True)
    progress_thread.start()
    try:
        response = litellm.completion(**completion_params)
    finally:
        progress_stop.set()
        progress_thread.join(timeout=0.2)

    total_wait_seconds = int(time.monotonic() - request_started_at)
    logger.info(f"LLM response received after {total_wait_seconds}s.")

    # Pull estimated request cost from response metadata.
    response_cost = response._hidden_params.get("response_cost", 0.0)
    logger.info(f"Response cost: {response_cost}")
    logger.debug(f"\n\nResponse: {response}")
    
    # Parse the response into our Pydantic schema.
    try:
        ai_response = AIThreatsResponseList.model_validate_json(response.choices[0].message.content)
    except Exception:
        # Fallback: try to pull JSON out of plain text/markdown.
        logger.warning("LLM returned invalid JSON. Trying to extract JSON...")
        # We expect a top-level object with an "items" array.
        match = re.search(r'\{\s*"items"\s*:\s*\[.*?\]\s*\}', response.choices[0].message.content, re.S)
        if match:
            ai_response = AIThreatsResponseList.model_validate_json(match.group())
        else:
            raise
    
    logger.debug(f"\n\nAI Response: {ai_response}")
    
    # Convert Pydantic objects to plain dictionaries.
    threats_data = {
        item.id: [threat.model_dump() for threat in item.threats] 
        for item in ai_response.items
    }
    
    total_threats = sum(len(threats) for threats in threats_data.values())
    logger.info(f"Generated {total_threats} threats for {len(threats_data)} elements")
    
    return threats_data, response_cost