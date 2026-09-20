variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "financial-market-dashboard"
}

variable "s3_prefix" {
  type    = string
  default = "market-data"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "github_repository" {
  description = "GitHub owner/repository allowed to assume the deployment role"
  type        = string
  default     = ""
}

variable "github_environment" {
  description = "Protected GitHub environment allowed to assume the deployment role"
  type        = string
  default     = "production"
}

variable "terraform_state_bucket" {
  description = "Existing S3 state bucket the GitHub deployment role may access"
  type        = string
  default     = ""
}

variable "container_image_uri" {
  description = "Optional full ECR image URI; defaults to the latest tag in this stack's repository"
  type        = string
  default     = ""
}
