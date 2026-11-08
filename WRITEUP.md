# TrustVault write-up

## 1. What I built
TrustVault is a document platform where only the right person can open a file, and every access is recorded. It is written in Python with FastAPI. The web page is one HTML file hosted on Netlify, talking to the API on Render. It uses SQLite on my laptop and Postgres on Render. The web page is live at https://trustvault-kw7s.onrender.com, the API docs are at https://trustvault-kw7s.onrender.com/docs, and the demo logins are in the README.

There are three kinds of users:
- **Admin**: manages users (deactivate, activate, change role) and reads the audit log. An admin cannot open other people's documents.
- **Owner**: the person who uploaded a document. They can read, edit, delete and share it.
- **Viewer / editor**: a person the owner gave a `read` or `edit` grant to.

## 2. My permission model
Every document belongs to one owner. Nobody else can reach it unless the owner gives them a grant (read or edit, with an optional expiry date).

The decision is made in one place: `require()` in `app/permissions.py`, which calls `can()`. Every document route calls `require()` first. `can()` is deny by default. It looks at the database every time, so nothing is cached.

If someone is refused, I return 404, not 403. That way a stranger cannot tell if a document exists or not. The refused attempt is also written to the audit log.

Admin has no automatic access to document contents. I chose this so that one stolen admin account cannot read everything. The cost is that if an owner leaves the company, an admin cannot recover their files.

## 3. How taking access away works immediately
Sessions and grants are stored in the database, not in a token that says "I am allowed". When an owner revokes a grant, `revoked_at` is set. On the next request `can()` reads the grants again and the access is gone. When an admin deactivates a user, their sessions are deleted, so their old token stops working on the very next request. The cost is one database check per request, which I accepted.

## 4. How the audit trail is protected
I log uploads, downloads, edits, deletes, grants, revokes, logins and admin actions. I also log refused attempts, not only successful ones.

Each audit row stores the hash of the row before it, so if someone edits an old row the chain breaks. `/admin/audit/verify` checks the chain. On Postgres I added database triggers that reject UPDATE, DELETE and TRUNCATE on the audit table. I tested this on the live database with `scripts/verify_triggers.py`, and all three were rejected.

Writes happen under a lock, because without it two requests at the same moment could fork the chain. My test showed that this really happened before I added the lock.

What can still go wrong: whoever owns the database can drop the triggers.

## 5. How files are stored
Files are saved with a random name in a storage folder that is not public. The user's file name is only used to show back to them, never as a path on disk. The type is decided from the first bytes of the file, not the extension or what the browser says. The limit is 5 MB. Downloads are sent as attachments with `nosniff`, so the browser does not run them. A file can only be downloaded through the route that checks permission.

## 6. What I did not build, and why
- Folders and groups: the per-document model was enough, and I wanted it solid first.
- Versions and restoring deleted documents: delete is a soft delete, but there is no restore screen.
- Sharing outside the company: it adds many risks and was not in the must-do list.
- Persistent storage: Render's free disk is wiped on a redeploy.
- A fully polished website: the web page is a single static file with no build step, so it is plain and has no automated browser tests.
- Self-service admin creation: admins come from the seed script or a role change by another admin.

## 7. How I used AI, and where it was wrong
I used Claude to build this. I did not just accept what it gave me. After each part I removed one check from the code and ran the tests. If the tests stayed green, the tests were weak, and I fixed them. Real mistakes I found (all in PROMPTS.md):
- No test for deactivated users. I removed the `is_active` check and all tests still passed.
- No test that a successful download is logged.
- Downgrading a grant (edit to read) was untested, so the old edit permission could stay.
- The audit log could fork its own hash chain when two requests came together.
- A date with a timezone (`...Z`) crashed the grant route.
- A huge document ID gave a 500 on Postgres but not on SQLite, so my tests missed it.
- The AI's deploy instructions used the wrong Postgres driver, and the first deploy crashed.
- The web page shipped with open CORS, a CSP that allowed any HTTPS site, and no sender name on shared documents; times showed UTC as India time.
- A live database password was committed to the public README; I rotated it.

## 8. What is unfinished or weak
Everything is in THREATS.md. The main open points:
- Anyone can lock a known username for 15 minutes by failing logins on purpose.
- The per-IP limit uses `X-Forwarded-For`, which can be faked.
- Uploads are lost when the free Render disk is wiped.
- My tests run on SQLite but production runs Postgres, so some bugs only show live.
- One admin can promote another admin with no second approval.
- Failed logins store the typed username, and someone may type a password there by mistake.
