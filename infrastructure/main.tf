provider "aws" {
  region = "us-west-2"
}

terraform {
  required_version = ">=1.13.5"
}

data "aws_vpc" "default" {
  default = true
}

resource "aws_ecr_repository" "buddy_agent" {
  name                 = "buddy-agent"
  force_delete         = true
  image_tag_mutability = "MUTABLE"

  tags = {
    project = "buddy-voice-agent"
  }
}

resource "aws_iam_role" "ec2_role_buddy_agent" {
  name = "ec2_role_buddy_agent"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF

  tags = {
    project = "buddy-voice-agent"
  }
}

resource "aws_iam_instance_profile" "ec2_profile_buddy_agent" {
  name = "ec2_profile_buddy_agent"
  role = aws_iam_role.ec2_role_buddy_agent.name
}

resource "aws_iam_role_policy" "ec2_policy" {
  name = "ec2_policy"
  role = aws_iam_role.ec2_role_buddy_agent.id

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

module "dev_ssh_sg" {
  source = "terraform-aws-modules/security-group/aws"

  name        = "ec2_ssh_sg"
  description = "SSH-only SG for EC2"
  vpc_id      = data.aws_vpc.default.id

  ingress_cidr_blocks = [var.allowed_ssh_cidr]
  ingress_rules       = ["ssh-tcp"]
}

module "ec2_sg" {
  source = "terraform-aws-modules/security-group/aws"

  name        = "ec2_web_sg"
  description = "Web/ICMP/LiveKit SG for EC2"
  vpc_id      = data.aws_vpc.default.id

  ingress_cidr_blocks = ["0.0.0.0/0"]
  ingress_rules       = ["http-80-tcp", "https-443-tcp", "all-icmp"]
  egress_rules        = ["all-all"]

  # LiveKit ports
  ingress_with_cidr_blocks = [
    {
      from_port   = 7880
      to_port     = 7880
      protocol    = "tcp"
      cidr_blocks = "0.0.0.0/0"
      description = "LiveKit signaling"
    },
    {
      from_port   = 50000
      to_port     = 60000
      protocol    = "udp"
      cidr_blocks = "0.0.0.0/0"
      description = "LiveKit RTC UDP"
    },
    {
      from_port   = 50000
      to_port     = 60000
      protocol    = "tcp"
      cidr_blocks = "0.0.0.0/0"
      description = "LiveKit RTC TCP"
    }
  ]
}

data "aws_ami" "amazon_linux_2_arm" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-arm64-gp2"]
  }
}

resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux_2_arm.id
  instance_type = "c6g.medium"

  root_block_device {
    volume_size = 8
  }

  vpc_security_group_ids = [
    module.ec2_sg.security_group_id,
    module.dev_ssh_sg.security_group_id
  ]
  iam_instance_profile = aws_iam_instance_profile.ec2_profile_buddy_agent.name

  tags = {
    project = "buddy-voice-agent"
  }

  key_name                = "hello-world-key"
  monitoring              = true
  disable_api_termination = false
  ebs_optimized           = true

  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Install Docker + Docker Compose
    yum update -y
    yum install -y docker git
    service docker start
    usermod -a -G docker ec2-user

    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose

    # Create app directory
    mkdir -p /home/ec2-user/app
    chown -R ec2-user:ec2-user /home/ec2-user/app

    # ECR login helper
    echo 'aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${aws_ecr_repository.buddy_agent.repository_url}' > /home/ec2-user/ecr-login.sh
    chmod +x /home/ec2-user/ecr-login.sh
  EOF
}

output "ec2_public_ip" {
  value       = aws_instance.web.public_ip
  description = "Public IP of the EC2 instance"
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.buddy_agent.repository_url
  description = "ECR repository URL for the buddy agent image"
}

output "livekit_url" {
  value       = "ws://${aws_instance.web.public_ip}:7880"
  description = "LiveKit server WebSocket URL"
}

output "ssh_command" {
  value       = "ssh -i hello-world-key.pem ec2-user@${aws_instance.web.public_ip}"
  description = "SSH command to connect to the instance"
}