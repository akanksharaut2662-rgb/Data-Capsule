# terraform/api_gateway.tf
# API Gateway — the ONLY public entry point

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"
  description   = "Data Capsule API Gateway"

  cors_configuration {
    allow_origins = ["*"]  # Restrict in production
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
    max_age       = 300
  }

  tags = {
    Name = "${var.project_name}-api"
  }
}

# Stage — deploy the API
resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = var.environment
  auto_deploy = true

  tags = {
    Name = "${var.project_name}-stage"
  }
}

# --- UPLOAD ROUTE ---
resource "aws_apigatewayv2_integration" "upload" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.upload.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "upload" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /capsule/upload"
  target    = "integrations/${aws_apigatewayv2_integration.upload.id}"
}

resource "aws_lambda_permission" "api_upload" {
  statement_id  = "AllowAPIGatewayUpload"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# --- INTERACT ROUTE ---
resource "aws_apigatewayv2_integration" "interact" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.interact.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "interact" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /capsule/{capsule_id}"
  target    = "integrations/${aws_apigatewayv2_integration.interact.id}"
}

resource "aws_lambda_permission" "api_interact" {
  statement_id  = "AllowAPIGatewayInteract"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.interact.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}