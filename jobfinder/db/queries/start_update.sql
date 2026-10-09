-- Let only one update store at a time, then return the time this update stores at.
-- A second update waits on the lock until the first commits; Postgres releases it at the end
-- of the transaction. MATERIALIZED makes the lock run first, so the time is read after the wait.
-- The time comes from the database, so updates from different machines share one clock.
WITH update_lock AS MATERIALIZED (
    SELECT PG_ADVISORY_XACT_LOCK(HASHTEXT('jobfinder.update'))
)

SELECT CLOCK_TIMESTAMP()
FROM update_lock;
