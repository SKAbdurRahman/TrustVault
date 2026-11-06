## Entry 1: 3 Nov 2026: permission tests missed a check

**Asked:** AI to write can() and tests (deny by default, owner/read/edit grants, revoke, expiry, no automatic admin access).

**It produced:** can() plus a permission matrix test and tests for revoked, expired and deleted cases.

**What was wrong:** No test covered deactivated users. I commented out the is_active check and all 11 tests still passed.

**What I did instead:** Added test_deactivated_user_denied_even_as_owner and confirmed it fails when the check is removed. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/7dcb249


## Entry 2: 3 Nov 2026: no test for audited downloads

**Asked:** AI to write the upload, download and list routes, with tests that use two users over real HTTP.

**It produced:** Routes that call `require()` before touching a document, and a test that a refused download is written to the audit log.

**What was wrong:** No test covered a successful download being logged. I deleted the `audit.log(...)` call in the download route and all 21 tests still passed, so "prove who read it" was untested for the normal case.

**What I did instead:** Added `test_successful_download_is_audited` and confirmed it fails when the audit call is removed. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/ad800ab


## Entry 3: 3 Nov 2026: download route used the wrong permission name

**Asked:** AI to write the download route.

**It produced:** A route that calls `require(db, user, doc_id, "download")`.

**What was wrong:** I changed "download" to "read" in that call and all 21 tests still passed, so no test checks which permission the route asks for. Low risk today because read and download are always granted together.

**What I did instead:** Recorded it as an open item (T12 in THREATS.md) instead of pretending it was covered. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/0461afb

## Entry 4: 3 Nov 2026: downgrading a grant left the old permission active

**Asked:** AI to write grant and revoke routes with two-user tests.

**It produced:** A grant route that replaces earlier active grants, and tests for grant, revoke and viewer refusals.

**What was wrong:** No test covered downgrading. I removed the loop that revokes the earlier grant and all 29 tests still passed, so a user downgraded from edit to read would have kept edit access.

**What I did instead:** Added test_regrant_replaces_old_permission and confirmed it fails without the loop. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/f002cb7


## Entry 5: 4 Nov 2026: Postgres driver mismatch broke the first deploy

**Asked:** AI for a Render deployment setup using Postgres.

**It produced:** Instructions to install `psycopg2-binary` and a URL fix that only handled the `postgres://` prefix.

**What was wrong:** SQLAlchemy 2 defaults to the `psycopg` (v3) driver for `postgresql://` URLs, so the deploy crashed with `ModuleNotFoundError: No module named 'psycopg'`.

**What I did instead:** Read the Render log, found the missing module, and made the config use `postgresql+psycopg2://` explicitly. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/50057ea


## Entry 6: 4 Nov 2026: deactivation cleanup was untested

**Asked:** AI to write admin routes with a deactivate-user route that ends the user's sessions, plus tests.

**It produced:** A deactivate route that sets `is_active` to False and deletes the user's session rows, and a test that the old token fails on the next request.

**What was wrong:** I removed the session-delete line and all 39 tests still passed. The old token was still refused because `get_current_user` checks `is_active`, so access was safe, but nothing tested that the session rows were removed.

**What I did instead:** Added test_deactivation_deletes_session_rows and confirmed it fails without the delete call. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/f5fd065


## Entry 7: 5 Nov 2026: audit log could fork its own hash chain

**Asked:** AI to write a hash-chained audit log.

**It produced:** An `audit.log` that reads the last row, then writes the next one.

**What was wrong:** Two requests at the same moment could build on the same previous row, forking the chain. I flagged it as a known risk, then wrote a 15-thread test and it failed with `verify_chain` returning (False, 2).

**What I did instead:** Serialized the read-and-write with a lock and a Postgres advisory lock. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/f06992c


## Entry 8: 5 Nov 2026: timezone-aware expiry crashed the grant route

**Asked:** AI to write a grant route with an optional expiry date.

**It produced:** A route that compared the request's expiry directly with a timezone-naive `now()`.

**What was wrong:** An expiry like `2099-01-01T00:00:00Z` raised `TypeError: can't compare offset-naive and offset-aware datetimes`, which would have been a 500 error on the live site. My attack test caught it.

**What I did instead:** Converted the value to naive UTC before comparing and storing it. I removed the fix to check the test fails without it, and it did. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/caad97b


## Entry 9: 5 Nov 2026: huge IDs crashed Postgres but not SQLite

**Asked:** AI to write document, grant and admin routes.

**It produced:** Routes taking unbounded integer IDs.

**What was wrong:** `GET /documents/99999999999999999999` returned 500 on the live Postgres, while the local SQLite tests passed. My first fix covered documents and grants but missed the admin routes, which I noticed from `git status` showing admin.py absent from the commit.

**What I did instead:** Bounded IDs with `Path(ge=1, le=2147483647)` and bounded the admin filters. On the live site the calls now return 422. Commits: https://github.com/SKAbdurRahman/TrustVault/commit/a939a22 and https://github.com/SKAbdurRahman/TrustVault/commit/d096ff8


## Entry 10: 5 Nov 2026: deploy-hang fix had the timeout in the wrong place

**Asked:** AI to help stop a Render deploy that hung for 18m 30s with no output (Port scan timeout).

**It produced:** A `SET lock_timeout` in `scripts/setup_db.py` placed after the line that applies the trigger SQL, and a threat note that stated the cause as a lock held by another connection.

**What was wrong:** The timeout ran after the SQL it was meant to protect, so it protected nothing. The note also claimed a cause I never confirmed: the hang happened once and a manual redeploy worked.

**What I did instead:** Moved `SET lock_timeout = '30s'` before the trigger SQL, added a 10-second `connect_timeout` for Postgres in `app/db.py`, and rewrote T23 as "cause not confirmed, mitigated". Commits: https://github.com/SKAbdurRahman/TrustVault/commit/afc192a and https://github.com/SKAbdurRahman/TrustVault/commit/c544a08


## Entry 11: 6 Nov 2026: web app shipped with open CORS and a CSP that allowed everything

**Asked:** AI to add a web front end I could deploy to Netlify.

**It produced:** `index.html` plus Vercel and Netlify configs, with `allow_origins=["*"]` combined with `allow_credentials=True`, a Content-Security-Policy whose `connect-src` ended with `https:`, and a deployment guide saying the policy restricts external network connections.

**What was wrong:** `*` lets any website call the API from a browser. `https:` lets the page talk to any HTTPS site, which made the Render allow-list meaningless, so the guide overclaimed. It also left config files for Vercel, which I don't use.

**What I did instead:** Restricted CORS to my Netlify URL and local dev, removed `https:` and `localhost:*` from `connect-src`, deleted the unused Vercel and duplicate header files, and added a test that an unknown origin gets no CORS header. Then I logged in from the live Netlify site to confirm it still worked. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/0b55db6


## Entry 12: 7 Nov 2026: live database URL in the README

**Asked:** AI to document the trigger-verification script in the README.

**It produced:** A README line telling readers to set `VERIFY_DB_URL`, followed by a full connection string with the username and password.

**What was wrong:** The repo is public, so anyone could read and use the credentials for my database.

**What I did instead:** Replaced the line with a placeholder, created a new database credential in Render, pointed `DATABASE_URL` at it, and confirmed the app worked on it (health check, login, and the old credential showing 0 open connections). Then I deleted the old credential and ran `git grep` for leftovers. Because the old password stays in git history, I rotated it instead of only deleting the line. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/2e22588
