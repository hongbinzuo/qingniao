# OpenClaw Setup Guide - DigitalOcean One-Click Deployment

## ⚠️ CRITICAL SECURITY RULES

**NEVER use OpenClaw for:**
- Direct trading execution
- Wallet management
- Exchange API key handling
- Any task involving real funds

**ONLY use OpenClaw for:**
- Market research and analysis
- Documentation generation
- Code review suggestions
- Public data collection
- Learning and experimentation

---

## Step 1: Create DigitalOcean Account

1. Go to: https://www.digitalocean.com
2. Click "Sign Up"
3. Choose sign-up method:
   - Email + Password
   - Google account
   - GitHub account
4. Verify your email address
5. Add payment method (credit card or PayPal)
   - Note: You may get $200 free credit for 60 days as a new user

**Cost Estimate:**
- 4GB RAM Droplet: $24/month ($0.036/hour)
- Or 2GB RAM Droplet: $12/month (minimum for OpenClaw)

---

## Step 2: Deploy OpenClaw Droplet

### Option A: Marketplace Deployment (Recommended)

1. **Navigate to Marketplace:**
   - Log into DigitalOcean
   - Click "Marketplace" in left sidebar
   - Search for "Moltbot" or "OpenClaw"
   - Click on the OpenClaw/Moltbot listing

2. **Create Droplet:**
   - Click "Create Moltbot Droplet" or "Create OpenClaw Droplet"

3. **Choose Plan:**
   - **Recommended**: Basic plan with 4GB RAM / 2 vCPUs ($24/month)
   - **Minimum**: 2GB RAM / 1 vCPU ($12/month) - may be slower
   - Select datacenter region closest to you

4. **Authentication:**
   - Choose "SSH Key" (more secure) or "Password"
   - If SSH Key:
     - Click "New SSH Key"
     - Follow instructions to generate and add your key
   - If Password:
     - You'll receive root password via email

5. **Finalize:**
   - Give your droplet a hostname (e.g., "openclaw-test")
   - Click "Create Droplet"
   - Wait 1-2 minutes for deployment

### Option B: Manual Deployment (If Marketplace Not Available)

1. **Create Regular Droplet:**
   - Click "Create" → "Droplets"
   - Choose Ubuntu 22.04 or 24.04 LTS
   - Select 4GB RAM plan
   - Choose datacenter region
   - Add SSH key or use password
   - Click "Create Droplet"

2. **Install OpenClaw Manually:**
   - SSH into your droplet (see Step 3)
   - Run the one-liner installer:
   ```bash
   curl -fsSL https://openclaw.ai/install.sh | bash
   ```

---

## Step 3: Connect to Your Droplet via SSH

### Get Your Droplet IP Address:
- In DigitalOcean dashboard, find your droplet
- Copy the IP address (e.g., 123.456.789.012)

### Connect from Windows:

**Option 1: Using PowerShell**
```powershell
ssh root@YOUR_DROPLET_IP
```

**Option 2: Using PuTTY**
- Download PuTTY from: https://www.putty.org/
- Enter your droplet IP in "Host Name"
- Port: 22
- Click "Open"
- Login as: root
- Enter password (from email) or use SSH key

### First Login:
- If using password, you may be prompted to change it
- Choose a strong password and save it securely

---

## Step 4: Complete OpenClaw Onboarding

After SSH connection, the onboarding wizard should start automatically.

### Onboarding Steps:

1. **Choose Setup Mode:**
   ```
   Select: Quickstart (recommended for beginners)
   ```

2. **Gateway Setup:**
   ```
   Select: Local gateway
   ```

3. **Choose AI Provider:**
   ```
   Options:
   - Anthropic (Claude) - Recommended for you
   - OpenAI (GPT-4)
   - Other providers
   
   Select: Anthropic
   ```

4. **Enter API Key:**
   - You need an Anthropic API key
   - Get one at: https://console.anthropic.com/
   - Create account → Go to API Keys → Create Key
   - Copy and paste the key when prompted
   
   ```
   Paste your API key: sk-ant-api03-...
   ```

5. **Set Gateway Token:**
   ```
   Create a strong password for accessing OpenClaw web UI
   Example: Use a password manager to generate a 20+ character password
   Save this token securely!
   ```

6. **Configure Messaging Channels (Optional):**
   ```
   You can skip this for now and configure later
   Or choose:
   - Telegram (easiest to set up)
   - Discord
   - WhatsApp (requires phone)
   - Slack
   ```

7. **Complete Setup:**
   - Onboarding will finish and start OpenClaw services
   - You should see: "OpenClaw is running!"

---

## Step 5: Access OpenClaw Web UI

OpenClaw binds to localhost for security. You need an SSH tunnel to access it.

