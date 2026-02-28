# terraform/dynamodb.tf
# Stores capsule metadata with automatic TTL-based expiry

resource "aws_dynamodb_table" "capsules" {
  name           = "${var.project_name}-capsules"
  billing_mode   = "PAY_PER_REQUEST"  # No capacity planning needed
  hash_key       = "capsule_id"

  attribute {
    name = "capsule_id"
    type = "S"
  }

  # TTL — DynamoDB auto-deletes expired items
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Encryption at rest
  server_side_encryption {
    enabled = true
  }

  # Point-in-time recovery for audit purposes
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-capsules"
    Environment = var.environment
  }
}