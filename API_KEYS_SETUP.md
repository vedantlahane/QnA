# 🔑 Missing API Keys - AI Chat Not Working

## 🚨 Problem
Your backend is working, but the AI agent returns the fallback message:
```
"Sorry, I could not generate a response right now."
```

**Root Cause:** Missing AI API keys in production environment.

---

## ✅ Required API Keys

### 1. **OPENAI_API_KEY** (REQUIRED)
This is the most critical key - your AI won't work without it.

**Get it here:** https://platform.openai.com/api-keys

Steps:
1. Go to https://platform.openai.com/
2. Sign in or create an account
3. Navigate to API Keys section
4. Click "Create new secret key"
5. Copy the key (it starts with `sk-...`)

**Cost:** Pay-as-you-go, typically $0.002-0.03 per 1K tokens
You'll need to add a payment method.

---

### 2. **TAVILY_API_KEY** (Optional but Recommended)
For web search functionality in your AI agent.

**Get it here:** https://app.tavily.com/

Steps:
1. Go to https://app.tavily.com/
2. Sign up for a free account
3. Copy your API key from the dashboard

**Cost:** Free tier available (1000 searches/month)

---

### 3. **LANGCHAIN_API_KEY** (Optional)
For debugging and tracing AI interactions.

**Get it here:** https://smith.langchain.com/

Steps:
1. Go to https://smith.langchain.com/
2. Sign in with your account
3. Go to Settings > API Keys
4. Create a new API key

**Cost:** Free tier available

---

## 🚀 How to Add API Keys to Production

### Option 1: Using Ansible (Recommended)

1. **Edit the Ansible configuration:**
   ```bash
   nano ansible/inventory/group_vars/webserver.yml
   ```

2. **Add your API keys:**
   ```yaml
   backend_env:
     # ... other variables ...
     OPENAI_API_KEY: 'sk-proj-your-actual-openai-key-here'
     TAVILY_API_KEY: 'tvly-your-actual-tavily-key-here'  # Optional
     LANGCHAIN_API_KEY: 'your-langchain-key-here'  # Optional
     LANGCHAIN_TRACING_V2: 'false'
     LANGCHAIN_PROJECT: 'axon'
   ```

3. **Deploy with Ansible:**
   ```bash
   cd ansible
   ansible-playbook -i inventory/hosts.ini playbooks/deploy_backend.yml
   ```

### Option 2: Manual Update (Quick Fix)

SSH into your EC2 instance and edit the environment file:

```bash
# SSH into EC2
ssh ubuntu@ec2-13-235-83-16.ap-south-1.compute.amazonaws.com

# Edit the environment file
sudo nano /etc/axon/axon.env

# Add these lines at the end:
OPENAI_API_KEY="sk-proj-your-actual-openai-key-here"
TAVILY_API_KEY="tvly-your-actual-tavily-key-here"
LANGCHAIN_API_KEY="your-langchain-key-here"
LANGCHAIN_TRACING_V2="false"
LANGCHAIN_PROJECT="axon"

# Save and exit (Ctrl+X, then Y, then Enter)

# Restart Gunicorn
sudo systemctl restart axon-gunicorn

# Check status
sudo systemctl status axon-gunicorn

# Test
curl http://localhost:8000/api/health/
```

---

## 🧪 Testing After Adding Keys

1. **Check environment variables are loaded:**
   ```bash
   ssh ubuntu@ec2-13-235-83-16.ap-south-1.compute.amazonaws.com
   sudo cat /etc/axon/axon.env | grep OPENAI
   ```

2. **Check service is running:**
   ```bash
   sudo systemctl status axon-gunicorn
   ```

3. **Test the AI:**
   - Visit https://axoncanvas.vercel.app
   - Login
   - Send a message: "Hello, what can you do?"
   - You should get a proper AI response!

4. **Check logs if still not working:**
   ```bash
   sudo journalctl -u axon-gunicorn -f
   ```

---

## 🔒 Security Best Practices

1. **Never commit API keys to Git!**
   - Keep them only in the Ansible configuration
   - Consider using Ansible Vault:
     ```bash
     ansible-vault encrypt ansible/inventory/group_vars/webserver.yml
     ```

2. **Rotate keys periodically**
   - Regenerate API keys every 3-6 months

3. **Monitor usage**
   - Check OpenAI dashboard for usage/costs
   - Set spending limits in OpenAI dashboard

4. **Restrict API key permissions**
   - Only enable required models/endpoints
   - Use project-specific keys when possible

---

## 💰 Cost Estimates

### OpenAI (GPT-4)
- **Input:** ~$0.03 per 1K tokens
- **Output:** ~$0.06 per 1K tokens
- **Typical chat message:** ~500-2000 tokens
- **Estimated cost per message:** $0.02-$0.10

### Tavily (Web Search)
- **Free tier:** 1000 searches/month
- **Paid:** $0.001 per search after free tier

### LangSmith (Tracing)
- **Free tier:** 5000 traces/month
- Most hobby projects stay within free tier

---

## 📋 Quick Checklist

- [ ] Get OpenAI API key (REQUIRED)
- [ ] Get Tavily API key (optional)
- [ ] Get LangChain API key (optional)
- [ ] Add keys to `webserver.yml` OR directly to `/etc/axon/axon.env`
- [ ] Deploy changes (Ansible) OR restart service (manual)
- [ ] Test chat functionality
- [ ] Verify AI responds with actual content
- [ ] Monitor costs and usage

---

## 🆘 Troubleshooting

### "Sorry, I could not generate a response" still appears:

1. **Verify keys are set:**
   ```bash
   ssh ubuntu@ec2-13-235-83-16.ap-south-1.compute.amazonaws.com
   sudo cat /etc/axon/axon.env | grep OPENAI
   ```

2. **Check for errors in logs:**
   ```bash
   sudo journalctl -u axon-gunicorn --since "5 minutes ago" --no-pager
   ```

3. **Verify OpenAI key is valid:**
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer YOUR_OPENAI_API_KEY"
   ```

4. **Restart the service:**
   ```bash
   sudo systemctl restart axon-gunicorn
   ```

### Invalid API key error:
- Double-check you copied the full key
- Ensure there are no extra spaces
- Verify key hasn't been revoked in OpenAI dashboard

### Rate limit errors:
- Check OpenAI dashboard for usage limits
- Add payment method if on free tier
- Consider implementing rate limiting in your app

---

## 🎯 Next Steps

1. **Get your OpenAI API key** (most important!)
2. **Add it to production** using one of the methods above
3. **Test your chat** - it should work now!
4. **Monitor costs** in the first few days

Once you add the API keys, your AI chat will work perfectly! 🚀
