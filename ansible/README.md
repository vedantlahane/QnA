# Axon Ansible playbooks

This directory centralizes all automation tasks for provisioning and deploying Axon services.

## Structure

```
ansible/
├── inventory/
│   ├── hosts.ini              # server definitions (web + monitoring)
│   └── group_vars/            # inventory-scoped defaults
│       ├── webserver.yml      # shared vars for backend hosts
│       └── monitoring.yml     # Ngaios admin creds + monitored host metadata
├── playbooks/
│   ├── setup_backend.yml      # base OS preparation for backend box
│   ├── deploy_backend.yml     # deploys / updates the Django backend via Gunicorn
│   └── provision_ngaios.yml   # installs Ngaios monitoring stack + Axon checks
├── templates/
│   ├── axon-gunicorn.service.j2       # systemd unit for Gunicorn
│   └── nagios-axon-backend.cfg.j2     # Nagios host + service definitions
└── README.md
```

## Usage

1. Update `inventory/hosts.ini` with the correct hostnames/IPs and SSH key paths.
2. Adjust group variables under `inventory/group_vars/` if you need different paths, credentials, or settings.
3. Run the playbooks in order (prepare ➜ deploy ➜ monitor) so that each layer has what it needs:

```bash
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/setup_backend.yml
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/deploy_backend.yml
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/provision_ngaios.yml
```

### Backend deployment notes

- `deploy_backend.yml` now provisions Gunicorn behind a managed systemd unit (`axon-gunicorn`). Tweak bind address, worker count, or timeout via `inventory/group_vars/webserver.yml`.
- The unit loads environment variables from `/etc/axon/axon.env` and also falls back to `DJANGO_SETTINGS_MODULE=backend.settings`. Add other environment variables to `inventory/group_vars/webserver.yml` under `backend_env` or create `/etc/axon/axon.env` on the target host.
	- Note: If you leave `DATABASE_URL` empty and run with the default SQLite database, it is recommended to set `gunicorn_workers` to 1 to avoid SQLite "database is locked" errors. Alternatively, set `DATABASE_URL` to a managed database like an RDS/Postgres instance for production.

### Monitoring notes

- `provision_ngaios.yml` ships a ready-made Nagios host + service definition that checks both the Gunicorn TCP port and a configurable HTTP endpoint.
- Customize the monitored host/port/path in `inventory/group_vars/monitoring.yml` (defaults auto-derive from the first `[webserver]` host in the inventory).
- The playbook has been updated to be more OS-aware: Debian (apt) package tasks run only on Debian-family hosts. You can override `nagios_version`, `nagios_plugins_version`, and `nagios_service_name` in `inventory/group_vars/monitoring.yml` to change which Nagios release is used.
