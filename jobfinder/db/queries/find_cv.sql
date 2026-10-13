-- One CV, without its file: it is large and needed only to download it or parse it again.
SELECT
    id AS cv_id,
    file_name,
    parsed_cv,
    uploaded_at,
    corrected_at
FROM cvs
WHERE
    id = %(cv_id)s;
