# terraform/outputs.tf

output "api_gateway_url" {
  description = "Base URL of the API Gateway — use this to make API calls"
  value       = aws_apigatewayv2_stage.main.invoke_url
}

output "upload_endpoint" {
  description = "Endpoint to upload a file and create a capsule"
  value       = "${aws_apigatewayv2_stage.main.invoke_url}/capsule/upload"
}

output "interact_endpoint" {
  description = "Endpoint to interact with a capsule"
  value       = "${aws_apigatewayv2_stage.main.invoke_url}/capsule/{capsule_id}"
}

output "s3_bucket_name" {
  description = "S3 bucket name (private — for reference only)"
  value       = aws_s3_bucket.capsule_storage.bucket
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.capsules.name
}