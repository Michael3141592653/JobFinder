-- Jobs inserted by this fetch are the ones first seen at this fetch's time.
SELECT COUNT(*)
FROM jobs
WHERE
    company_id = %(company_id)s
    AND first_seen = %(refresh_time)s;
