-- Replace what the LLM read with the user's corrected version.
UPDATE cvs
SET
    parsed_cv = %(parsed_cv)s,
    corrected_at = NOW()
WHERE
    id = %(cv_id)s
RETURNING
    id AS cv_id,
    file_name,
    parsed_cv,
    uploaded_at,
    corrected_at;
