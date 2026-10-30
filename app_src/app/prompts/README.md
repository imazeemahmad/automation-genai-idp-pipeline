# Bedrock Prompts

This directory contains all Bedrock prompt templates, organized by category.

## Structure

```
prompts/
├── config.yaml                                  ← Global default inference config
├── README.md                                    ← This file (excluded from scan)
└── biomarker/
    ├── extract_data.md                          ← Prompt template (user message)
    ├── extract_data_system.md                   ← System prompt (optional, dedicated file)
    └── extract_data_config.yaml                 ← Per-prompt override config
```

## How It Works

1. **Auto-discovery**: Terraform scans this directory recursively for `**/*.md`
   files (excluding `README.md` and `*_system.md`). Each discovered `.md` file
   becomes a Bedrock prompt resource automatically — no Terraform code change needed.

2. **Naming convention**: The deployed prompt name follows:
   ```
   pdb-emea-<category>-<prompt-name>-<env>[-<developer>]
   ```
   Example: `prompts/biomarker/extract_data.md`
   → `pdb-emea-biomarker-extract-data-sbx-developer-4`

3. **Configuration**:
   - `config.yaml` (root): Global defaults applied to all prompts
   - `<prompt_name>_config.yaml` (next to the `.md`): Per-prompt overrides

4. **System prompt resolution** (priority order):
   1. `<prompt_name>_system.md` file (if it exists next to the `.md`)
   2. `system_prompt` key in `<prompt_name>_config.yaml`
   3. `system_prompt` from `config.yaml` (global default)

   Using a dedicated `_system.md` file is recommended for long system prompts
   as it keeps the content readable and version-control friendly.

## Adding a New Prompt

1. Create a `.md` file in the appropriate category folder:
   ```
   prompts/biomarker/my_new_prompt.md
   ```

2. (Optional) Override inference settings by creating:
   ```
   prompts/biomarker/my_new_prompt_config.yaml
   ```
   with only the keys you want to override:
   ```yaml
   max_tokens: 8192
   temperature: 0.3
   stop_sequences:
     - "Human:"
   additional_model_request_fields: '{"thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"}}'
   ```

   You can also create the file with only comments (as a template for later):
   ```yaml
   ---
   # model_id: "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
   # max_tokens: 4096
   # temperature: 0
   # top_p: 0.9
   # stop_sequences:
   #   - "Human:"
   # additional_model_request_fields: '{"key": "value"}'
   # system_prompt: "Your system prompt here"
   ```
   This is valid — commented-only files are treated as no override.

3. (Optional) Create a dedicated system prompt file:
   ```
   prompts/biomarker/my_new_prompt_system.md
   ```
   This file contains the system prompt as plain text (no YAML, no markdown fences).
   It takes priority over the `system_prompt` key in the config YAML.

4. Run `terraform plan` — the new prompt will be picked up automatically.

## Per-Prompt Override Keys

The following keys are supported in a `_config.yaml` file:

| Key | Type | Description |
|-----|------|-------------|
| `model_id` | string | Bedrock model identifier |
| `max_tokens` | int | Maximum tokens in the response |
| `temperature` | float | Sampling temperature |
| `top_p` | float | Nucleus sampling parameter |
| `additional_model_request_fields` | JSON string | Extra model parameters (e.g., extended thinking, effort) |
| `stop_sequences` | list of strings | Sequences that stop generation (e.g., `["Human:"]`) |
| `system_prompt` | string | System prompt fallback (used if no `_system.md` file exists) |

## Global Defaults (config.yaml)

```yaml
model_id: "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
max_tokens: 4096
temperature: 0
top_p: 0.9
system_prompt: "Anwser in JSON format using the schema. DO not add additional comment. DO NOT add markdown formatting."
```

These values apply to every prompt unless overridden by a `_config.yaml` file.
