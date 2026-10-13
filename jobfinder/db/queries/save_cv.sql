-- Store an uploaded CV with what the LLM read from it, and which prompt and model read it.
INSERT INTO cvs (
    file_name,
    file_bytes,
    markdown,
    parsed_cv,
    prompt_version,
    llm_model
)
VALUES (
    %(file_name)s,
    %(file_bytes)s,
    %(markdown)s,
    %(parsed_cv)s,
    %(prompt_version)s,
    %(llm_model)s
)
RETURNING
    id;
