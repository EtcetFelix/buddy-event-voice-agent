provider "aws" {
  region = "us-west-2"
}

terraform {
    required_version = ">=1.13.5"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnet_ids" "all" {
  vpc_id = data.aws_vpc.default.id
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
  description = "Web/ICMP SG for EC2"
  vpc_id      = data.aws_vpc.default.id

  ingress_cidr_blocks = ["0.0.0.0/0"]
  ingress_rules       = ["http-80-tcp", "https-443-tcp", "all-icmp"]
  egress_rules        = ["all-all"]
}

data "aws_ami" "amazon_linux_2_arm" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-arm64-gp3"]
  }
}

resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux_2_arm.id
  instance_type = "c6g.medium"

  root_block_device {
    volume_size = 8
  }

  vpc_security_group_ids = [
    module.ec2_sg.this_security_group_id,
    module.dev_ssh_sg.this_security_group_id
  ]
  iam_instance_profile = aws_iam_instance_profile.ec2_profile_hello_world.name

  tags = {
    project = "hello-world"
  }

  key_name                = "hello-world-key"
  monitoring              = true
  disable_api_termination = false
  ebs_optimized           = true
}
