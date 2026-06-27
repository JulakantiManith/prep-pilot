# Custom Domain Pre-Deployment Checklist

Use this checklist before going live with a custom domain. Each section must pass before proceeding to the next.

---

## 1. DNS Propagation Check

- [ ] A/CNAME record for frontend domain resolves correctly
  ```bash
  dig +short myapp.com A
  # Should return your hosting provider's IP
  ```
- [ ] A/CNAME record for API subdomain resolves correctly
  ```bash
  dig +short api.myapp.com CNAME
  # Should return your backend host
  ```
- [ ] DNS resolves from multiple nameservers
  ```bash
  nslookup myapp.com 8.8.8.8
  nslookup myapp.com 1.1.1.1
  ```
- [ ] No conflicting DNS records (check for duplicate A/AAAA/CNAME entries)
- [ ] TTL values are reasonable (300s for initial setup, can increase later)

---

## 2. SSL Certificate Validation

- [ ] Frontend serves valid HTTPS
  ```bash
  curl -I https://myapp.com
  # Should return 200 with no SSL errors
  ```
- [ ] Backend API serves valid HTTPS
  ```bash
  curl -I https://api.myapp.com/api/v1/health
  # Should return 200 with no SSL errors
  ```
- [ ] Certificate is not expired
  ```bash
  openssl s_client -connect myapp.com:443 -servername myapp.com </dev/null 2>/dev/null \
    | openssl x509 -noout -dates
  ```
- [ ] Certificate covers all required domains (including `www` if applicable)
- [ ] Certificate chain is complete (no intermediate cert issues)
  ```bash
  openssl s_client -connect myapp.com:443 -servername myapp.com </dev/null 2>/dev/null \
    | openssl verify
  ```
- [ ] HTTP to HTTPS redirect is working
  ```bash
  curl -I http://myapp.com
  # Should return 301/302 redirect to https://
  ```

---

## 3. Auth Flow Testing

### Registration Flow
- [ ] Navigate to `https://myapp.com/register`
- [ ] Submit registration form with valid email
- [ ] Verification email is received within 60 seconds
- [ ] Verification email "From" shows configured sender name and email
- [ ] Verification link URL points to `https://myapp.com/auth/callback` (not localhost)
- [ ] Clicking verification link successfully verifies the account
- [ ] User is redirected to the app on the custom domain after verification

### Login Flow
- [ ] Navigate to `https://myapp.com/login`
- [ ] Sign in with verified credentials
- [ ] Session is created successfully
- [ ] Auth tokens are stored correctly (no mixed-content warnings)

### Password Reset Flow
- [ ] Request password reset from `https://myapp.com/forgot-password`
- [ ] Reset email is received within 60 seconds
- [ ] Reset link URL points to `https://myapp.com/auth/reset-password` (not localhost)
- [ ] Clicking reset link opens the password reset page on the custom domain
- [ ] Submitting new password works and redirects to login

### Magic Link / OTP (if enabled)
- [ ] Magic link email points to custom domain
- [ ] OTP code works when entered on custom domain login page

---

## 4. Email Delivery Testing

### Basic Delivery
- [ ] Verification email arrives in inbox (not spam/junk)
- [ ] Password reset email arrives in inbox
- [ ] Session completion notification arrives in inbox (if enabled)
- [ ] Emails render correctly on desktop and mobile clients

### Sender Identity
- [ ] "From" address matches `SMTP_SENDER_EMAIL`
- [ ] "From" name matches `SMTP_SENDER_NAME`
- [ ] Reply-to is configured appropriately

### Deliverability
- [ ] SPF record is configured and passes
  ```bash
  dig +short TXT myapp.com | grep spf
  ```
- [ ] DKIM record is configured and passes
  ```bash
  dig +short TXT selector._domainkey.myapp.com
  ```
- [ ] DMARC record is configured
  ```bash
  dig +short TXT _dmarc.myapp.com
  ```
- [ ] Email passes SPF/DKIM/DMARC checks (view email headers in received email)
- [ ] Email health endpoint returns healthy
  ```bash
  curl -s https://api.myapp.com/api/v1/health/email | jq .
  ```

### Links in Emails
- [ ] All links in verification email use `https://myapp.com` (not localhost or Supabase URL)
- [ ] All links in password reset email use `https://myapp.com`
- [ ] CTA button in session completion email links to correct session page

---

## 5. CORS Verification

- [ ] Preflight OPTIONS request returns correct headers
  ```bash
  curl -X OPTIONS https://api.myapp.com/api/v1/health \
    -H "Origin: https://myapp.com" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: Authorization,Content-Type" \
    -v 2>&1 | grep -i "access-control"
  ```
- [ ] `Access-Control-Allow-Origin` includes `https://myapp.com`
- [ ] `Access-Control-Allow-Methods` includes GET, POST, PUT, DELETE
- [ ] `Access-Control-Allow-Headers` includes Authorization and Content-Type
- [ ] No CORS errors in browser console during normal app usage
- [ ] API calls from frontend to backend work without errors
  ```bash
  # Test from browser console:
  # fetch('https://api.myapp.com/api/v1/health').then(r => r.json()).then(console.log)
  ```
- [ ] WebSocket connections (if any) work through custom domain

---

## Final Verification

- [ ] All checklist items above pass
- [ ] Full user journey works end-to-end on custom domain:
  1. Register → Verify email → Login → Start session → Complete session → Receive notification
- [ ] No console errors or mixed-content warnings in browser
- [ ] Environment variables in production match the deployment guide checklist
- [ ] Monitoring and logging are active for the production environment

---

## Rollback Plan

If issues are found after going live:

1. **DNS rollback**: Revert DNS records to previous values (note: propagation delay applies)
2. **Supabase rollback**: Reset Site URL to platform URL (e.g., Vercel/Netlify URL)
3. **Environment rollback**: Remove `APP_DOMAIN`, reset `FRONTEND_URL`/`BACKEND_URL` to platform URLs
4. **Verify**: Confirm app works on platform URL after rollback
