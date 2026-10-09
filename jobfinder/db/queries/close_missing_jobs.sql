-- Close the company's open jobs that this fetch did not see.
UPDATE jobs
SET
    closed_at = %(seen_at)s
WHERE
    company_id = %(company_id)s
    AND last_seen < %(seen_at)s
    AND closed_at IS NULL;
