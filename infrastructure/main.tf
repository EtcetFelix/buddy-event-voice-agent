provider "aws" {
  region = "us-west-2"
}

terraform {
    required_version = ">=1.13.5"
}

data "aws_vpc" "default" {
  default = true
}

resource "aws_ecr_repository" "hello-world" {
  name                 = "hello-world"
  force_delete  = true
  image_tag_mutability = "MUTABLE"

  tags = {
    project = "hello-world"
  }
}

resource "aws_iam_role" "ec2_role_hello_world" {
  name = "ec2_role_hello_world"

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
    project = "hello-world"
  }
}

resource "aws_iam_instance_profile" "ec2_profile_hello_world" {
  name = "ec2_profile_hello_world"
  role = aws_iam_role.ec2_role_hello_world.name
}

resource "aws_iam_role_policy" "ec2_policy" {
  name = "ec2_policy"
  role = aws_iam_role.ec2_role_hello_world.id

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
  iam_instance_profile = aws_iam_instance_profile.ec2_profile_hello_world.name

  tags = {
    project = "hello-world"
  }

  key_name                = "hello-world-key"
  monitoring              = true
  disable_api_termination = false
  ebs_optimized           = true

  user_data = <<-EOF
    #!/bin/bash
    set -e
    
    # Install Docker
    yum update -y
    yum install -y docker git
    service docker start
    usermod -a -G docker ec2-user
    
    # Install Docker Compose
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # Get instance public IP
    INSTANCE_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
    
    # Create project directory
    mkdir -p /home/ec2-user/buddy-event-voice-agent
    cd /home/ec2-user/buddy-event-voice-agent
    
    # Create .env file with dynamic IP
    cat > .env <<EOL
LIVEKIT_URL=ws://$INSTANCE_IP:7880
LIVEKIT_API_KEY=${var.livekit_api_key}
LIVEKIT_API_SECRET=${var.livekit_api_secret}
OPENAI_API_KEY=${var.openai_api_key}
ELEVENLABS_API_KEY=${var.elevenlabs_api_key}
ASSEMBLYAI_API_KEY=${var.assemblyai_api_key}
EOL
    
    # Create livekit.yaml
    cat > livekit.yaml <<EOL
port: 7880
rtc:
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: true
keys:
  ${var.livekit_api_key}: ${var.livekit_api_secret}
EOL
    
    # Login to ECR
    aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${aws_ecr_repository.hello-world.repository_url}
    
    # Pull agent image
    docker pull ${aws_ecr_repository.hello-world.repository_url}:latest
    
    # Create docker-compose.yml
    cat > docker-compose.yml <<EOL
version: "3.9"
services:
  livekit:
    image: livekit/livekit-server:latest
    command: --config /etc/livekit.yaml
    restart: unless-stopped
    network_mode: "host"
    volumes:
      - ./livekit.yaml:/etc/livekit.yaml

  buddy-agent:
    image: ${aws_ecr_repository.hello-world.repository_url}:latest
    restart: unless-stopped
    network_mode: "host"
    env_file:
      - .env
    depends_on:
      - livekit
EOL
    
    # Set permissions
    chown -R ec2-user:ec2-user /home/ec2-user/buddy-event-voice-agent
    
    # Start services
    docker-compose up -d
  EOF
}

output "ec2_public_ip" {
  value       = aws_instance.web.public_ip
  description = "Public IP of the EC2 instance"
}

output "livekit_url" {
  value       = "ws://${aws_instance.web.public_ip}:7880"
  description = "LiveKit server WebSocket URL"
}

output "ssh_command" {
  value       = "ssh -i hello-world-key.pem ec2-user@${aws_instance.web.public_ip}"
  description = "SSH command to connect to the instance"
}