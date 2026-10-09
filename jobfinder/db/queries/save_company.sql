-- Insert or update a company and return its id.
-- The name is NULL when the fetch failed: keep the known name (or use the slug for a new company).
INSERT INTO companies (
    provider,
    slug,
    name,
    last_fetched_at,
    last_error
)
VALUES (
    %(provider)s,
    %(slug)s,
    COALESCE(%(name)s, %(slug)s),
    %(update_time)s,
    %(error)s
)
ON CONFLICT (provider, slug) DO UPDATE
    SET
        name = COALESCE(%(name)s, companies.name),
        last_fetched_at = excluded.last_fetched_at,
        last_error = excluded.last_error
RETURNING
    id;
