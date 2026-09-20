output "dashboard_url" {
  value       = "http://${aws_lb.dashboard.dns_name}"
  description = "Public HTTP URL of the dashboard"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.dashboard.repository_url
}

output "data_bucket" {
  value = aws_s3_bucket.data.bucket
}

output "github_deploy_role_arn" {
  value       = try(aws_iam_role.github_actions[0].arn, null)
  description = "IAM role for GitHub Actions, when github_repository is configured"
}
