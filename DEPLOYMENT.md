# TrustVault Deployment Guide: Vercel & Netlify

TrustVault includes a zero-dependency, advanced, secure single-page web application (`index.html`) engineered for 1-click deployment on static & JAMstack hosting platforms such as **Vercel** and **Netlify**.

---

## 1. Deploying to Vercel

### Option A: Via Vercel Web Dashboard (1-Click Import)
1. Push your repository to GitHub / GitLab / Bitbucket.
2. Go to [vercel.com/new](https://vercel.com/new).
3. Import your **TrustVault** repository.
4. In the Project Configuration:
   - **Framework Preset**: *Other*
   - **Root Directory**: `./` (default)
   - **Build Command**: *Leave blank* (no build step required)
   - **Output Directory**: *Leave blank* (root directory with `index.html`)
5. Click **Deploy**.
6. Vercel will immediately read `vercel.json` and deploy the secure web application with configured Content Security Policies and headers.

### Option B: Via Vercel CLI
```bash
npm i -g vercel
cd TrustVault
vercel
```
Follow the interactive prompts; select default project settings.

---

## 2. Deploying to Netlify

### Option A: Via Netlify Web Dashboard
1. Go to [app.netlify.com](https://app.netlify.com).
2. Click **Add new site** &rarr; **Import an existing project**.
3. Select your Git provider and choose the **TrustVault** repository.
4. Build settings are automatically detected from `netlify.toml`:
   - **Base directory**: (empty)
   - **Build command**: (empty)
   - **Publish directory**: `.`
5. Click **Deploy TrustVault**.

### Option B: Via Netlify CLI
```bash
npm i -g netlify-cli
cd TrustVault
netlify deploy --prod --dir=.
```

---

## 3. Connecting to the Backend

The web application features an in-app **Endpoint Switcher** in the top navigation bar:
- **Cloud (Render Live)**: Connects to `https://trustvault-kw7s.onrender.com`.
  > *Note: Render's free tier spins down on idle. When connecting after idle, the status indicator will show "Waking up..." with a friendly prompt. The enclave boots in ~45 seconds.*
- **Local (127.0.0.1:8000)**: Connects to your local FastAPI backend instance when running `uvicorn app.main:app --reload`.
- **Custom URL**: Connect to your self-hosted instance or custom domain.

---

## 4. Built-in Security Architecture

The web application enforces strict defense-in-depth principles:
1. **Content Security Policy (CSP)**: Pre-configured in `vercel.json`, `netlify.toml`, and `_headers` to restrict script execution, object embedding, and external network connections.
2. **Contextual Escaping**: All user-controlled text (titles, categories, usernames, audit logs) is sanitized to prevent DOM-based XSS.
3. **Client-Side Signature Validation**: Inspects magic bytes (PDF, PNG, JPEG, UTF-8 text) and 5MB limits before transmitting data over the wire.
4. **Sandboxed Previews**: Document previews for text, images, and PDFs run in isolated, sandboxed containers.
5. **Zero-Knowledge Privacy**: Access denials return 404 to ensure existence of private documents is never disclosed.
6. **Session Termination**: 401 status codes immediately wipe `sessionStorage` tokens and return to the authentication gate.
