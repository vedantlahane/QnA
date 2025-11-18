# Axon Terraform stack

This Terraform configuration provisions the base infrastructure that pairs with the Ansible playbooks:

- VPC + public subnet + internet gateway
- Security groups for the backend (Gunicorn) and monitoring (Nagios) hosts
- SSH key pair upload
- Two Ubuntu EC2 instances (one for the Django backend, one for Ngaios/Nagios)

After `terraform apply`, feed the emitted inventory snippet into `ansible/inventory/hosts.ini` and run the playbooks.

## Prerequisites

- Terraform 1.6+
- AWS account credentials configured via environment variables or shared credentials file
- An SSH public key (defaults to `~/.ssh/id_rsa.pub`, override via `-var public_key_path=...`)

## Usage

```bash
cd infra/terraform
terraform init
terraform plan -out plan.tfplan
terraform apply plan.tfplan
```

Useful variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `aws_region` | `ap-south-1` | Deployment region |
| `aws_az` | `ap-south-1a` | AZ for subnet + instances |
| `key_pair_name` | `axon-key` | AWS key pair name |
| `public_key_path` | `~/.ssh/id_rsa.pub` | Local SSH key to upload |
| `web_instance_type` | `t3.small` | Backend EC2 size |
| `monitoring_instance_type` | `t3.micro` | Monitoring EC2 size |
| `allowed_ssh_cidrs` | `[0.0.0.0/0]` | Lock down SSH access |
| `allowed_app_cidrs` | `[0.0.0.0/0]` | Inbound Gunicorn access |
| `allowed_monitor_http_cidrs` | `[0.0.0.0/0]` | Nagios web access |

Override variables via `-var` flags or a `terraform.tfvars` file.

## Next steps

1. Copy the `inventory_snippet` output into `ansible/inventory/hosts.ini`.
2. Run `ansible/playbooks/setup_backend.yml` and `deploy_backend.yml` against the new backend host.
3. Run `ansible/playbooks/provision_ngaios.yml` against the monitoring host to bring Nagios online.
