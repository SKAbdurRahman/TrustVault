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
**What I did:** Each audit row stores the hash of the previous row. `verify_chain()` detects an edited or reordered row. Refused attempts are logged too.
**Test:** `test_tampering_is_detected`, `test_refused_login_is_logged_and_chain_is_valid`.
**Status:** **Partly open.** The chain does not detect rows deleted from the end of the log. Planned fix: database triggers in `sql/schema.sql` that block UPDATE and DELETE on `audit_log`, plus a database account for the app that cannot alter that table.

## T7: Two requests writing the audit log at the same moment
**Attack/risk:** Both read the same "last row" and the chain forks, making verification fail.
**What I did:** Nothing yet.
**Status:** **Open.** Planned fix: write audit rows inside a lock or a serialized transaction.

## T8: Guessing passwords (brute force)
**Attack:** An attacker tries many passwords against a known username.
**What I did:** Passwords are hashed with Argon2. Failed logins are logged. Unknown usernames take about the same time as real ones.
**Status:** **Open.** There is no rate limit or lockout yet. Planned: limit failed attempts per username and per IP.

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

## Still to cover (grants, revoke and delete routes are not built yet)
These are on my list and I will write full entries once the code exists:
- A viewer calling owner-only routes (grant, revoke, delete)
- Granting yourself access, or granting beyond what you were given
- Uploaded text files shown in the browser (HTML or script in a .txt)
- Rebuilding the "who can read" rule by hand in the list route instead of calling can()














