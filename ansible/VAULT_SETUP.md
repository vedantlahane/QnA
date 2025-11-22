# Ansible Vault Setup Guide

## Overview
This project uses Ansible Vault to securely encrypt sensitive data like API keys and secrets.

## Files
- `inventory/group_vars/vault.yml` - Contains encrypted secrets (variables)
- `inventory/group_vars/webserver.yml` - References vault variables using Jinja2 templates

## Setup Instructions

### 1. Encrypt the Vault File

**First time setup:**
```bash
cd ansible
ansible-vault encrypt inventory/group_vars/vault.yml
```

You'll be prompted to create a vault password. **Remember this password** - you'll need it to run playbooks!

### 2. Using Ansible Playbooks with Vault

When running playbooks that use encrypted variables, you need to provide the vault password:

**Option A: Prompt for password**
```bash
ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml --ask-vault-pass
```

**Option B: Use password file (more convenient)**
```bash
# Create a password file (DO NOT COMMIT THIS!)
echo "your-vault-password" > ~/.ansible_vault_password
chmod 600 ~/.ansible_vault_password

# Use it in playbooks
ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml --vault-password-file ~/.ansible_vault_password
```

### 3. Editing Encrypted Vault File

To update secrets:
```bash
cd ansible
ansible-vault edit inventory/group_vars/vault.yml
```

This will decrypt the file in your editor, allow you to make changes, and re-encrypt on save.

### 4. View Encrypted Content

To view the encrypted file without editing:
```bash
ansible-vault view inventory/group_vars/vault.yml
```

### 5. Change Vault Password

To change the vault password:
```bash
ansible-vault rekey inventory/group_vars/vault.yml
```

## Security Best Practices

1. ✅ **DO** keep the vault password secure (use a password manager)
2. ✅ **DO** commit the encrypted `vault.yml` file to git
3. ✅ **DO** use `.gitignore` to prevent committing password files
4. ❌ **DON'T** commit the unencrypted vault file
5. ❌ **DON'T** share the vault password in Slack/email/chat
6. ❌ **DON'T** commit `.vault_password` or similar password files

## Variables in vault.yml

Current encrypted variables:
- `django_secret_key` - Django SECRET_KEY setting
- `openai_api_key` - OpenAI API key for GPT-4 chat
- `tavily_api_key` - Tavily API key for web search
- `langchain_api_key` - LangChain API key for tracing (optional)

## Adding New Secrets

1. Edit the vault file: `ansible-vault edit inventory/group_vars/vault.yml`
2. Add your new variable (e.g., `my_new_secret: 'value'`)
3. Reference it in `webserver.yml` using Jinja2: `"{{ my_new_secret }}"`
4. Save and the file will be automatically re-encrypted

## Troubleshooting

**Error: "Attempting to decrypt but no vault secrets found"**
- Solution: Provide the vault password using `--ask-vault-pass` or `--vault-password-file`

**Error: "ERROR! Decryption failed"**
- Solution: Check your vault password is correct

**Need to rotate API keys?**
1. Edit vault: `ansible-vault edit inventory/group_vars/vault.yml`
2. Update the key values
3. Redeploy: `ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml --ask-vault-pass`

## Example: Full Deployment with Vault

```bash
# Navigate to ansible directory
cd /home/vedant/Desktop/Axon/ansible

# Deploy backend with encrypted secrets
ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml --ask-vault-pass

# Enter your vault password when prompted
# The playbook will decrypt vault.yml, use the variables, and deploy
```

## Repository Security

GitHub has secret scanning enabled. This vault approach ensures:
- No plaintext API keys in git history
- Push protection won't block commits
- Secrets are encrypted at rest in the repository
- Only authorized users with the vault password can decrypt

## Next Steps

1. Encrypt the vault file: `ansible-vault encrypt inventory/group_vars/vault.yml`
2. Commit the changes (encrypted vault is safe to commit)
3. Push to GitHub (no more secret scanning blocks!)
4. Share vault password with team members securely (password manager/1Password/LastPass)
