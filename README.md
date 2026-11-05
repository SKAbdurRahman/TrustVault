# TrustVault

A document platform where the wrong person can never read a file, and you can prove who read it.

## Live demo
URL: https://trustvault-kw7s.onrender.com/docs

The free Render instance sleeps when idle, so the first load can take about a minute.
The database on Render's free plan expires on 4 Dec 2026.

### Demo accounts (demo data only, no real information)
| Role | Username | Password |
|---|---|---|
| Admin | demo_admin | Iam@admin2 |
| Owner | demo_owner | Ur@owner7 |
| Viewer | demo_viewer | Theyr@viewers2 |

How to log in: open `/docs`, call `POST /auth/login`, copy the `access_token`, click **Authorize**, paste it.

## What it does
- Login with roles (admin, owner, viewer), sessions stored in the database
- Upload, search, download, edit and delete documents
- Owners grant and revoke read or edit access to named people, with optional expiry
- Every access, including refused attempts, goes into a hash-chained audit log
- Access removal takes effect on the very next request

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
- A locked account unlocks after 15 minutes
- `scripts/verify_triggers.py`: tries UPDATE, DELETE and TRUNCATE on the audit log and reports that each is rejected (needs `VERIFY_DB_URL`)
