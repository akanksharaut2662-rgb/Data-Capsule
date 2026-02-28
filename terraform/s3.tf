# terraform/s3.tf
# Private S3 bucket — never directly exposed to clients

resource "aws_s3_bucket" "capsule_storage" {
  bucket = "${var.project_name}-storage-${random_id.suffix.hex}"

  tags = {
    Name        = "${var.project_name}-storage"
    Environment = var.environment
  }
}

# Block ALL public access
resource "aws_s3_bucket_public_access_block" "capsule_storage" {
  bucket = aws_s3_bucket.capsule_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for audit trail
resource "aws_s3_bucket_versioning" "capsule_storage" {
  bucket = aws_s3_bucket.capsule_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Encrypt all objects at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "capsule_storage" {
  bucket = aws_s3_bucket.capsule_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Auto-delete objects after 2 days (safety net beyond DynamoDB TTL)
resource "aws_s3_bucket_lifecycle_configuration" "capsule_storage" {
  bucket = aws_s3_bucket.capsule_storage.id

  rule {
    id     = "auto-delete-capsules"
    status = "Enabled"

    filter {
      prefix = "capsules/"
    }

    expiration {
      days = 2
    }
  }
}

# Bucket policy — only allow Lambda role to access it
resource "aws_s3_bucket_policy" "capsule_storage" {
  bucket = aws_s3_bucket.capsule_storage.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaOnly"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda_role.arn
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.capsule_storage.arn}/*"
      },
      {
        Sid    = "DenyDirectAccess"
        Effect = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [
          aws_s3_bucket.capsule_storage.arn,
          "${aws_s3_bucket.capsule_storage.arn}/*"
        ]
        Condition = {
          StringNotEquals = {
            "aws:PrincipalArn" = aws_iam_role.lambda_role.arn
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.capsule_storage]
}