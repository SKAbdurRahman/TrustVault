# THREATS.md

Each entry: the attack, what I did about it, how it is tested, and its status.
"Open" means I know about it and have not fixed it yet. I would rather say so than hide it.

## T1: IDOR (changing the document ID in the URL)
**Attack:** A logged-in user edits /documents/42 to /documents/43 to reach someone else's file.
**What I did:** Every document route will call `require()` in `app/permissions.py`, which calls `can()`. It checks the database on every request and denies by default. A refused request returns 404, so a user cannot tell whether a document exists.
**Test:** `tests/test_permissions.py` (permission matrix). Route-level two-user tests are planned for Wednesday.
**Status:** Core check built. Route-level HTTP tests still to come.

## T2: Access still works after revocation or expiry
**Attack:** A user whose grant was revoked or has expired keeps reading the file.
**What I did:** Sessions and permissions live in the database, not in a self-contained token. `can()` re-reads the grants on every request and ignores revoked and expired ones. Grants are never deleted, only marked with `revoked_at`.
**Test:** `test_revoked_and_expired_grants_stop_working`.
**Evidence:** I removed the revoked check and the test failed (assert not can(...) at line 57). I also removed the expiry check and the test failed again. Both checks are protected by `test_revoked_and_expired_grants_stop_working`.
**Status:** Fixed.

## T3: Deleted documents still readable
**Attack:** A document the owner deleted is still reachable by ID.
**What I did:** Deletion is a soft delete (`deleted_at`). `can()` refuses any document with `deleted_at` set, even for the owner.
**Test:** `test_deleted_document_and_unknown_action_denied`.
**Evidence:** I removed the `deleted_at` check and the test failed, so the test protects that line.
**Status:** Fixed.

## T4: Deactivated user keeps access
**Attack:** An account the admin deactivated can still use documents it owns or was granted.
**What I did:** `can()` returns False if the user is missing or `is_active` is False. The login and session lookup also refuse inactive users.
**Test:** `test_deactivated_user_denied_even_as_owner`.
**Evidence:** I removed the `is_active` check and all 11 existing tests still passed, so my test suite had a gap. I added the test above, and it fails when the check is removed. Commit 7dcb249.
**Status:** Fixed.

## T5: Admin reading everything
**Attack:** A compromised or curious admin account reads confidential documents.
**What I did:** My design decision: admins manage users and see the activity view, but `can()` has no admin shortcut. An admin can read a document only if someone granted it.
**Test:** The permission matrix asserts that an admin without a grant is refused.
**Status:** Fixed by design. Cost: an admin cannot recover a document if its owner leaves the company. I accept that for now.

## T6: Tampering with the audit trail
**Attack:** Someone edits or deletes audit rows to hide who read a document.
**What I did:**
- Each audit row stores the hash of the previous row. `verify_chain()` detects an edited or reordered row.
- Refused attempts are logged too, not just successful ones.
- On Postgres, database triggers (`sql/audit_triggers.sql`, applied by `scripts/setup_db.py`) reject UPDATE, DELETE and TRUNCATE on `audit_log`.
- The app code never issues UPDATE or DELETE on that table.
**Test:** `test_tampering_is_detected` and `test_refused_login_is_logged_and_chain_is_valid` (these run on SQLite, where triggers are not applied, so the hash chain is what they test).
**Status:** Partly open.
- **Verified on the live Postgres (5 Nov 2026):** UPDATE, DELETE and TRUNCATE on `audit_log` were each rejected with `audit_log is append-only`, using `scripts/verify_triggers.py`.
- Whoever owns the database can still drop the triggers (see T18).

## T7: Two requests writing the audit log at the same moment
**Risk:** Both read the same "last row" and the chain forks, making verification fail.
**What I did:** Audit writes run under a process lock, and on Postgres also under an advisory transaction lock, from reading the last row until the commit.
**Test:** `test_concurrent_audit_writes_do_not_fork_the_chain` (15 threads, hashing slowed to widen the race).
**Evidence:** Before adding the lock, this test failed with `verify_chain` returning (False, 2), so the fork was real. With the lock it passes, and removing the lock again makes it fail.
**Status:** Fixed for threads, and for multiple processes on Postgres. The Postgres advisory lock is not covered by an automated test, because the tests run on SQLite.

