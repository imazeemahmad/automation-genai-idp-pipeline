resource "awscc_bedrock_data_automation_project" "ocr" {
  project_name = "${local.resource_prefix}-common-bda-ocr-${local.resource_suffix}"

  standard_output_configuration = {
    document = {
      extraction = {
        bounding_box = {
          state = "DISABLED"
        }
        granularity = {
          types = ["DOCUMENT", "PAGE", "ELEMENT"]
        }
      }
      generative_field = {
        state = "DISABLED"
      }
      output_format = {
        text_format = {
          types = ["MARKDOWN"]
        }
        additional_file_format = {
          state = "ENABLED"
        }
      }
    }
  }

  override_configuration = {
    image = {
      modality_processing = {
        state = "DISABLED"
      }
    }
    video = {
      modality_processing = {
        state = "DISABLED"
      }
    }
    audio = {
      modality_processing = {
        state = "DISABLED"
      }
    }
  }

  tags = [
    for k, v in local.standard_tags : {
      key   = k
      value = v
    }
  ]
}
