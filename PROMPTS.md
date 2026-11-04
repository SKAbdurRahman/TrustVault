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