## T8: Guessing passwords (brute force)
**Attack:** An attacker tries many passwords against a known username.
**What I did:** Passwords are hashed with Argon2. After 5 failed logins per username or 20 per IP in 15 minutes, login returns 429, even for the correct password. Counts are stored in the database, so they survive restarts. A lockout is written to the audit log once. Unknown usernames are throttled the same way, so lockouts don't reveal which accounts exist.
**Test:** `tests/test_ratelimit.py` (7 tests).
**Evidence:** I removed the check, changed `>=` to `>`, removed the failure recording and removed the counter reset, one at a time, and each made at least one test fail. On the live Render site, six wrong logins for a made-up user gave 5 x 401 then 429 with `retry-after: 900`, and one `login_lockout` row appeared in the activity log.
**Status:** Fixed, with open risks: anyone can lock a known username for 15 minutes by failing on purpose; `X-Forwarded-For` can be faked, so the per-IP limit is best-effort and the per-username limit is the real protection; failed-login `details` still stores the typed username.

## T9: Discovering which usernames exist
**Risk:** `/auth/register` answers "Username already taken".
**What I did:** Nothing yet. Login errors are identical for a wrong username and a wrong password.
**Status:** **Knowingly accepted for now.** Usernames are not secret inside a company, and fixing it would hurt usability. I will revisit it if time allows.

## T10: Registering as admin
**Attack:** A new user sends `"role": "admin"` in the register request.
**What I did:** The role is never read from the request. New accounts are always `user`.
**Test:** `test_cannot_self_register_as_admin`.
**Status:** Fixed.

## T11: Using a session after logout
**Attack:** A stolen or old token keeps working after the user logs out.
**What I did:** Sessions are stored in the database, and only a hash of the token is stored. Logout deletes the session.
**Test:** `test_logout_revokes_token_immediately`.
**Status:** Fixed.

## T12: Download route uses the wrong permission name
**What I found:** Changing "download" to "read" in the download route did not fail any test.
**Status:** Open (low risk today). Read and download are always granted together. Becomes real if I add a read-only-no-download permission.

## T13: Fake file type or oversized upload
**Attack:** Upload a program renamed to .pdf, or a huge file to exhaust memory.
**What I did:** The type is decided from the file's first bytes, not its name or the browser's claim. Reads stop at the 5 MB limit plus one byte.
**Test:** `test_fake_extension_rejected`, `test_oversized_file_rejected`.
**Status:** Fixed for the allowed types. Plain text accepts any UTF-8 content, which is a known limit.

## T14: Path traversal in file names
**Attack:** A name like ../../etc/passwd to write or read outside the storage folder.
**What I did:** Files are stored under a random name. The user's file name is only used for display, with path parts stripped.
**Test:** `test_path_traversal_name_is_harmless`.
**Status:** Fixed.

## T15: Search leaking other users' documents
**Attack:** Searching for words to discover titles of documents the user cannot open.
**What I did:** The list and search query only ever selects documents the user owns or holds a valid grant for.
**Test:** `test_search_and_list_never_show_other_users_documents`.
**Evidence:** I removed the owner/granted filter and the test failed.
**Status:** Fixed.

## T16: Successful downloads not logged
**Attack/risk:** A file leaves the server and nothing records who took it.
**What I did:** The download route logs before sending the file.
**Test:** `test_successful_download_is_audited`.
**Evidence:** I deleted the audit call and all 21 original tests still passed, so I added this test and confirmed it fails without the call.
**Status:** Fixed.

## T17: Uploaded files lost on free-tier redeploy
**Risk:** Render's free disk is wiped on every redeploy, so user uploads disappear.
**What I did:** The seed script recreates the demo files. Real uploads are not preserved.
**Status:** Knowingly accepted for the challenge. A real deployment would use persistent storage or object storage.

