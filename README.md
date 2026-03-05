# AI-Powered Threat Modeling Tool

![td-ai](assets/td-ai.png)

An intelligent threat modeling application that uses Large Language Models (LLMs) to automatically generate security threats and their mitigation proposals for Threat Dragon models.

## Features

- **AI-Powered Threat Generation**: Uses state-of-the-art LLMs to analyze system components and generate comprehensive security threats
- **Threat Framework Support**: Supports STRIDE threat modeling framework, however the code can be adjusted for others as well
- **Multi-LLM Support**: Tested on OpenAI, Anthropic, Google, Novita, and xAI. As the code uses LiteLLM library, it should work with other models as well.
- **Threat Dragon Integration**: Works seamlessly with Threat Dragon JSON models
- **Smart Filtering**: Automatically skips out-of-scope components
- **Data Validation**: Built-in Pydantic validation for threat data integrity
- **Response Validation**: Comprehensive validation of AI responses against original models
- **Validation Logging**: Timestamped validation logs with detailed coverage reports
- **Visual Indicators**: Automatically adds visual cues (red strokes) to components with threats

## Quick Start

### Prerequisites

- Python 3.8+
- API key for your chosen LLM provider

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd td-ai-modeler
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # Choose your LLM provider (uncomment one)
   LLM_MODEL_NAME=openai/gpt-5
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Schema file from assets/
   THREAT_SCHEMA_JSON=owasp.threat-dragon.schema.V2.json
   ```

4. **Prepare files**
   - The Threat Dragon schema file is read from `./assets/`
   - Choose your threat model JSON at runtime in the GUI (`Open Model`)

5. **Run the GUI application**
   ```bash
   python src/main.py
   ```

6. **Check results**
   - Updated model with AI-generated threats is saved to the selected model file
   - Validation logs with timestamp are generated in `./logs/`

## Configuration

### Tested LLM Providers

| Provider | Model | API Key Variable | Recommended Configuration |
|----------|-------|------------------|---------------------------|
| **Anthropic** | `anthropic/claude-sonnet-4-5-20250929` | `ANTHROPIC_API_KEY` | `# litellm.enable_json_schema_validation = False`<br>`temperature = 0.1`<br>`# response_format = AIThreatsResponseList`<br>`max_tokens=24000` |
| **Anthropic** | `anthropic/claude-opus-4-1-20250805` | `ANTHROPIC_API_KEY` | `# litellm.enable_json_schema_validation = False`<br>`temperature = 0.1`<br>`# response_format = AIThreatsResponseList`<br>`max_tokens=24000` |
| **Novita** | `novita/deepseek/deepseek-r1` | `NOVITA_API_KEY` | `# litellm.enable_json_schema_validation = False`<br>`temperature = 0.1`<br>`# response_format = AIThreatsResponseList`<br>`max_tokens=16000` |
| **Novita** | `novita/qwen/qwen3-coder-480b-a35b-instruct` | `NOVITA_API_KEY` | `# litellm.enable_json_schema_validation = False`<br>`temperature = 0.1`<br>`# response_format = AIThreatsResponseList`<br>`max_tokens=24000` |
| **Novita** | `novita/deepseek/deepseek-v3.1-terminus` | `NOVITA_API_KEY` | `# litellm.enable_json_schema_validation = False`<br>`temperature = 0.1`<br>`# response_format = AIThreatsResponseList`<br>`max_tokens=24000` |
| **Local Ollama** | `ollama/gemma3:27b` | None | `# litellm.enable_json_schema_validation = False`<br>`# temperature = 0.1`<br>`response_format = AIThreatsResponseList`<br>`max_tokens=24000` |
| **xAI** | `xai/grok-4-fast-reasoning-latest` | `XAI_API_KEY` | `litellm.enable_json_schema_validation = True`<br>`temperature = 0.1`<br>`response_format = AIThreatsResponseList`<br>`max_tokens=24000` |
| **xAI** | `xai/grok-4-latest` | `XAI_API_KEY` | `litellm.enable_json_schema_validation = True`<br>`temperature = 0.1`<br>`response_format = AIThreatsResponseList`<br>`max_tokens=24000` |
| **OpenAI** | `openai/gpt-5` | `OPENAI_API_KEY` | `litellm.enable_json_schema_validation = True`<br>`temperature = 0.1`<br>`response_format = AIThreatsResponseList`<br>`max_tokens=24000` |
| **OpenAI** | `openai/gpt-5-mini` | `OPENAI_API_KEY` | `litellm.enable_json_schema_validation = True`<br>`temperature = 0.1`<br>`response_format = AIThreatsResponseList`<br>`max_tokens=24000` |
| **Google** | `gemini/gemini-2.5-pro` | `GOOGLE_API_KEY` | `# litellm.enable_json_schema_validation = False`<br>`temperature = 0.1`<br>`# response_format = AIThreatsResponseList`<br>`max_tokens=24000` |

