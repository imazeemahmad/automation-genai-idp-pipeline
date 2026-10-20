resource "aws_s3_bucket" "bucket" {
  bucket = var.bucket_name
  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:s3_bucket"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "1.2.0"
  })
}

# Object ownership stays with the bucket owner, not the principal doing the upload
resource "aws_s3_bucket_ownership_controls" "ownership" {
  bucket = aws_s3_bucket.bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Make the bucket private
resource "aws_s3_bucket_acl" "acl" {
  bucket     = aws_s3_bucket.bucket.id
  acl        = "private"
  depends_on = [aws_s3_bucket_ownership_controls.ownership]
}


# Block all public access
resource "aws_s3_bucket_public_access_block" "block" {
  bucket                  = aws_s3_bucket.bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versionning
resource "aws_s3_bucket_versioning" "versionning" {
  bucket = aws_s3_bucket.bucket.id
  versioning_configuration {
    status = var.versionning ? "Enabled" : "Disabled"
  }
}

# Always enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "encryption" {
  bucket = aws_s3_bucket.bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id != null ? var.kms_key_id : null
    }
    bucket_key_enabled = var.enable_bucket_key
  }
}

# Lifecyle rules (must only have 1 of these objects)
resource "aws_s3_bucket_lifecycle_configuration" "lifecycle" {
  bucket = aws_s3_bucket.bucket.id

  rule {
    id     = "Cleanup multipart upload"
    status = "Enabled"
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  dynamic "rule" {
    for_each = var.versionning ? [1] : []
    content {
      id     = "Expire old versions"
      status = "Enabled"
      noncurrent_version_expiration {
        noncurrent_days = 60
      }
    }
  }

  dynamic "rule" {
    for_each = var.lifecycle_rules
    content {
      id     = rule.value.id
      status = "Enabled"

      dynamic "filter" {
        for_each = rule.value.filter == null ? [true] : []
        content {}
      }

      dynamic "filter" {
        for_each = rule.value.filter != null ? [rule.value.filter] : []
        content {
          and {
            prefix                   = filter.value.prefix
            object_size_greater_than = filter.value.object_size_greater_than
            object_size_less_than    = filter.value.object_size_less_than
            dynamic "tag" {
              for_each = filter.value.tags != null ? filter.value.tags : {}
              content {
                key   = tag.key
                value = tag.value
              }
            }
          }
        }
      }

      dynamic "expiration" {
        for_each = rule.value.expiration != null ? [rule.value.expiration] : []
        content {
          days                         = expiration.value.days
          date                         = expiration.value.date
          expired_object_delete_marker = expiration.value.expired_object_delete_marker
        }
      }

      dynamic "transition" {
        for_each = rule.value.transition != null ? rule.value.transition : []
        content {
          days          = transition.value.days
          date          = transition.value.date
          storage_class = transition.value.storage_class
        }
      }
    }
  }
}

# Custom bucket policy (optional)
resource "aws_s3_bucket_policy" "policy" {
  bucket = aws_s3_bucket.bucket.id
  policy = var.bucket_policy
}

# S3 bucket notifications (optional)
resource "aws_s3_bucket_notification" "notifications" {
  count  = var.notifications != null ? 1 : 0
  bucket = aws_s3_bucket.bucket.id

  dynamic "lambda_function" {
    for_each = var.notifications.lambda_functions != null ? var.notifications.lambda_functions : []
    content {
      lambda_function_arn = lambda_function.value.lambda_function_arn
      events              = lambda_function.value.events
      filter_prefix       = lambda_function.value.filter_prefix
      filter_suffix       = lambda_function.value.filter_suffix
    }
  }

  dynamic "queue" {
    for_each = var.notifications.sqs_queues != null ? var.notifications.sqs_queues : []
    content {
      queue_arn     = queue.value.queue_arn
      events        = queue.value.events
      filter_prefix = queue.value.filter_prefix
      filter_suffix = queue.value.filter_suffix
    }
  }

  dynamic "topic" {
    for_each = var.notifications.sns_topics != null ? var.notifications.sns_topics : []
    content {
      topic_arn     = topic.value.topic_arn
      events        = topic.value.events
      filter_prefix = topic.value.filter_prefix
      filter_suffix = topic.value.filter_suffix
    }
  }
}

