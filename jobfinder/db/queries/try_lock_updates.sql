-- Take the update lock if no other update holds it: true if taken, false otherwise.
-- A session lock: held across transactions until unlocked or the connection closes.
SELECT PG_TRY_ADVISORY_LOCK(HASHTEXT('jobfinder.update'));
