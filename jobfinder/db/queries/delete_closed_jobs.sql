-- Delete jobs closed before the cutoff, so the table holds only recent history.
DELETE FROM jobs
WHERE
    closed_at < %(closed_before)s;
