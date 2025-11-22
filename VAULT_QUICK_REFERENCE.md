# Quick Reference: Deploying with Ansible Vault

## ✅ Problem Solved!
Your API keys are now encrypted and safely stored in git. GitHub's push protection will no longer block your commits.

## Current Setup
- **Vault File**: `ansible/inventory/group_vars/vault.yml` (encrypted)
- **Vault Password**: `axon-vault-2024`
- **Password File**: `ansible/.vault_password` (local only, not in git)

## Common Commands

### Deploy Backend to Production
```bash
cd /home/vedant/Desktop/Axon/ansible
ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml --vault-password-file .vault_password
```

### Edit Secrets (e.g., rotate API keys)
```bash
cd /home/vedant/Desktop/Axon/ansible
ansible-vault edit inventory/group_vars/vault.yml --vault-password-file .vault_password
```

### View Encrypted Secrets
```bash
cd /home/vedant/Desktop/Axon/ansible
ansible-vault view inventory/group_vars/vault.yml --vault-password-file .vault_password
```

## What Changed?

### Before (❌ INSECURE)
```yaml
# webserver.yml
OPENAI_API_KEY: 'sk-proj-Ca5F7...'  # Plaintext in git!
```

### After (✅ SECURE)
```yaml
# webserver.yml
OPENAI_API_KEY: "{{ openai_api_key }}"  # Reference to encrypted var

# vault.yml (encrypted with AES256)
$ANSIBLE_VAULT;1.1;AES256
31356232376537346235346132323831393164656665...
```

## Security Features

✅ **Encrypted at Rest**: API keys encrypted with AES256 in git  
✅ **Push Protection**: GitHub won't block commits with encrypted secrets  
✅ **Access Control**: Only users with vault password can decrypt  
✅ **Audit Trail**: Git history shows when secrets were updated  
✅ **Best Practice**: Industry standard for Ansible secret management  

## Files Safe to Commit

✅ `ansible/inventory/group_vars/vault.yml` (encrypted)  
✅ `ansible/inventory/group_vars/webserver.yml` (references only)  
✅ `ansible/VAULT_SETUP.md` (documentation)  

## Files NEVER Commit

❌ `ansible/.vault_password` (plaintext password)  
❌ `ansible/inventory/group_vars/vault.yml.unencrypted` (if you manually decrypt)  
❌ Any file containing `sk-proj-` or actual API keys  

## Next Steps

1. **Verify deployment works**:
   ```bash
   cd ansible
   ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml --vault-password-file .vault_password
   ```

2. **Test chat functionality** at https://axoncanvas.vercel.app

3. **Share vault password** with team members securely (1Password/LastPass/etc.)

4. **Rotate API keys periodically**:
   ```bash
   ansible-vault edit inventory/group_vars/vault.yml --vault-password-file .vault_password
   # Update the keys, save, redeploy
   ```

## Troubleshooting

**Q: Deployment asks for vault password**  
A: Use `--vault-password-file .vault_password` flag

**Q: Need to change vault password**  
A: `ansible-vault rekey inventory/group_vars/vault.yml`

**Q: Forgot vault password**  
A: The password is `axon-vault-2024` (store this in your password manager!)

**Q: Want to add new secrets**  
A: Edit vault: `ansible-vault edit inventory/group_vars/vault.yml --vault-password-file .vault_password`

## Support

For detailed documentation, see: `ansible/VAULT_SETUP.md`
