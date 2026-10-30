resource "aws_bedrockagent_prompt" "prompt" {
  for_each = local.bedrock_prompts

  name            = local.bedrock_prompt_names[each.key]
  description     = "Prompt: ${replace(replace(each.key, "/", " - "), "_", " ")}"
  default_variant = "default"

  variant {
    name          = "default"
    model_id      = each.value.model_id
    template_type = "CHAT"

    template_configuration {
      chat {
        system {
          text = fileexists("../app_src/app/prompts/${each.key}_system.md") ? file("../app_src/app/prompts/${each.key}_system.md") : each.value.system_prompt
        }

        message {
          role = "user"
          content {
            text = file("../app_src/app/prompts/${each.key}.md")
          }
        }
      }
    }

    inference_configuration {
      text {
        max_tokens     = each.value.max_tokens
        temperature    = each.value.temperature
        top_p          = each.value.top_p
        stop_sequences = try(each.value.stop_sequences, null)
      }
    }

    additional_model_request_fields = try(each.value.additional_model_request_fields, null)
  }

  tags = merge(local.standard_tags, {
    prompt_name     = replace(each.key, "/", "-")
    prompt_category = split("/", each.key)[0]
  })
}

resource "awscc_bedrock_prompt_version" "prompt_version" {
  for_each = local.bedrock_prompts

  prompt_arn  = aws_bedrockagent_prompt.prompt[each.key].arn
  description = "Version for ${replace(each.key, "/", " - ")}"

  lifecycle {
    replace_triggered_by = [aws_bedrockagent_prompt.prompt[each.key]]
  }
}