## T18: Audit protection depends on database triggers
**Risk:** Triggers block UPDATE, DELETE and TRUNCATE on `audit_log` for the app, but whoever owns the database could drop them.
**What I did:** The hash chain still detects edits, and the app never issues UPDATE or DELETE on that table.
**Status:** Partly open. The triggers were verified against the live Postgres on 5 Nov 2026: UPDATE, DELETE and TRUNCATE on `audit_log` were each rejected with `audit_log is append-only` (see T6 and `scripts/verify_triggers.py`). What remains open is that whoever owns the database can still drop the triggers, so the log is protected against the app, not against the database owner.

## T19: Live demo accounts
**Risk:** Demo accounts exist on the live site.
**What I did:** Random passwords set through environment variables, never committed to the repo. They guard demo data only.
**Status:** Accepted. Sessions are revoked by logout, and the live test confirmed it.

## T20: Viewer or editor using owner-only routes
**Attack:** A user with read or edit access calls grant, revoke, list-grants or delete, or upgrades their own permission.
**What I did:** Those routes call `require()` with the `grant` or `delete` action, which only the owner passes. Refusals return 404 and are logged.
**Test:** `test_viewer_cannot_grant_revoke_list_edit_or_delete`, `test_editor_can_edit_but_not_delete_or_grant`.
**Evidence:** Changing `"grant"` to `"read"` in the list-grants route and `"delete"` to `"edit"` in the delete route each made a test fail.
**Status:** Fixed.

## Live check on Render (4 Nov 2026)
Owner saw both demo documents. Viewer saw only the shared one; downloading it returned 200 and downloading the private one returned 404. A request with no token returned 401. Logout deleted the session.

## T21: Admin routes
**Attack:** A normal user calls admin routes, or an admin misuses their power.
**What I did:** Every admin route depends on `require_admin`. Non-admins get the same 404 as an unknown URL, and the attempt is logged. Admins manage users and read the audit log but have no automatic access to document contents. Deactivation deletes the user's sessions. An admin cannot deactivate or change the role of themselves.
**Test:** `test_normal_user_refused_on_every_admin_route_and_it_is_logged`, `test_admin_has_no_automatic_access_to_document_contents`, `test_deactivation_ends_sessions_immediately_and_blocks_login`, `test_admin_cannot_deactivate_self`, `test_admin_changes_are_audited`.
**Evidence:** I disabled the admin check, the self-deactivate guard and the role-change audit line one at a time, and each made at least one test fail. Removing the session delete did not fail any test until I added `test_deactivation_deletes_session_rows`.
**Status:** Fixed, with these **open** risks: one compromised admin can promote others with no second approval, two admins could deactivate each other and leave no admin, and failed-login `details` stores the typed username (people sometimes type a password there).

## T22: Tests run on SQLite, production runs Postgres
**Risk:** Some bugs only appear on Postgres (a huge ID crashed it with a 500 while SQLite tests passed).
**What I did:** Bounded all ID parameters and verified the fix with live calls.
**Status:** Open. A real project would run the test suite against Postgres too.

## T23: Deploy hung on startup once
**Risk:** One deploy printed nothing after the start command began and was timed out by Render after 18m 30s (Port scan timeout). A manual redeploy worked.
**Cause:** Not confirmed. Possible causes are a database lock, the database being briefly unreachable, or free-tier slowness.
**What I did:** Added a 30-second lock timeout and a 10-second connection timeout, so a repeat fails fast with a clear error.
**Status:** Mitigated, cause not proven.

## Still to cover (known gaps)
- Admin account creation is only through the seed script and the promote-role route; there is no self-service path
- Uploaded text files shown in the browser (HTML or script in a .txt); downloads are forced as attachments with `nosniff`, but plain text accepts any UTF-8 content
- The "who can read" rule in the list route is written by hand instead of calling `can()`, so the two could drift apart if one is changed later
- Lockout can be used against a known username (it expires after 15 minutes), and `X-Forwarded-For` can be faked, so the per-IP limit is best-effort (see T8)
- Free-tier disk is wiped on redeploy, so real uploads are lost (see T17)
- Tests run on SQLite while production runs Postgres (see T22), so some bugs only show live
- A deploy hung once, cause unconfirmed (see T23)” so it matches the new T23 wording












