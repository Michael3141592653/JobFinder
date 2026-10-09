-- Let only one update store at a time: a second one waits here until the first commits.
-- Postgres releases the lock by itself when the transaction ends.
SELECT PG_ADVISORY_XACT_LOCK(HASHTEXT('jobfinder.update'));
