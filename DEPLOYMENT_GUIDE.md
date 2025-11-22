# Deployment Guide - Security Fixes Applied

## ✅ Changes Applied

### 1. Django Settings (`backend/backend/settings.py`)
- ✅ `DEBUG` mode now reads from `DJANGO_DEBUG` environment variable (defaults to False)
- ✅ `SECRET_KEY` now reads from `DJANGO_SECRET_KEY` environment variable
- ✅ Both changes are backward compatible with fallback values

### 2. Ansible Playbook (`ansible/playbooks/deploy_backend.yml`)
- ✅ Reduced `gunicorn_workers` from 3 to 1 (fixes SQLite database locking)
- ✅ Removed redundant worker reduction logic

### 3. Ansible Group Variables (`ansible/inventory/group_vars/webserver.yml`)
- ✅ Set `gunicorn_workers: 1` for SQLite compatibility
- ✅ Added `DJANGO_DEBUG: 'False'` for production
- ✅ Added placeholder for `DJANGO_SECRET_KEY`
- ✅ Updated `DJANGO_ALLOWED_HOSTS` with EC2 IP and domain
- ✅ Added `FRONTEND_ORIGINS` with all Vercel deployment URLs

---

## 🚀 Deployment Steps

### Step 1: Generate a New Secret Key

```bash
cd /home/vedant/Desktop/Axon
python3 scripts/generate_secret_key.py
```

Copy the generated key (it will look like: `django-insecure-abc123xyz...`)

### Step 2: Update the Secret Key in Ansible

Edit `ansible/inventory/group_vars/webserver.yml`:

```yaml
backend_env:
  # ... other vars ...
  DJANGO_SECRET_KEY: 'your-generated-secret-key-here'  # Paste the key from Step 1
```

**⚠️ IMPORTANT:** Never commit this secret key to Git! Consider using Ansible Vault:

```bash
# Encrypt the file with Ansible Vault
ansible-vault encrypt ansible/inventory/group_vars/webserver.yml

# When deploying, use --ask-vault-pass
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/deploy_backend.yml --ask-vault-pass
```

### Step 3: Deploy to Production

```bash
cd ansible
ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml
```

If you encrypted with Ansible Vault:
```bash
ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml --ask-vault-pass
```

### Step 4: Verify the Deployment

#### Check Service Status
```bash
ssh ubuntu@ec2-13-235-83-16.ap-south-1.compute.amazonaws.com
sudo systemctl status axon-gunicorn
```

#### Check Worker Count
```bash
ps aux | grep gunicorn
# Should show only 1 worker process (plus 1 master process)
```

#### Test Health Endpoint
```bash
curl http://ec2-13-235-83-16.ap-south-1.compute.amazonaws.com:8000/api/health/
```

Should return:
```json
{
  "status": "ok",
  "timestamp": "...",
  "checks": {
    "database": {
      "status": "ok",
      "error": null
    }
  }
}
```

#### Test Chat Functionality
1. Visit https://axoncanvas.vercel.app
2. Register/login
3. Send a test message
4. Should work without 500 errors! ✅

---

## 🔍 Troubleshooting

### If deployment fails:

1. **Check Ansible connection:**
   ```bash
   ansible -i inventory/hosts.ini webserver -m ping
   ```

2. **Check logs on EC2:**
   ```bash
   ssh ubuntu@ec2-13-235-83-16.ap-south-1.compute.amazonaws.com
   sudo journalctl -u axon-gunicorn -n 50
   ```

3. **Verify environment variables:**
   ```bash
   ssh ubuntu@ec2-13-235-83-16.ap-south-1.compute.amazonaws.com
   sudo cat /etc/axon/axon.env
   ```

4. **Check database permissions:**
   ```bash
   ssh ubuntu@ec2-13-235-83-16.ap-south-1.compute.amazonaws.com
   ls -la /home/ubuntu/axon/backend/db.sqlite3
   ```

### If chat still returns 500:

1. **Check if migrations are applied:**
   ```bash
   ssh ubuntu@ec2-13-235-83-16.ap-south-1.compute.amazonaws.com
   cd /home/ubuntu/axon/backend
   source .venv/bin/activate
   python manage.py showmigrations
   ```

2. **Apply migrations if needed:**
   ```bash
   python manage.py migrate
   ```

3. **Restart the service:**
   ```bash
   sudo systemctl restart axon-gunicorn
   ```

---

## 📋 Environment Variables Reference

| Variable | Value | Purpose |
|----------|-------|---------|
| `DJANGO_DEBUG` | `'False'` | Disable debug mode in production |
| `DJANGO_SECRET_KEY` | Generated key | Secure session/crypto key |
| `DJANGO_ALLOWED_HOSTS` | EC2 IP/domain | Allowed HTTP Host headers |
| `FRONTEND_ORIGINS` | Vercel URLs | CORS allowed origins |
| `DATABASE_URL` | Empty (SQLite) | Database connection string |

---

## 🎯 Expected Results After Deployment

- ✅ Chat messages work without 500 errors
- ✅ No more database locking issues
- ✅ Debug mode disabled (no sensitive info exposed)
- ✅ Secure secret key in use
- ✅ Single Gunicorn worker (stable with SQLite)

---

## 🔐 Security Notes

1. **Never commit secrets to Git!** Use Ansible Vault or environment variables
2. Consider using AWS Secrets Manager or AWS Systems Manager Parameter Store
3. Rotate the `DJANGO_SECRET_KEY` periodically
4. Keep `DEBUG = False` in production always

---

## 📈 Future Improvements

When ready to scale:
1. Migrate from SQLite to PostgreSQL (AWS RDS)
2. Increase Gunicorn workers to 3-5
3. Add Redis for caching
4. Enable HTTPS with SSL certificate
5. Set up CloudWatch monitoring
6. Configure auto-scaling

---

## 📞 Quick Commands Reference

```bash
# Generate secret key
python3 scripts/generate_secret_key.py

# Deploy
cd ansible
ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml

# Check service
ssh ubuntu@ec2-13-235-83-16.ap-south-1.compute.amazonaws.com 'sudo systemctl status axon-gunicorn'

# View logs
ssh ubuntu@ec2-13-235-83-16.ap-south-1.compute.amazonaws.com 'sudo journalctl -u axon-gunicorn -f'

# Test health
curl http://ec2-13-235-83-16.ap-south-1.compute.amazonaws.com:8000/api/health/
```
