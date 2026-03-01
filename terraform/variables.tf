# terraform/variables.tf

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ca-central-1"
}

variable "project_name" {
  description = "Project name used as prefix for all resource names"
  type        = string
  default     = "data-capsule"
}

variable "expiry_hours" {
  description = "How many hours before a capsule expires"
  type        = number
  default     = 0.25
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}