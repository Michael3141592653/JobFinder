-- Store an uploaded CV with what the LLM read from it.
INSERT INTO cvs (file_name, file_bytes, markdown, parsed_cv)
VALUES (%(file_name)s, %(file_bytes)s, %(markdown)s, %(parsed_cv)s)
RETURNING
    id;
