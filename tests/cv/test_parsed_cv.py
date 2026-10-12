import pytest
from pydantic import ValidationError

from jobfinder.cv.parsed_cv import Publication, YearMonth


@pytest.mark.parametrize("month", [0, 13])
def test_year_month_rejects_a_month_outside_1_to_12(month):
    with pytest.raises(ValidationError, match="month"):
        YearMonth(year=2022, month=month)


def test_text_fields_reject_an_empty_string():
    with pytest.raises(ValidationError, match="at least 1 character"):
        Publication(title="Latent Diffusion for CT", venue="", year=2024)
