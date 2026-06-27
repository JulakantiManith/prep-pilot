# Deployment Guide

This guide covers the full deployment process for the AI Interview & Presentation Coach application, including domain setup, SSL configuration, Supabase settings, SMTP configuration, and verification steps.

---

## Table of Contents

1. [Domain DNS Setup](#1-domain-dns-setup)
2. [SSL/TLS Certificate Configuration](#2-ssltls-certificate-configuration)
3. [Supabase Project Settings](#3-supabase-project-settings)
4. [SMTP Provider Setup](#4-smtp-provider-setup)
5. [Environment Variable Checklist](#5-environment-variable-checklist)
6. [Deployment Verification Steps](#6-deployment-verification-steps)

---

## 1. Domain DNS Setup

### Frontend Domain

Create DNS records pointing your frontend domain to your hosting provider.

| Record Type | Name | Value | TTL |
|-------------|------|-------|-----|
| A | `@` or `myapp.com` | Hosting provider IP | 300 |
| CNAME | `www` | `myapp.com` | 300 |

**Common hosting providers:**
- **Vercel**: Add domain in project settings, use their nameservers or CNAME
- **Netlify**: Add custom domain in site settings, CNAME to `your-site.netlify.app`
- **Cloudflare Pages**: Add custom domain, use Cloudflare nameservers

### Backend Domain (API)

Create a subdomain for the backend API:

| Record Type | Name | Value | TTL |
|-------------|------|-------|-----|
| A | `api` | Backend server IP | 300 |
| CNAME | `api` | `your-backend.onrender.com` | 300 |

**Common backend hosts:**
- **Render**: Add custom domain in service settings
- **Railway**: Add domain under service settings
- **AWS/GCP/Azure**: Point to load balancer or app service

### DNS Propagation

DNS changes can take up to 48 hours to propagate globally. Verify with:

```bash
# Check A record
dig +short myapp.com A

# Check CNAME record
dig +short api.myapp.com CNAME

# Check from multiple locations
nslookup myapp.com 8.8.8.8
nslookup myapp.com 1.1.1.1
```

---

## 2. SSL/TLS Certificate Configuration

### Option A: Let's Encrypt (Free)

Most hosting providers handle Let's Encrypt automatically:
- **Vercel/Netlify/Cloudflare Pages**: Automatic SSL provisioning
- **Render/Railway**: Automatic SSL for custom domains
- **Self-hosted (certbot)**:

```bash
sudo certbot --nginx -d myapp.com -d www.myapp.com -d api.myapp.com
```

### Option B: Cloudflare (Free Tier)

1. Add your domain to Cloudflare
2. Update nameservers at your registrar
3. Enable "Full (strict)" SSL mode in SSL/TLS settings
4. Cloudflare issues and auto-renews certificates

### Option C: Cloud Provider Managed Certificates

- **AWS Certificate Manager**: Free certificates for use with ALB/CloudFront
- **GCP Managed Certificates**: Free with GCP load balancers
- **Azure App Service**: Free managed certificates

### Verification

```bash
# Verify SSL certificate
openssl s_client -connect myapp.com:443 -servername myapp.com </dev/null 2>/dev/null | openssl x509 -noout -dates

# Check certificate chain
curl -vI https://myapp.com 2>&1 | grep -A5 "Server certificate"
```

---

## 3. Supabase Project Settings

### Authentication URL Configuration

1. Go to **Supabase Dashboard** → **Authentication** → **URL Configuration**
2. Set **Site URL**: `https://myapp.com`
3. Add **Redirect URLs**:
   - `https://myapp.com/auth/callback`
   - `https://myapp.com/auth/reset-password`
   - `http://localhost:5173/auth/callback` (for local development)

### Email Templates

1. Go to **Authentication** → **Email Templates**
2. Update the "Confirm signup" template to use your custom domain in links
3. Update the "Reset password" template similarly
4. Ensure `{{ .SiteURL }}` resolves to your custom domain

### API Settings

1. Go to **Settings** → **API**
2. Note your **Project URL** and **anon key** for frontend
3. Note your **service_role key** for backend (keep secret)

### Auth Providers (Optional)

If using OAuth providers (Google, GitHub):
1. Update authorized redirect URIs to include `https://myapp.com/auth/callback`
2. Update authorized JavaScript origins to include `https://myapp.com`

For detailed Supabase configuration, see [supabase-project-settings.md](./supabase-project-settings.md).

---

## 4. SMTP Provider Setup

Choose one of the following SMTP providers for transactional emails.

### SendGrid

1. Create a SendGrid account and verify your sender domain
2. Generate an API key with "Mail Send" permission
3. Configuration:
   ```env
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=SG.your-api-key
   SMTP_SENDER_EMAIL=noreply@myapp.com
   SMTP_SENDER_NAME=AI Interview Coach
   ```

### AWS SES

1. Verify your domain in AWS SES console
2. Create SMTP credentials in SES → SMTP Settings
3. Request production access (move out of sandbox)
4. Configuration:
   ```env
   SMTP_HOST=email-smtp.us-east-1.amazonaws.com
   SMTP_PORT=587
   SMTP_USERNAME=your-ses-smtp-username
   SMTP_PASSWORD=your-ses-smtp-password
   SMTP_SENDER_EMAIL=noreply@myapp.com
   SMTP_SENDER_NAME=AI Interview Coach
   ```

### Resend

1. Create a Resend account and add your domain
2. Generate an API key
3. Configuration:
   ```env
   SMTP_HOST=smtp.resend.com
   SMTP_PORT=587
   SMTP_USERNAME=resend
   SMTP_PASSWORD=re_your-api-key
   SMTP_SENDER_EMAIL=noreply@myapp.com
   SMTP_SENDER_NAME=AI Interview Coach
   ```

### Mailgun

1. Add and verify your domain in Mailgun
2. Get SMTP credentials from domain settings
3. Configuration:
   ```env
   SMTP_HOST=smtp.mailgun.org
   SMTP_PORT=587
   SMTP_USERNAME=postmaster@mg.myapp.com
   SMTP_PASSWORD=your-mailgun-smtp-password
   SMTP_SENDER_EMAIL=noreply@myapp.com
   SMTP_SENDER_NAME=AI Interview Coach
   ```

### Email Deliverability

After configuring SMTP, set up SPF, DKIM, and DMARC records. See [email-deliverability-setup.md](./email-deliverability-setup.md) for detailed DNS configuration.

---

## 5. Environment Variable Checklist

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | Yes | — | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Supabase service role key |
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key |
| `GROQ_API_KEY` | No | — | Groq API key (optional provider) |
| `OPENROUTER_API_KEY` | No | — | OpenRouter API key (optional provider) |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `JWT_SECRET` | Yes | — | Secret for JWT token signing |
| `APP_DOMAIN` | No | `""` | Custom domain (e.g., `myapp.com`) |
| `FRONTEND_URL` | No | `http://localhost:5173` | Frontend base URL |
| `BACKEND_URL` | No | `http://localhost:8000` | Backend base URL |
| `ALLOWED_ORIGINS` | No | `""` | Comma-separated CORS origins |
| `SMTP_HOST` | No | `""` | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USERNAME` | No | `""` | SMTP auth username |
| `SMTP_PASSWORD` | No | `""` | SMTP auth password |
| `SMTP_SENDER_EMAIL` | No | `""` | Sender email address |
| `SMTP_SENDER_NAME` | No | `""` | Sender display name |
| `EMAIL_DELIVERABILITY_CHECK_ENABLED` | No | `false` | Verify SMTP at startup |
| `EMAIL_NOTIFICATIONS_ENABLED` | No | `true` | Enable session completion emails |

### Frontend (`frontend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | Yes | `http://localhost:8000/api/v1` | Backend API URL |
| `VITE_SUPABASE_URL` | Yes | — | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | — | Supabase anonymous key |
| `VITE_APP_NAME` | No | `""` | Application display name |
| `VITE_APP_DOMAIN` | No | `""` | Custom domain for auth redirects |
| `VITE_AUTH_REDIRECT_URL` | No | `""` | Explicit auth callback URL override |
| `VITE_CREATOR_NAME` | No | `""` | Footer creator name |
| `VITE_GITHUB_URL` | No | `""` | Footer GitHub link |
| `VITE_LINKEDIN_URL` | No | `""` | Footer LinkedIn link |

---

## 6. Deployment Verification Steps

After deploying, run through the following verification steps.

### Health Checks

```bash
# Backend health
curl -s https://api.myapp.com/api/v1/health | jq .

# Email health (if SMTP configured)
curl -s https://api.myapp.com/api/v1/health/email | jq .
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Auth Flow Test

1. **Registration**: Create a new account at `https://myapp.com/register`
2. **Email verification**: Check inbox for verification email from your custom sender
3. **Verify link domain**: Confirmation link should point to `https://myapp.com/auth/callback`
4. **Login**: Sign in with the verified account
5. **Password reset**: Request password reset and verify the email link domain

### Email Delivery Test

1. Register a new user and confirm the verification email arrives
2. Check the "From" address matches `SMTP_SENDER_EMAIL`
3. Check the sender name matches `SMTP_SENDER_NAME`
4. Verify links in email use the correct domain
5. Check email doesn't land in spam (SPF/DKIM/DMARC configured)

### CORS Verification

```bash
# Preflight request
curl -X OPTIONS https://api.myapp.com/api/v1/health \
  -H "Origin: https://myapp.com" \
  -H "Access-Control-Request-Method: GET" \
  -v 2>&1 | grep -i "access-control"
```

Expected headers:
```
access-control-allow-origin: https://myapp.com
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS
```

### Session Flow Test

1. Start a practice interview session
2. Complete a session with answers
3. Verify session completion email is received (if notifications enabled)
4. Verify the email contains correct session summary data
5. Verify CTA link points to the correct domain

---

## Troubleshooting

| Issue | Possible Cause | Fix |
|-------|---------------|-----|
| CORS errors in browser | `ALLOWED_ORIGINS` missing frontend URL | Add frontend URL to `ALLOWED_ORIGINS` |
| Auth redirect to localhost | Supabase Site URL not updated | Update Site URL in Supabase dashboard |
| Emails not arriving | SMTP not configured | Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_SENDER_EMAIL` |
| Emails in spam | Missing SPF/DKIM/DMARC | See [email-deliverability-setup.md](./email-deliverability-setup.md) |
| SSL certificate error | DNS not propagated yet | Wait and re-check with `dig` |
| 502 Bad Gateway | Backend not running | Check backend logs and health endpoint |
