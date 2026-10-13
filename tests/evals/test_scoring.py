import pytest

from evals.cv_parsing.scoring import (
    IDENTIFYING_FIELDS,
    EntryWithWrongFields,
    ParsedCvScore,
    score_parsed_cv,
)
from jobfinder.cv.parsed_cv import Experience, ParsedCv, YearMonth

ACME_JOB = Experience(
    title="ML Engineer",
    company="Acme AI",
    start=YearMonth(year=2022, month=3),
    end=None,
    description="Built the search ranking.",
)

GROUND_TRUTH_CV = ParsedCv(
    location="Milan, Italy",
    experiences=[ACME_JOB],
    education=[],
    publications=[],
    skills=["Python", "PyTorch"],
    languages=["Italian (native)"],
)


def _get_cell_counts(parsed_cv_score: ParsedCvScore) -> tuple[int, int, int]:
    """Right, parsed and ground-truth cells. GROUND_TRUTH_CV has 9: a location, a job's 5 fields,
    2 skills and a language."""
    return (
        parsed_cv_score.right_cell_count,
        parsed_cv_score.parsed_cell_count,
        parsed_cv_score.ground_truth_cell_count,
    )


def test_score_parsed_cv_of_the_ground_truth_is_perfect():
    parsed_cv_score = score_parsed_cv(GROUND_TRUTH_CV, GROUND_TRUTH_CV)

    assert _get_cell_counts(parsed_cv_score) == (9, 9, 9)


def test_score_parsed_cv_counts_a_missed_entry_against_recall_only():
    parsed_cv = GROUND_TRUTH_CV.model_copy(update={"skills": ["Python"]})

    parsed_cv_score = score_parsed_cv(GROUND_TRUTH_CV, parsed_cv)

    assert _get_cell_counts(parsed_cv_score) == (8, 8, 9)


def test_score_parsed_cv_counts_an_extra_entry_against_precision_only():
    parsed_cv = GROUND_TRUTH_CV.model_copy(update={"skills": ["Python", "PyTorch", "Rust"]})

    parsed_cv_score = score_parsed_cv(GROUND_TRUTH_CV, parsed_cv)

    assert _get_cell_counts(parsed_cv_score) == (9, 10, 9)


def test_score_parsed_cv_reports_an_entry_with_a_wrong_field_field_by_field():
    wrong_job = ACME_JOB.model_copy(update={"end": YearMonth(year=2024, month=1)})
    parsed_cv = GROUND_TRUTH_CV.model_copy(update={"experiences": [wrong_job]})

    experiences_score = score_parsed_cv(GROUND_TRUTH_CV, parsed_cv).section_scores["experiences"]

    assert experiences_score.entries_with_wrong_fields == [
        EntryWithWrongFields("Acme AI, ML Engineer", 4, {"end": (None, {"year": 2024, "month": 1})})
    ]
    assert (experiences_score.missing_entries, experiences_score.extra_entries) == ([], [])


def test_score_parsed_cv_reports_an_entry_with_every_other_field_wrong_field_by_field():
    wrong_job = ACME_JOB.model_copy(
        update={
            "start": YearMonth(year=2020, month=1),
            "end": YearMonth(year=2021, month=1),
            "description": "Ran the payments team.",
        }
    )
    parsed_cv = GROUND_TRUTH_CV.model_copy(update={"experiences": [wrong_job]})

    experiences_score = score_parsed_cv(GROUND_TRUTH_CV, parsed_cv).section_scores["experiences"]

    assert [
        entry_with_wrong_fields.right_field_count
        for entry_with_wrong_fields in experiences_score.entries_with_wrong_fields
    ] == [2]


def test_score_parsed_cv_reports_an_entry_with_a_wrong_identity_as_missing_and_extra():
    wrong_job = ACME_JOB.model_copy(update={"company": "Acme"})
    parsed_cv = GROUND_TRUTH_CV.model_copy(update={"experiences": [wrong_job]})

    experiences_score = score_parsed_cv(GROUND_TRUTH_CV, parsed_cv).section_scores["experiences"]

    assert experiences_score.missing_entries == [ACME_JOB.model_dump(mode="json")]
    assert experiences_score.extra_entries == [wrong_job.model_dump(mode="json")]


def test_score_parsed_cv_counts_every_field_of_an_entry_with_a_wrong_identity_as_wrong():
    wrong_job = ACME_JOB.model_copy(update={"company": "Acme"})
    parsed_cv = GROUND_TRUTH_CV.model_copy(update={"experiences": [wrong_job]})

    parsed_cv_score = score_parsed_cv(GROUND_TRUTH_CV, parsed_cv)

    assert _get_cell_counts(parsed_cv_score) == (4, 9, 9)


def test_score_parsed_cv_counts_only_the_wrong_field_of_an_entry_as_wrong():
    wrong_job = ACME_JOB.model_copy(update={"end": YearMonth(year=2024, month=1)})
    parsed_cv = GROUND_TRUTH_CV.model_copy(update={"experiences": [wrong_job]})

    parsed_cv_score = score_parsed_cv(GROUND_TRUTH_CV, parsed_cv)

    assert _get_cell_counts(parsed_cv_score) == (8, 9, 9)


def test_score_parsed_cv_ignores_case_and_whitespace_in_descriptions():
    reworded_job = ACME_JOB.model_copy(update={"description": "built the  search ranking."})
    parsed_cv = GROUND_TRUTH_CV.model_copy(update={"experiences": [reworded_job]})

    assert score_parsed_cv(GROUND_TRUTH_CV, parsed_cv).right_cell_count == 9


def test_score_parsed_cv_counts_each_duplicate_once():
    parsed_cv = GROUND_TRUTH_CV.model_copy(update={"skills": ["Python", "Python"]})

    skills_score = score_parsed_cv(GROUND_TRUTH_CV, parsed_cv).section_scores["skills"]

    assert (skills_score.missing_entries, skills_score.extra_entries) == (["PyTorch"], ["Python"])


def test_score_parsed_cv_counts_no_location_on_both_sides_as_right():
    no_location_cv = GROUND_TRUTH_CV.model_copy(update={"location": None})

    location_score = score_parsed_cv(no_location_cv, no_location_cv).section_scores["location"]

    assert location_score.right_cell_count == 1


def test_f1_is_the_harmonic_mean_of_precision_and_recall():
    parsed_cv = GROUND_TRUTH_CV.model_copy(update={"skills": ["Python", "Rust"]})

    parsed_cv_score = score_parsed_cv(GROUND_TRUTH_CV, parsed_cv)

    assert parsed_cv_score.f1 == pytest.approx(8 / 9)


def test_identifying_fields_name_sections_of_the_parsed_cv():
    assert IDENTIFYING_FIELDS.keys() <= ParsedCv.model_fields.keys()
