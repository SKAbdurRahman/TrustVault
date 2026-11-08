# TrustVault

A document platform where only the people you choose can read a file, and you can prove who did.

## Live demo
- Web Application: https://frabjous-puppy-0abe47.netlify.app
- Backend API Docs: https://trustvault-kw7s.onrender.com/docs

The free Render instance sleeps when idle, so the first load can take about a minute.
The database on Render's free plan expires on 4 Dec 2026.

### Demo accounts (demo data only, no real information)
| Role | Username | Password |
|---|---|---|
| Admin | demo_admin | Iam@admin2 |
| Owner | demo_owner | Ur@owner7 |
| Viewer | demo_viewer | Theyr@viewers2 |

- How to log in via Web UI: Open `index.html` (or run locally and visit `http://127.0.0.1:8000/`), choose your endpoint, and click any demo button to log in instantly.
- How to log in via Swagger `/docs`: Open `/docs`, call `POST /auth/login`, copy the `access_token`, click **Authorize**, paste it.
- A locked account unlocks after 15 minutes (5 failed logins per username or 20 per IP trigger it), so a mistyped demo password is not permanent.

## What it does
- Modern, secure Web UI (`index.html`) deployable to Netlify with zero build config
- Login with roles (admin, owner, viewer), sessions stored in the database
- Upload, search, inline sandboxed preview, download, edit and delete documents
- Pre-validation of file size (≤5MB) and cryptographic magic bytes (PDF, PNG, JPEG, UTF-8 text)
- Owners grant and revoke read or edit access to named people, with optional expiry
- Every access, including refused attempts, goes into a hash-chained audit log
- Access removal takes effect on the very next request
- Real-time cryptographic SHA-256 hash-chain verification tool for administrators

## Run it locally
1. Install Python 3.13 and Git.
2. `git clone https://github.com/SKAbdurRahman/TrustVault.git` and `cd TrustVault`
3. `py -m venv venv`, then `venv\Scripts\Activate.ps1`
4. `pip install -r requirements.txt`
5. Set passwords (PowerShell):
   `$env:DEMO_ADMIN_PASSWORD="..."`, `$env:DEMO_OWNER_PASSWORD="..."`, `$env:DEMO_VIEWER_PASSWORD="..."`
6. `python -m scripts.setup_db` then `python -m scripts.seed`
7. `uvicorn app.main:app --reload` and open http://127.0.0.1:8000/docs
8. Run the tests with `pytest -q`

## Documentation
- `THREATS.md`: how it could be attacked, what I did, and what is still open
- `PROMPTS.md`: where the AI was wrong and what I did about it
- `sql/schema.sql`: database schema and audit-log triggers
- API reference: the live `/docs` page lists every endpoint
- `scripts/verify_triggers.py`: tries UPDATE, DELETE and TRUNCATE on the audit log and reports that each is rejected (set `VERIFY_DB_URL` to your own Postgres connection string first)

## API: who may call each endpoint

All endpoints except register, login and health need `Authorization: Bearer <token>`.
Where someone is refused, the answer is **404** (same as a missing item), so existence is not revealed. A missing or invalid token gives **401**. Every refusal is written to the audit log.

"Owner" means the user who uploaded the document. "Editor" and "Viewer" mean a user holding an active `edit` or `read` grant on that document. Admin has **no** automatic access to document contents.

### Auth
| Endpoint | Who |
|---|---|
| `POST /auth/register` | Anyone (always creates a normal user) |
| `POST /auth/login` | Anyone (throttled: 5 failures per username or 20 per IP in 15 minutes gives 429) |
| `POST /auth/logout` | Logged-in user (ends their own session) |
| `GET /auth/me` | Logged-in user |

### Documents
| Endpoint | Owner | Editor | Viewer | Other users | Admin (no grant) |
|---|---|---|---|---|---|
| `POST /documents` (upload) | yes | n/a | n/a | any logged-in user can upload their own | same |
| `GET /documents` (list, search) | own + granted only | granted | granted | sees nothing of others | own + granted only |
| `GET /documents/{id}` | yes | yes | yes | 404 | 404 |
| `GET /documents/{id}/download` | yes | yes | yes | 404 | 404 |
| `PATCH /documents/{id}` (edit title, category) | yes | yes | 404 | 404 | 404 |
| `DELETE /documents/{id}` (soft delete) | yes | 404 | 404 | 404 | 404 |

### Grants (all owner-only)
| Endpoint | Who |
|---|---|
| `POST /documents/{id}/grants` (grant read or edit, optional expiry) | Owner only |
| `GET /documents/{id}/grants` | Owner only |
| `DELETE /documents/{id}/grants/{grant_id}` (revoke, effective on the next request) | Owner only |

### Admin (role `admin` only; everyone else gets 404)
| Endpoint | What it does |
|---|---|
| `GET /admin/activity` | Read the audit log, filter by user, action, document, result |
| `GET /admin/audit/verify` | Check the audit hash chain |
| `GET /admin/users` | List users |
| `GET /admin/documents` | List every document's owner, type, size, time and status (no titles or contents) |
| `POST /admin/users/{id}/deactivate` | Deactivate a user and end their sessions (not yourself) |
| `POST /admin/users/{id}/activate` | Reactivate a user |
| `PATCH /admin/users/{id}/role` | Change a user's role (not your own) |

### Other
| Endpoint | Who |
|---|---|
| `GET /health` | Anyone |
| `GET /` | Anyone (serves the web page) |
