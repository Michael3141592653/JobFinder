"""Postgres storage for the CVs: each with its file, its text and what the LLM read from it."""

from datetime import datetime

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict

from jobfinder.cv.cv_file import CvFile
from jobfinder.cv.parsed_cv import ParsedCv
from jobfinder.db.sql import fetch_value, find_row, load_query

_SAVE_CV = load_query("save_cv")
_FIND_CV = load_query("find_cv")
_UPDATE_PARSED_CV = load_query("update_parsed_cv")


class StoredCv(BaseModel):
    """Built from a row by its column names: Pydantic turns the parsed_cv JSON into a ParsedCv."""

    model_config = ConfigDict(frozen=True)

    cv_id: int
    file_name: str
    parsed_cv: ParsedCv
    uploaded_at: datetime
    corrected_at: datetime | None  # None: still as the LLM read it


def _to_jsonb(parsed_cv: ParsedCv) -> Jsonb:
    return Jsonb(parsed_cv.model_dump(mode="json"))


class CvStore:
    """Reads and writes the CVs. It never commits: the DatabaseSession around it decides that."""

    def __init__(self, connection: psycopg.AsyncConnection) -> None:
        self._connection = connection

    async def save(
        self,
        cv_file: CvFile,
        markdown: str,
        parsed_cv: ParsedCv,
        prompt_version: int,
        llm_model: str,
    ) -> int:
        """Store an uploaded CV and return its id. The file and its text are kept to read it again
        later, e.g. with a better model, without uploading it again; the prompt version and the
        model tell which CVs need it."""
        params = {
            "file_name": cv_file.file_name,
            "file_bytes": cv_file.file_bytes,
            "markdown": markdown,
            "parsed_cv": _to_jsonb(parsed_cv),
            "prompt_version": prompt_version,
            "llm_model": llm_model,
        }
        return await fetch_value(self._connection, _SAVE_CV, params)

    async def find(self, cv_id: int) -> StoredCv | None:
        return await find_row(self._connection, _FIND_CV, {"cv_id": cv_id}, StoredCv)

    async def update_parsed_cv(self, cv_id: int, parsed_cv: ParsedCv) -> StoredCv | None:
        """Store the user's corrections. None if there is no CV with this id."""
        params = {"cv_id": cv_id, "parsed_cv": _to_jsonb(parsed_cv)}
        return await find_row(self._connection, _UPDATE_PARSED_CV, params, StoredCv)
