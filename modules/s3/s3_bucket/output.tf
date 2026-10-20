output "bucket_name" {
  value       = aws_s3_bucket.bucket.id
  description = "Bucket name"
}

output "bucket_arn" {
  value       = aws_s3_bucket.bucket.arn
  description = "Bucket ARN"
}

output "hosted_zone_id" {
  value       = aws_s3_bucket.bucket.hosted_zone_id
  description = "Hosted zone ID (for Route53 alias records)"
}

output "bucket_regional_domain_name" {
  value       = aws_s3_bucket.bucket.bucket_regional_domain_name
  description = "Regional domain name of the bucket"
}

output "bucket_domain_name" {
  value       = aws_s3_bucket.bucket.bucket_domain_name
  description = "Domain name of the bucket"
}
