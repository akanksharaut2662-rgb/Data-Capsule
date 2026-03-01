# terraform/lambda.tf

# ---- UPLOAD LAMBDA ----
resource "aws_lambda_function" "upload" {
  function_name = "${var.project_name}-upload"
  filename      = "${path.module}/upload.zip"
  handler       = "index.lambda_handler"
  runtime       = "python3.12"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 60
  memory_size   = 256

  source_code_hash = filebase64sha256("${path.module}/upload.zip")

  environment {
    variables = {
      BUCKET_NAME  = aws_s3_bucket.capsule_storage.bucket
      TABLE_NAME   = aws_dynamodb_table.capsules.name
      EXPIRY_HOURS = tostring(var.expiry_hours)
      SNS_TOPIC_ARN  = aws_sns_topic.capsule_notifications.arn  
      FRONTEND_URL   = "http://${aws_s3_bucket.frontend.bucket}.s3-website.${var.aws_region}.amazonaws.com" 
    }
  }
  tags = {
    Name = "${var.project_name}-upload"
  }
}

# ---- INTERACT LAMBDA ----
resource "aws_lambda_function" "interact" {
  function_name = "${var.project_name}-interact"
  filename      = "${path.module}/interact.zip"
  handler       = "index.lambda_handler"
  runtime       = "python3.12"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 30
  memory_size   = 256

  source_code_hash = filebase64sha256("${path.module}/interact.zip")

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.capsule_storage.bucket
      TABLE_NAME  = aws_dynamodb_table.capsules.name
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tags = {
    Name = "${var.project_name}-interact"
  }
}

# ---- CLEANUP LAMBDA ----
resource "aws_lambda_function" "cleanup" {
  function_name = "${var.project_name}-cleanup"
  filename      = "${path.module}/cleanup.zip"
  handler       = "index.lambda_handler"
  runtime       = "python3.12"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 60
  memory_size   = 128

  source_code_hash = filebase64sha256("${path.module}/cleanup.zip")

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.capsule_storage.bucket
      TABLE_NAME  = aws_dynamodb_table.capsules.name
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tags = {
    Name = "${var.project_name}-cleanup"
  }
}

# Schedule cleanup to run every hour via EventBridge
resource "aws_cloudwatch_event_rule" "cleanup_schedule" {
  name                = "${var.project_name}-cleanup-schedule"
  description         = "Trigger cleanup Lambda every hour"
  schedule_expression = "rate(1 hour)"
}

resource "aws_cloudwatch_event_target" "cleanup_target" {
  rule      = aws_cloudwatch_event_rule.cleanup_schedule.name
  target_id = "cleanup-lambda"
  arn       = aws_lambda_function.cleanup.arn
}

resource "aws_lambda_permission" "allow_eventbridge_cleanup" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cleanup.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cleanup_schedule.arn
}