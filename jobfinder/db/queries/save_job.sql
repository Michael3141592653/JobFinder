-- Insert a new job, or update a known one: first_seen stays, last_seen moves, closed_at clears.
INSERT INTO jobs (
    company_id,
    provider_job_id,
    title,
    locations,
    url,
    description,
    posted_at,
    updated_at,
    first_seen,
    last_seen
)
VALUES (
    %(company_id)s,
    %(provider_job_id)s,
    %(title)s,
    %(locations)s,
    %(url)s,
    %(description)s,
    %(posted_at)s,
    %(updated_at)s,
    %(refresh_time)s,
    %(refresh_time)s
)
ON CONFLICT (company_id, provider_job_id) DO UPDATE
    SET
        title = excluded.title,
        locations = excluded.locations,
        url = excluded.url,
        description = excluded.description,
        posted_at = excluded.posted_at,
        updated_at = excluded.updated_at,
        last_seen = excluded.last_seen,
        closed_at = NULL;
