# Threat Dragon AI Tool

![Threat Dragon AI Tool](assets/td-ai.png)



A desktop application that automatically generates STRIDE threats and mitigations for [OWASP Threat Dragon](https://owasp.org/www-project-threat-dragon/) models using LLMs.

You open a Threat Dragon `.json` model file, pick an AI provider, and the tool analyzes the entire data-flow diagram - trust boundaries, flows, zones, encryption flags - then writes threats and mitigations directly back into the file. Open it in Threat Dragon and the threats are already there.

## Prerequisites
- An API key for at least one supported LLM provider

### Supported LLMs

The application uses the LiteLLM library, so any provider/model supported by LiteLLM should work. Use the [LiteLLM naming convention](https://docs.litellm.ai/docs/providers) (`provider/model`).

Generating threats and mitigations is a complex task that requires capable models. For good results, use a model with at least 400M parameters. The best results were achieved with Anthropic Claude, OpenAI GPT, and xAI Grok. Self-hosted DeepSeek and Qwen also produced good results in testing.

You can read more about testing different models and its results in my blog [AI-Powered Threat Modeling with OWASP Threat Dragon – Part 2: Generating Threats with Artificial Intelligence](https://infosecotb.com/ai-powered-threat-modeling-with-owasp-threat-dragon-part-2-generating-threats-with-artificial-intelligence/) 

## Installation
Copy `td-ai-tool.exe` to a folder and run it. 

### Instructions
1. **Configure** - Adjust the LLM model, temperature, API key and other settings in the left panel if needed. Settings from `.env` are pre-filled.

   ![Settings panel](assets/settings.png)

   Configuration fields:
   - `API Key` - API key for accessing the LLM service.
   - `LLM Model` - LLM model identifier, for example `openai/gpt-5`, `anthropic/claude-sonnet-4-5`, or `xai/grok-4`.
   - `Temperature` - Lower values make output more deterministic; higher values increase creativity and randomness. Valid range: `0` to `2`.
   - `Response Format` - Enables structured JSON output. Recommended for supported models such as `openai/gpt-5` or `xai/grok-4`. If enabled for an unsupported model, the request may fail.
   - `API Base URL` - Custom API base URL. Most hosted AI providers do not require this because LiteLLM handles it automatically.
   - `Log Level` - Logging level: `INFO` or `DEBUG`.
   - `Timeout` - Request timeout in seconds for LLM API calls. Default: `900` seconds (`15` minutes).


   Creating a `.env` file in the same folder as `td-ai-tool.exe` is optional; if present, the application will read settings from it. You can also enter settings in the application, but they are lost when you close it. For security and simplicity, saving settings from inside the application is not supported at this time.

### Optional `.env` variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | *(empty)* | LiteLLM model identifier |
| `API_KEY` | *(empty)* | Generic API key (auto-mapped to the right provider env var) |
| `API_BASE_URL` | *(empty)* | Custom API endpoint |
| `TEMPERATURE` | `0.1` | LLM temperature (0.0–2.0) |
| `RESPONSE_FORMAT` | `true` | Enforce JSON schema validation on the LLM response |
| `LOG_LEVEL` | `INFO` | `INFO` or `DEBUG` |
| `TIMEOUT` | `900` | Request timeout in seconds |

Example:

```dotenv
API_KEY="sk-proj-your_key"
LLM_MODEL=openai/gpt-5.2
TEMPERATURE=0.1
RESPONSE_FORMAT=true
API_BASE_URL=
LOG_LEVEL=INFO
TIMEOUT=900
```

2. **Open a model** - Click *Open Model* (or File → Open Model) and select a Threat Dragon `.json` file.

3. **Generate** - Click *Generate Threat and Mitigations*. A warning dialog will appear - read it, then confirm.

4. **Wait** - The console on the right shows progress. Depending on the model size and LLM provider, this can take from a few seconds to several minutes.

5. **Done** - The tool writes threats directly into your `.json` file and runs a validation pass. Open the file in Threat Dragon to see the results.

### Things to keep in mind

- **Close Threat Dragon first** before running the tool. Editing the JSON while Threat Dragon has it open can cause data loss.
- **Back up your model file.** The tool overwrites it in place. Existing threats may be kept, updated, or replaced.
- **Only STRIDE is supported.** Running this on models that use other methodologies (LINDDUN, CIA, etc.) may produce unexpected results.
- You can run the tool multiple times on the same file. Each run re-evaluates existing threats and may add new ones.

## How it works

### Architecture

```
main.py → gui.py → runtime.py → ai_client.py → LiteLLM → LLM provider
                                    ↓
                                utils.py (read/write JSON)
                                    ↓
                              validator.py (post-run checks)
```

The GUI collects user settings and kicks off `run_threat_modeling()` on a background thread. That function:

1. Loads the Threat Dragon JSON model and the OWASP schema.
2. Injects both into a system prompt (`prompt.txt`) that instructs the LLM to analyze the data-flow diagram using STRIDE.
3. Calls the LLM through LiteLLM and parses the structured JSON response (with a regex fallback if the model returns markdown-wrapped output).
4. Merges the generated threats back into the original file - each threat gets a UUID, affected cells get a red stroke indicator, and the `hasOpenThreats` flag is updated.
5. Validates the response: checks element ID overlap, coverage, threat quality, and prints a summary.

### Project structure

```
threat-dragon-ai-tool/
├── assets/
│   └── owasp.threat-dragon.schema.V2.json   # Threat Dragon V2 schema
├── src/
│   ├── main.py           # Entry point
│   ├── gui.py            # Tkinter/ttkbootstrap desktop UI
│   ├── runtime.py        # Orchestration (UI-agnostic)
│   ├── ai_client.py      # LLM integration via LiteLLM
│   ├── validator.py      # Post-generation response validation
│   ├── models.py         # Pydantic models for the AI response format
│   └── utils.py          # JSON file I/O, threat merging
├── prompt.txt            # System prompt template sent to the LLM
├── requirements.txt
├── env.example           # Example .env configuration
└── .env                  # Your local config (not tracked by git)
```

### Key dependencies

- **[LiteLLM](https://github.com/BerriAI/litellm)** - unified API wrapper that lets you swap LLM providers without changing code.
- **[Pydantic](https://docs.pydantic.dev/)** - validates and parses the structured JSON that comes back from the LLM.
- **[ttkbootstrap](https://ttkbootstrap.readthedocs.io/)** - modern-looking Tkinter theme for the GUI.
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** - loads `.env` defaults on startup.

### License
This project is licensed under the Apache 2.0 License - see the LICENSE file for details.

### Acknowledgments
- **[OWASP Threat Dragon](https://owasp.org/www-project-threat-dragon/)** for the excellent threat modeling framework
- **[LiteLLM](https://github.com/BerriAI/litellm)** for seamless multi-LLM support
- **[Pydantic](https://pydantic.dev/)** for robust data validation

### Additional Resources
For more information about cybersecurity and AI projects, visit my blog at https://infosecotb.com.


