-- Close the company's open jobs that this fetch did not see.
UPDATE jobs
SET
    closed_at = %(refresh_time)s
WHERE
    company_id = %(company_id)s
    AND last_seen_at < %(refresh_time)s
    AND closed_at IS NULL;
