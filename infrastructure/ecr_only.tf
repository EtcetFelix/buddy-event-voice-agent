provider "aws" {
  region = "us-west-2"
}

terraform {
  required_version = ">=1.13.5"
}

# ECR Repository
resource "aws_ecr_repository" "buddy_agent" {
  name                 = "buddy-agent"
  force_delete         = true
  image_tag_mutability = "MUTABLE"
  tags = {
    project = "buddy-voice-agent"
  }
}

# Reference the existing OIDC provider (created via AWS CLI)
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# IAM role for GitHub Actions (scoped to your specific repo)
resource "aws_iam_role" "github_actions_ecr" {
  name = "github-actions-buddy-agent-ecr"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = data.aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            # Only allows GitHub Actions from this specific repo's main branch
            "token.actions.githubusercontent.com:sub" = "repo:EtcetFelix/buddy-event-voice-agent:environment:production"
          }
        }
      }
    ]
  })

  tags = {
    project = "buddy-voice-agent"
    purpose = "github-actions-ecr-push"
  }
}

# Policy: Minimal ECR push permissions (only for buddy-agent repo)
resource "aws_iam_role_policy" "github_actions_ecr_push" {
  name = "ecr-push-only"
  role = aws_iam_role.github_actions_ecr.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = aws_ecr_repository.buddy_agent.arn
      }
    ]
  })
}

# IAM user for droplet to pull from ECR (read-only)
resource "aws_iam_user" "droplet_ecr_pull" {
  name = "droplet-ecr-pull-buddy-agent"
  
  tags = {
    project = "buddy-voice-agent"
    purpose = "droplet-ecr-readonly"
  }
}

resource "aws_iam_user_policy" "droplet_ecr_pull" {
  name = "ecr-pull-only"
  user = aws_iam_user.droplet_ecr_pull.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = aws_ecr_repository.buddy_agent.arn
      }
    ]
  })
}

resource "aws_iam_access_key" "droplet_ecr_pull" {
  user = aws_iam_user.droplet_ecr_pull.name
}

# Outputs
output "ecr_repository_url" {
  value       = aws_ecr_repository.buddy_agent.repository_url
  description = "ECR repository URL for the buddy agent image"
}

output "github_actions_role_arn" {
  value       = aws_iam_role.github_actions_ecr.arn
  description = "IAM role ARN for GitHub Actions to assume (add this to GitHub secrets as AWS_ROLE_ARN)"
}

output "droplet_aws_access_key_id" {
  value     = aws_iam_access_key.droplet_ecr_pull.id
  sensitive = true
  description = "AWS Access Key ID for droplet to pull from ECR (configure on droplet)"
}

output "droplet_aws_secret_access_key" {
  value     = aws_iam_access_key.droplet_ecr_pull.secret
  sensitive = true
  description = "AWS Secret Access Key for droplet to pull from ECR (configure on droplet)"
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