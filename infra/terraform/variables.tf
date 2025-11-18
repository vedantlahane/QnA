variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "ap-south-1"
}

variable "aws_az" {
  description = "Availability zone for the public subnet"
  type        = string
  default     = "ap-south-1a"
}

variable "key_pair_name" {
  description = "Name to assign to the generated AWS key pair"
  type        = string
  default     = "axon-key"
}

variable "public_key_path" {
  description = "Path to the local SSH public key to upload"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "web_ami" {
  description = "AMI ID for the webserver instance"
  type        = string
  default     = "ami-03f4878755434977f" # Ubuntu 22.04 LTS (ap-south-1)
}

variable "monitoring_ami" {
  description = "AMI ID for the monitoring instance"
  type        = string
  default     = "ami-03f4878755434977f"
}

variable "web_instance_type" {
  description = "Instance type for the backend"
  type        = string
  default     = "t3.small"
}

variable "monitoring_instance_type" {
  description = "Instance type for the monitoring host"
  type        = string
  default     = "t3.micro"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.20.1.0/24"
}

variable "allowed_ssh_cidrs" {
  description = "CIDR ranges allowed to SSH into instances"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allowed_app_cidrs" {
  description = "CIDR ranges permitted to hit the Gunicorn port"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allowed_monitor_http_cidrs" {
  description = "CIDR ranges permitted to view the Nagios UI"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