#### Recommended Configuration Parameters

The recommended configuration settings in the table above include several key parameters that can be adjusted in `src/ai_client.py`:

- **`litellm.enable_json_schema_validation`**: Enables structured JSON validation for supported models. When prefixed with `#`, this parameter should be **commented out** (disabled) as the model doesn't support JSON schema validation.

- **`temperature`**: Controls the randomness and creativity of AI responses (0.0 = deterministic, 1.0 = very random). Lower values (0.1) provide more consistent, focused responses ideal for threat modeling.

- **`response_format`**: Forces the AI to return structured JSON using Pydantic models. When prefixed with `#`, this parameter should be **commented out** as the model doesn't support structured output.

- **`max_tokens`**: Maximum number of tokens the AI can generate in a single response. Higher values allow for more comprehensive threat descriptions but may increase processing time and costs.

**Important**: Parameters prefixed with `#` in the table should be **commented out** in your configuration, while parameters without `#` should be **uncommented** (active).

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_MODEL_NAME` | LLM model identifier | `openai/gpt-5` |
| `THREAT_SCHEMA_JSON` | Threat Dragon schema filename in `assets/` | `owasp.threat-dragon.schema.V2.json` |

### Advanced Configuration Options

The tool supports several advanced configuration options that can be modified in `src/ai_client.py`:

#### LLM Response Settings
- **`max_tokens`**: Maximum tokens in response (default: 24000)
- **`timeout`**: Request timeout in seconds (default: 14400 = 4 hours)

#### JSON Schema Validation
- **`litellm.enable_json_schema_validation`**: Enable structured JSON validation for supported models (OpenAI, xAI)
- **`response_format`**: Force structured JSON response format using Pydantic models

#### Custom API Endpoints
- **`api_base`**: Override default API endpoint for custom deployments or local models
  - Example: `api_base="https://your-custom-endpoint.com"` for custom deployments

#### LiteLLM Configuration
- **`litellm.drop_params`**: Remove unsupported parameters (default: True)

## Project Structure

```
td-ai-modeler/
├── src/
│   ├── main.py              # GUI application entry point
│   ├── gui.py               # Tkinter/ttkbootstrap desktop interface
│   ├── runtime.py           # Threat generation runtime orchestration
│   ├── ai_client.py         # LLM integration and threat generation
│   ├── utils.py             # File operations and model updates
│   ├── models.py            # Pydantic data models
│   └── validator.py         # AI response validation
├── assets/                  # App assets and threat schema file
│   └── owasp.threat-dragon.schema.V2.json
├── logs/                    # Runtime and validation logs
├── prompt.txt               # AI threat modeling prompt template
├── env.example              # Environment configuration template
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## How It Works