### Create SSH Tunnel:

**From Windows PowerShell:**
```powershell
ssh -N -L 18789:127.0.0.1:18789 root@YOUR_DROPLET_IP
```

**What this does:**
- `-N`: Don't execute remote commands
- `-L 18789:127.0.0.1:18789`: Forward local port 18789 to remote localhost:18789
- Keep this terminal window open while using OpenClaw

### Access Web Interface:

1. **Keep SSH tunnel running** in PowerShell
2. **Open browser** and go to:
   ```
   http://localhost:18789/?token=YOUR_GATEWAY_TOKEN
   ```
   Replace `YOUR_GATEWAY_TOKEN` with the token you set during onboarding

3. **You should see OpenClaw dashboard!**

---

## Step 6: Initial Security Hardening

### 6.1 Create Non-Root User (Recommended)

```bash
# Create new user
adduser openclaw

# Add to sudo group
usermod -aG sudo openclaw

# Copy SSH keys (if using SSH key auth)
rsync --archive --chown=openclaw:openclaw ~/.ssh /home/openclaw
```

### 6.2 Configure Firewall

```bash
# Install UFW if not present
apt update
apt install ufw -y

# Allow SSH
ufw allow 22/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

### 6.3 Disable Root SSH Login (After testing non-root user)

```bash
# Edit SSH config
nano /etc/ssh/sshd_config

# Find and change:
PermitRootLogin no

# Save and restart SSH
systemctl restart sshd
```

---

## Step 7: Test OpenClaw with Low-Risk Tasks

### Safe Tasks to Try:

1. **Web Research:**
   ```
   "Search for the latest Bitcoin market analysis from CoinDesk"
   ```

2. **Document Summarization:**
   ```
   "Summarize this article: [paste URL]"
   ```

3. **Code Review:**
   ```
   "Review this Python function for potential bugs: [paste code]"
   ```

4. **Market Data Collection:**
   ```
   "Get the current top 10 cryptocurrencies by market cap from CoinGecko"
   ```

### ⚠️ NEVER Test These:

- ❌ "Connect to my Binance account"
- ❌ "Execute a trade on my behalf"
- ❌ "Access my wallet"
- ❌ "Store my API keys"

---

## Step 8: Monitor and Maintain

### Check OpenClaw Status:

```bash
# SSH into droplet
ssh root@YOUR_DROPLET_IP

# Check Docker containers
docker ps

# View logs
docker logs openclaw

# Restart if needed
docker restart openclaw
```

### Monitor Costs:

- Check DigitalOcean billing dashboard regularly
- Monitor Anthropic API usage at: https://console.anthropic.com/
- Set up billing alerts

---

## Troubleshooting

### OpenClaw Not Starting:

```bash
# Check Docker status
systemctl status docker

# Restart Docker
systemctl restart docker

# Check OpenClaw logs
docker logs openclaw
```

### Can't Access Web UI:

1. Verify SSH tunnel is running
2. Check if port 18789 is correct
3. Verify gateway token is correct
4. Try accessing without token first: `http://localhost:18789/`

### Out of Memory:

- Upgrade to 4GB RAM droplet if using 2GB
- Check memory usage: `free -h`
- Restart OpenClaw: `docker restart openclaw`

---

## Cost Management

### Monthly Costs:
- **DigitalOcean Droplet**: $12-24/month
- **Anthropic API (Claude)**:
  - Light usage: $5-15/month
  - Moderate usage: $20-50/month
  - Heavy usage: $100+/month

### Tips to Reduce Costs:
- Use Claude Haiku model (cheaper) for simple tasks
- Monitor API usage regularly
- Destroy droplet when not in use (can recreate anytime)
- Use DigitalOcean snapshots to save state

---

## Next Steps

After successful setup:

1. ✅ Test with safe, non-financial tasks
2. ✅ Monitor API usage for 1 week
3. ✅ Evaluate if OpenClaw improves your workflow
4. ✅ Keep it isolated from trading systems
5. ✅ Consider using it for:
   - Market research automation
   - Documentation generation
   - Code review assistance
   - Learning new technologies

---

## Support Resources

- **OpenClaw Documentation**: Check their GitHub repository
- **DigitalOcean Docs**: https://docs.digitalocean.com/
- **Anthropic API Docs**: https://docs.anthropic.com/
- **Community**: Search for OpenClaw Discord or forums

---

## Remember

OpenClaw is a powerful tool, but with great power comes great responsibility. Keep it isolated from your trading systems and use it only for tasks that don't involve financial risk.

Your existing **Qingniao trading bot** is already well-built and tested. OpenClaw should complement your workflow, not replace your proven systems.

Good luck! 🚀
