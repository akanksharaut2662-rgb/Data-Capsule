# terraform/sns.tf

resource "aws_sns_topic" "capsule_notifications" {
  name = "${var.project_name}-notifications"

  tags = {
    Name        = "${var.project_name}-notifications"
    Environment = var.environment
  }
}

output "sns_topic_arn" {
  value = aws_sns_topic.capsule_notifications.arn
}