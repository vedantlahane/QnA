# Production Issues & Fixes

## 🚨 Critical Issue: Database OperationalError (500 Error on Chat)

### Root Cause
The `OperationalError` when sending chat messages is caused by **SQLite database locking** with multiple Gunicorn workers trying to write simultaneously.

### Error Details
```
XHRPOST https://axoncanvas.vercel.app/api/chat/
[HTTP/2 500  164ms]

OperationalError at /api/chat/
```

---

## 🔧 Required Fixes

### 1. **Fix Gunicorn Workers for SQLite (URGENT)**

**Problem:** Running 3 Gunicorn workers with SQLite causes database locks.

**Solution:** Reduce to 1 worker OR switch to PostgreSQL.

#### Option A: Quick Fix - Single Worker (Recommended for now)

SSH into your EC2 instance and edit the Gunicorn service:

```bash
sudo nano /etc/systemd/system/axon-gunicorn.service
```

Find the line with `--workers` and change it to:
```
--workers 1
```

Then restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart axon-gunicorn
```

#### Option B: Update Ansible Playbook

Edit `ansible/playbooks/deploy_backend.yml`:

```yaml
# Change this line (around line 13):
gunicorn_workers: 1  # Changed from 3 to 1 for SQLite
```

Then redeploy:
```bash
cd ansible
ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml
```

---

### 2. **Fix DEBUG Mode in Production (SECURITY RISK)**

**Problem:** `DEBUG = True` in production exposes sensitive information.

**File:** `backend/backend/settings.py` (line 42)

**Fix:**
```python
# Change from:
DEBUG = True

# To:
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')
```

Then set in your environment file on EC2 (`/etc/axon/axon.env`):
```bash
DJANGO_DEBUG=False
```

---

### 3. **Fix SECRET_KEY (SECURITY RISK)**

**Problem:** Using the default Django secret key in production.

**File:** `backend/backend/settings.py` (line 39)

**Fix:**
```python
# Change from:
SECRET_KEY = 'django-insecure-i^xxm##v@nuq!hzfuxejtj$kqtwnydutg7kg%8!-%*cl+b86a%'

# To:
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-i^xxm##v@nuq!hzfuxejtj$kqtwnydutg7kg%8!-%*cl+b86a%')
```

Generate a new secret key:
```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Add to `/etc/axon/axon.env` on EC2:
```bash
DJANGO_SECRET_KEY=your-generated-secret-key-here
```

---

### 4. **Verify Database Migrations**

SSH into EC2 and verify:

```bash
cd /home/ubuntu/axon/backend
source .venv/bin/activate
python manage.py showmigrations

# If any are unmarked, run:
python manage.py migrate
```

---

### 5. **Check Database File Permissions**

```bash
ls -la /home/ubuntu/axon/backend/db.sqlite3
# Should show: -rw-r--r-- 1 ubuntu ubuntu

# If not, fix with:
sudo chown ubuntu:ubuntu /home/ubuntu/axon/backend/db.sqlite3
sudo chmod 644 /home/ubuntu/axon/backend/db.sqlite3
```

---

## 📋 Recommended Long-term Solution

**Switch from SQLite to PostgreSQL** for production:

### Why?
- SQLite is designed for single-user/low-concurrency scenarios
- PostgreSQL handles multiple workers properly
- Better for production applications

### How?
1. Set up RDS PostgreSQL instance on AWS
2. Update `DATABASE_URL` in environment variables
3. Run migrations
4. Restore workers to 3+

---

## 🧪 Testing After Fixes

### 1. Test Backend Health
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

### 2. Test Chat (after authentication)
Visit https://axoncanvas.vercel.app and try sending a message.

---

## 📊 Current Status Summary

| Component | Status | Issues |
|-----------|--------|--------|
| Backend Server | ✅ Running | None |
| Frontend | ✅ Deployed | None |
| Health Endpoint | ✅ Working | None |
| Authentication | ✅ Working | None |
| Chat Endpoint | ❌ 500 Error | SQLite locking |
| DEBUG Mode | ⚠️ Enabled | Security risk |
| SECRET_KEY | ⚠️ Default | Security risk |

---

## 🚀 Quick Fix Command Sequence

SSH into your EC2 instance and run:

```bash
# 1. Stop the service
sudo systemctl stop axon-gunicorn

# 2. Edit the service file
sudo sed -i 's/--workers [0-9]\+/--workers 1/g' /etc/systemd/system/axon-gunicorn.service

# 3. Reload and start
sudo systemctl daemon-reload
sudo systemctl start axon-gunicorn

# 4. Check status
sudo systemctl status axon-gunicorn

# 5. Test
curl http://localhost:8000/api/health/
```

---

## 📞 Support

If issues persist after applying these fixes:
1. Check logs: `sudo journalctl -u axon-gunicorn -f`
2. Check database: `ls -la ~/axon/backend/db.sqlite3`
3. Verify migrations: `cd ~/axon/backend && source .venv/bin/activate && python manage.py showmigrations`
