import pytest

from jobfinder.cv.cv_file import CvFile
from jobfinder.cv.parsed_cv import Experience, ParsedCv, YearMonth
from jobfinder.db.cv_store import CvStore

pytestmark = pytest.mark.anyio

UNKNOWN_CV_ID = 999_999
PROMPT_VERSION = 2
LLM_MODEL = "qwen3:8b"

PARSED_CV = ParsedCv(
    location="Milan, Italy",
    experiences=[
        Experience(
            title="ML Engineer",
            company="Acme AI",
            start=YearMonth(year=2022, month=3),
            end=None,
            description=None,
        )
    ],
    education=[],
    publications=[],
    skills=["Python", "PyTorch"],
    languages=["Italian (native)"],
)


async def test_find_unknown_id_returns_none(connection):
    assert await CvStore(connection).find(UNKNOWN_CV_ID) is None


async def test_save_then_find_returns_the_parsed_cv(connection):
    cv_store = CvStore(connection)
    cv_id = await cv_store.save(
        CvFile("cv.pdf", b"%PDF"), "ML Engineer at Acme AI", PARSED_CV, PROMPT_VERSION, LLM_MODEL
    )

    stored_cv = await cv_store.find(cv_id)

    assert stored_cv is not None
    assert (stored_cv.file_name, stored_cv.parsed_cv) == ("cv.pdf", PARSED_CV)


async def test_save_stores_the_file_and_its_markdown(connection):
    cv_id = await CvStore(connection).save(
        CvFile("cv.pdf", b"%PDF"), "ML Engineer", PARSED_CV, PROMPT_VERSION, LLM_MODEL
    )

    cv_cursor = await connection.execute(
        "SELECT file_bytes, markdown FROM cvs WHERE id = %s", [cv_id]
    )
    assert await cv_cursor.fetchone() == (b"%PDF", "ML Engineer")


async def test_save_stores_the_prompt_version_and_model_that_parsed_it(connection):
    cv_id = await CvStore(connection).save(
        CvFile("cv.pdf", b"%PDF"), "ML Engineer", PARSED_CV, PROMPT_VERSION, LLM_MODEL
    )

    cv_cursor = await connection.execute(
        "SELECT prompt_version, llm_model FROM cvs WHERE id = %s", [cv_id]
    )
    assert await cv_cursor.fetchone() == (PROMPT_VERSION, LLM_MODEL)


async def test_save_keeps_the_cvs_saved_before(connection):
    cv_store = CvStore(connection)
    first_cv_id = await cv_store.save(
        CvFile("first.pdf", b"%PDF"), "Junior", PARSED_CV, PROMPT_VERSION, LLM_MODEL
    )

    second_cv_id = await cv_store.save(
        CvFile("second.docx", b"PK"), "Senior", PARSED_CV, PROMPT_VERSION, LLM_MODEL
    )

    assert first_cv_id != second_cv_id
    assert await cv_store.find(first_cv_id) is not None


async def test_update_parsed_cv_replaces_it_with_the_corrected_one(connection):
    cv_store = CvStore(connection)
    cv_id = await cv_store.save(
        CvFile("cv.pdf", b"%PDF"), "ML Engineer", PARSED_CV, PROMPT_VERSION, LLM_MODEL
    )
    corrected_cv = PARSED_CV.model_copy(update={"location": "Turin, Italy"})

    await cv_store.update_parsed_cv(cv_id, corrected_cv)

    stored_cv = await cv_store.find(cv_id)
    assert stored_cv is not None
    assert stored_cv.parsed_cv == corrected_cv


async def test_save_stores_a_cv_never_corrected(connection):
    cv_store = CvStore(connection)
    cv_id = await cv_store.save(
        CvFile("cv.pdf", b"%PDF"), "ML Engineer", PARSED_CV, PROMPT_VERSION, LLM_MODEL
    )

    stored_cv = await cv_store.find(cv_id)

    assert stored_cv is not None
    assert stored_cv.corrected_at is None


async def test_update_parsed_cv_marks_it_corrected(connection):
    cv_store = CvStore(connection)
    cv_id = await cv_store.save(
        CvFile("cv.pdf", b"%PDF"), "ML Engineer", PARSED_CV, PROMPT_VERSION, LLM_MODEL
    )

    stored_cv = await cv_store.update_parsed_cv(cv_id, PARSED_CV)

    assert stored_cv is not None
    assert stored_cv.corrected_at is not None


async def test_update_parsed_cv_of_unknown_id_returns_none(connection):
    assert await CvStore(connection).update_parsed_cv(UNKNOWN_CV_ID, PARSED_CV) is None
