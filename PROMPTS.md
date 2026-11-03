## Entry 1: 3 Nov 2026: permission tests missed a check

**Asked:** AI to write can() and tests (deny by default, owner/read/edit grants, revoke, expiry, no automatic admin access).

**It produced:** can() plus a permission matrix test and tests for revoked, expired and deleted cases.

**What was wrong:** No test covered deactivated users. I commented out the is_active check and all 11 tests still passed.

**What I did instead:** Added test_deactivated_user_denied_even_as_owner and confirmed it fails when the check is removed. Commit: https://github.com/SKAbdurRahman/TrustVault/commit/7dcb24928263e8c102c09c2628830b9827a5946a
