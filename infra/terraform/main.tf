terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_vpc" "axon" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "axon-vpc"
  }
}

resource "aws_internet_gateway" "axon" {
  vpc_id = aws_vpc.axon.id

  tags = {
    Name = "axon-igw"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.axon.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.aws_az
  map_public_ip_on_launch = true

  tags = {
    Name = "axon-public"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.axon.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.axon.id
  }

  tags = {
    Name = "axon-public"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "web" {
  name        = "axon-web-sg"
  description = "Allow SSH, HTTP(S), and app traffic"
  vpc_id      = aws_vpc.axon.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Gunicorn"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.allowed_app_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "axon-web-sg"
  }
}

resource "aws_security_group" "monitoring" {
  name        = "axon-monitoring-sg"
  description = "Allow SSH and HTTP for Nagios"
  vpc_id      = aws_vpc.axon.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  ingress {
    description = "Nagios Web"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_monitor_http_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "axon-monitoring-sg"
  }
}

locals {
  common_tags = {
    Project = "Axon"
    Managed = "Terraform"
  }
}

resource "aws_key_pair" "axon" {
  key_name   = var.key_pair_name
  public_key = file(var.public_key_path)
}

resource "aws_instance" "webserver" {
  ami                         = var.web_ami
  instance_type               = var.web_instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.web.id]
  key_name                    = aws_key_pair.axon.key_name
  associate_public_ip_address = true
  tags = merge(local.common_tags, { Role = "web", Name = "axon-web" })

  user_data = <<-EOT
              #!/bin/bash
              apt-get update -y
              apt-get install -y python3 python3-venv python3-pip git
              EOT
}

resource "aws_instance" "monitoring" {
  ami                         = var.monitoring_ami
  instance_type               = var.monitoring_instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.monitoring.id]
  key_name                    = aws_key_pair.axon.key_name
  associate_public_ip_address = true
  tags = merge(local.common_tags, { Role = "monitoring", Name = "axon-monitoring" })

  user_data = <<-EOT
              #!/bin/bash
              apt-get update -y
              apt-get install -y python3 python3-venv python3-pip git
              EOT
}
*** End of File