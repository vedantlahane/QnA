output "webserver_public_ip" {
  description = "Public IP for the Axon backend host"
  value       = aws_instance.webserver.public_ip
}

output "monitoring_public_ip" {
  description = "Public IP for the Nagios monitoring host"
  value       = aws_instance.monitoring.public_ip
}

output "inventory_snippet" {
  description = "Ansible inventory snippet referencing the created instances"
  value = <<-EOT
          [webserver]
          ${aws_instance.webserver.public_dns} ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/axon.pem

          [monitoring]
          monitoring-node ansible_host=${aws_instance.monitoring.public_dns} ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/axon.pem
          EOT
}