1. **Input Processing**: Loads Threat Dragon schema and model files
2. **AI Threat Generation**: Uses LLM to analyze components and generate threats
3. **Data Validation**: Ensures all generated threats have required fields
4. **Response Validation**: Validates AI response completeness and accuracy
5. **Model Update**: Updates the threat model while preserving original formatting
6. **Visual Updates**: Adds red stroke indicators to components with threats
7. **Validation Logging**: Generates detailed validation reports with timestamps

## Validation Features

The tool includes comprehensive validation to ensure AI responses are complete and accurate:

### Validation Categories
- **INFO**: Elements in scope but missing threats (informational)
- **WARNINGS**: Out-of-scope elements or quality issues (non-blocking)
- **ERRORS**: Completely different IDs with no model overlap (blocking)

### Validation Checks
- **Coverage Validation**: Ensures all in-scope elements (outOfScope=false) have threats
- **ID Validation**: Verifies all response IDs correspond to valid model elements
- **Quality Validation**: Checks that threats include proper mitigation strategies (empty mitigations generate warnings)
- **Data Integrity**: Validates threat structure and required fields

### Validation Outputs
- **Console Summary**: Real-time validation results with coverage statistics
- **Detailed Logs**: Timestamped logs in `./logs/` directory
- **Error Reporting**: Specific details about missing elements and invalid IDs
- **Coverage Metrics**: Percentage of in-scope elements with generated threats

### Validation Notes
- Trust boundary boxes and curves are excluded from validation
- Missing elements are informational, not errors
- Invalid IDs (out of scope) are warnings, not errors
- Only completely different IDs are validation errors

Validation runs automatically during threat generation and creates detailed logs in the `./logs/` directory.

## Troubleshooting

### Common Issues

#### LLM Response Errors
- **Invalid JSON**: The tool automatically attempts to extract JSON from malformed responses
- **Timeout Issues**: Increase `timeout` value in `ai_client.py` for large models
- **Token Limits**: Adjust `max_tokens` based on model capabilities

#### Validation Warnings
- **Missing Elements**: Normal for complex models - elements may be out of scope
- **Empty Mitigations**: Check AI response quality or adjust prompt template
- **Out-of-Scope Elements**: Elements not in scope but have threats generated
- **Invalid IDs**: Verify model structure and element IDs

#### Configuration Issues
- **API Key Errors**: Ensure correct environment variables are set
- **Model Not Found**: Verify model name format matches provider requirements
- **Connection Issues**: Check `api_base` URL for custom endpoints

### Performance Optimization

#### For Large Models
- Use `max_tokens=32000` for models with higher token limits
- Consider using faster models for initial threat generation

#### For Local Models (Ollama)
- Ensure sufficient hardware (GPU, CPU, RAM)
- Monitor system resources during generation

## Development

### Running the GUI Application

```bash
# Install development dependencies
pip install -r requirements.txt

# Run the GUI application
python src/main.py
```

### Code Structure

- **`main.py`**: GUI launcher entry point
- **`gui.py`**: Desktop user interface and interaction flow
- **`runtime.py`**: Core threat modeling orchestration used by GUI
- **`ai_client.py`**: Handles LLM communication and threat generation
- **`utils.py`**: File operations and model manipulation utilities
- **`models.py`**: Pydantic models for threat data validation
- **`validator.py`**: Comprehensive validation of AI responses

### Customization

#### Modifying the AI Prompt
Edit `prompt.txt` to customize threat generation behavior:
- Add specific threat frameworks
- Modify threat categories
- Adjust output format requirements

#### Adding New LLM Providers
1. Add provider configuration to `env.example`
2. Update provider table in README
3. Test with sample threat model


## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OWASP Threat Dragon](https://owasp.org/www-project-threat-dragon/) for the excellent threat modeling framework
- [LiteLLM](https://github.com/BerriAI/litellm) for seamless multi-LLM support
- [Pydantic](https://pydantic.dev/) for robust data validation

## Additional Resources

For more information about cybersecurity and AI projects, visit my blog at [https://infosecotb.com](https://infosecotb.com).

---

**Built for security professionals and threat modeling practitioners**
