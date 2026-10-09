import pytest

from jobfinder.text import html_to_text


@pytest.mark.parametrize(
    ("markup", "expected"),
    [
        pytest.param("<p>Hi <b>there</b></p>", "Hi there", id="strips-tags"),
        pytest.param("<h2>About</h2><p>Role</p>", "About\nRole", id="one-line-per-block"),
        pytest.param("<ul><li>A</li><li>B</li></ul>", "A\nB", id="one-line-per-list-item"),
        pytest.param("Tom &amp; Jerry&nbsp;Inc", "Tom & Jerry Inc", id="decodes-entities"),
        pytest.param("<p>  a \n\t b  </p><p> </p>", "a b", id="collapses-whitespace"),
        pytest.param("", "", id="empty-input"),
    ],
)
def test_html_to_text(markup, expected):
    assert html_to_text(markup) == expected
