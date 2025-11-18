# Axon Ansible playbooks

This directory centralizes all automation tasks for provisioning and deploying Axon services.

## Structure

```
ansible/
├── inventory/
│   └── hosts.ini              # server definitions (web + monitoring)
├── playbooks/
│   ├── setup_backend.yml      # base OS preparation for backend box
│   ├── deploy_backend.yml     # deploys / updates the Django backend via Gunicorn
│   └── provision_ngaios.yml   # installs Ngaios monitoring stack + Axon checks
├── templates/
│   ├── axon-gunicorn.service.j2       # systemd unit for Gunicorn
│   └── nagios-axon-backend.cfg.j2     # Nagios host + service definitions
├── group_vars/
│   ├── webserver.yml          # shared vars for backend hosts
│   └── monitoring.yml         # Ngaios admin creds + monitored host metadata
└── README.md
```

## Usage

1. Update `inventory/hosts.ini` with the correct hostnames/IPs and SSH key paths.
2. Adjust group variables if you need different paths, credentials, or settings.
3. Run the required playbook:

```bash
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/setup_backend.yml
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/deploy_backend.yml
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/provision_ngaios.yml
```

### Backend deployment notes

- `deploy_backend.yml` now provisions Gunicorn behind a managed systemd unit (`axon-gunicorn`). Tweak bind address, worker count, or timeout via `group_vars/webserver.yml`.
- The unit simply exports `DJANGO_SETTINGS_MODULE=backend.settings`. If you rely on additional environment variables, point the service to an env file or extend the template under `templates/`.

### Monitoring notes

- `provision_ngaios.yml` ships a ready-made Nagios host + service definition that checks both the Gunicorn TCP port and a configurable HTTP endpoint.
- Customize the monitored host/port/path in `group_vars/monitoring.yml` (defaults auto-derive from the first `[webserver]` host in the inventory).
