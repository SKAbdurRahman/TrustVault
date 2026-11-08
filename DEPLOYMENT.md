# TrustVault Deployment Guide: Netlify

TrustVault includes a zero-dependency, advanced, secure single-page web application (`index.html`) engineered for 1-click deployment on static & JAMstack hosting platforms such as  **Netlify**.

**Live site:** [https://frabjous-puppy-0abe47.netlify.app](https://frabjous-puppy-0abe47.netlify.app/)


## 1. Deploying to Netlify

### Option A: Via Netlify Web Dashboard
1. Go to [app.netlify.com](https://app.netlify.com).
2. Click **Add new site** &rarr; **Import an existing project**.
3. Select your Git provider and choose the **TrustVault** repository.
4. Build settings are automatically detected from `netlify.toml`:
   - **Base directory**: (empty)
   - **Build command**: none needed (`netlify.toml` runs a no-op `echo`)
   - **Publish directory**: `.`
5. Click **Deploy TrustVault**.

### Option B: Via Netlify CLI
```bash
npm i -g netlify-cli
cd TrustVault
netlify deploy --prod --dir=.
```

---

## 2. Connecting to the Backend

The web application features an in-app **Endpoint Switcher** in the top navigation bar:
- **Cloud (Render Live)**: Connects to `https://trustvault-kw7s.onrender.com`.
  > *Note: Render's free tier spins down on idle. When connecting after idle, the status indicator will show "Waking up..." with a friendly prompt. The backend wakes in about 45 seconds.*
- **Local (127.0.0.1:8000)**: Connects to your local FastAPI backend instance when running `uvicorn app.main:app --reload`.

---

## 3. Built-in Security Architecture

The web application enforces strict defense-in-depth principles:
1. **Content Security Policy (CSP)**: Pre-configured in `netlify.toml` and in `index.html` to limit where the page can connect (only the backend and local development) and to block embedded objects. It still allows inline script and styles, so it does not stop injected inline script (see THREATS.md).
2. **Contextual Escaping**: All user-controlled text (titles, categories, usernames, audit logs) is sanitized to prevent DOM-based XSS.
3. **Client-Side Signature Validation**: Inspects magic bytes (PDF, PNG, JPEG, UTF-8 text) and 5MB limits before transmitting data over the wire.
4. **Sandboxed Previews**: Document previews for text, images, and PDFs run in isolated, sandboxed containers.
5. **Hidden Existence**: Access denials return 404 to ensure existence of private documents is never disclosed.
6. **Session Termination**: 401 status codes immediately wipe `sessionStorage` tokens and return to the authentication gate.
