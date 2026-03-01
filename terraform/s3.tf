# terraform/s3.tf

resource "aws_s3_bucket" "capsule_storage" {
  bucket = "${var.project_name}-store-${random_id.suffix.hex}"

  tags = {
    Name        = "${var.project_name}-storage"
    Environment = var.environment
  }
}