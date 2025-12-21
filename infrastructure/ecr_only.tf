provider "aws" {
  region = "us-west-2"
}

terraform {
  required_version = ">=1.13.5"
}

resource "aws_ecr_repository" "buddy_agent" {
  name                 = "buddy-agent"
  force_delete         = true
  image_tag_mutability = "MUTABLE"

  tags = {
    project = "buddy-voice-agent"
  }
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.buddy_agent.repository_url
  description = "ECR repository URL for the buddy agent image"
}

output "ecr_push_commands" {
  value = <<-EOT
    # Login to ECR
    aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${aws_ecr_repository.buddy_agent.repository_url}
    
    # Build and tag your image
    docker build -t buddy-agent:latest .
    docker tag buddy-agent:latest ${aws_ecr_repository.buddy_agent.repository_url}:latest
    
    # Push to ECR
    docker push ${aws_ecr_repository.buddy_agent.repository_url}:latest
  EOT
  description = "Commands to build and push your image"
}