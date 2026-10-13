"""Score a parsed CV against its ground truth cell by cell, as ExtractBench does: a cell is a
plain entry, e.g. one skill, or one field of a record, e.g. a job's end date, so a job with one
wrong field still gets its other fields right. Precision is how many parsed cells are right, recall
how many ground-truth cells were found, F1 their balance. Plain code, no LLM, so the same answers
always get the same score."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Any, cast

from jobfinder.cv.parsed_cv import ParsedCv

# A job, a degree or a publication as JSON: field name -> value, e.g. a date as {year, month}
Record = dict[str, Any]
# A section's entry: a record, plain text such as a skill or the location, or None for no location
Entry = Record | str | None

# What tells an entry apart: an entry with these right but other fields wrong is reported field
# by field, however many are wrong, instead of as missing and extra. Sections not
# listed (skills, languages, location) are plain text.
IDENTIFYING_FIELDS = {
    "experiences": ("company", "title"),
    "education": ("institution", "degree"),
    "publications": ("title",),
}


@dataclass(frozen=True)
class EntryWithWrongFields:
    """A ground-truth entry parsed with some or all of its fields wrong, except its identifying
    fields: field -> (ground truth, parsed)."""

    name: str
    right_field_count: int
    field_differences: dict[str, tuple[Any, Any]]

    @property
    def field_count(self) -> int:
        return self.right_field_count + len(self.field_differences)


@dataclass(frozen=True)
class SectionScore:
    right_cell_count: int
    parsed_cell_count: int
    ground_truth_cell_count: int
    entries_with_wrong_fields: list[EntryWithWrongFields]
    missing_entries: list[Entry]
    extra_entries: list[Entry]


@dataclass(frozen=True)
class ParsedCvScore:
    section_scores: dict[str, SectionScore]

    @property
    def right_cell_count(self) -> int:
        return sum(section_score.right_cell_count for section_score in self.section_scores.values())

    @property
    def parsed_cell_count(self) -> int:
        return sum(
            section_score.parsed_cell_count for section_score in self.section_scores.values()
        )

    @property
    def ground_truth_cell_count(self) -> int:
        return sum(
            section_score.ground_truth_cell_count for section_score in self.section_scores.values()
        )

    @property
    def f1(self) -> float:
        """The harmonic mean of precision and recall. Never divides by zero: the location is always
        a cell."""
        return 2 * self.right_cell_count / (self.parsed_cell_count + self.ground_truth_cell_count)


def _list_entries(section: Any) -> list[Entry]:
    """A section's entries: the location is a section with one entry."""
    return section if isinstance(section, list) else [section]


def _count_cells(entry: Entry) -> int:
    """A record has a cell per field, e.g. a date is one cell; anything else is one cell."""
    return len(entry) if isinstance(entry, dict) else 1


def _normalize_field_value(field_name: str, value: Any) -> Any:
    """Descriptions are long text: case and whitespace don't count. The rest must be exact."""
    if field_name == "description" and isinstance(value, str):
        return " ".join(value.casefold().split())
    return value


def _normalize_entry(entry: Entry) -> Entry:
    if isinstance(entry, dict):
        return {
            field_name: _normalize_field_value(field_name, value)
            for field_name, value in entry.items()
        }
    return entry


def _get_identity(record: Record, identifying_fields: tuple[str, ...]) -> list[Any]:
    return [record[field_name] for field_name in identifying_fields]


def _is_same_entry(ground_truth_entry: Entry, parsed_entry: Entry) -> bool:
    return _normalize_entry(ground_truth_entry) == _normalize_entry(parsed_entry)


def _has_same_identity(
    ground_truth_record: Record, parsed_record: Record, identifying_fields: tuple[str, ...]
) -> bool:
    return _get_identity(ground_truth_record, identifying_fields) == _get_identity(
        parsed_record, identifying_fields
    )


def _find_field_differences(
    ground_truth_record: Record, parsed_record: Record
) -> dict[str, tuple[Any, Any]]:
    return {
        field_name: (ground_truth_value, parsed_record[field_name])
        for field_name, ground_truth_value in ground_truth_record.items()
        if _normalize_field_value(field_name, ground_truth_value)
        != _normalize_field_value(field_name, parsed_record[field_name])
    }


def _build_entry_with_wrong_fields(
    ground_truth_record: Record, parsed_record: Record, identifying_fields: tuple[str, ...]
) -> EntryWithWrongFields:
    field_differences = _find_field_differences(ground_truth_record, parsed_record)
    return EntryWithWrongFields(
        name=", ".join(
            str(value) for value in _get_identity(ground_truth_record, identifying_fields)
        ),
        right_field_count=len(ground_truth_record) - len(field_differences),
        field_differences=field_differences,
    )


class SectionScorer:
    """Scores one section. Every ground-truth entry starts missing and every parsed entry extra;
    each match crosses one off both lists, so neither matches twice. First the entries parsed
    exactly are matched, then, of the rest, the ones with the same identifying fields. What is
    left is missing or extra."""

    def __init__(
        self, identifying_fields: tuple[str, ...], ground_truth_section: Any, parsed_section: Any
    ) -> None:
        self._identifying_fields = identifying_fields
        self._ground_truth_entries = _list_entries(ground_truth_section)
        self._parsed_entries = _list_entries(parsed_section)
        self._missing_entries: list[Entry] = []
        self._extra_entries: list[Entry] = []

    def _find_extra_entry_index(
        self, ground_truth_entry: Entry, is_match: Callable[[Any, Any], bool]
    ) -> int | None:
        """An index, not the entry: an entry can be None, e.g. no location."""
        return next(
            (
                index
                for index, extra_entry in enumerate(self._extra_entries)
                if is_match(ground_truth_entry, extra_entry)
            ),
            None,
        )

    def _cross_off_matching_pairs(
        self, is_match: Callable[[Any, Any], bool]
    ) -> list[tuple[Entry, Entry]]:
        """Pairs each missing entry with the first extra entry it matches, and crosses both off."""
        pairs = []
        for ground_truth_entry in list(self._missing_entries):
            extra_entry_index = self._find_extra_entry_index(ground_truth_entry, is_match)
            if extra_entry_index is not None:
                self._missing_entries.remove(ground_truth_entry)
                pairs.append((ground_truth_entry, self._extra_entries.pop(extra_entry_index)))
        return pairs

    def _match_exact_entries(self) -> list[Entry]:
        return [
            ground_truth_entry
            for ground_truth_entry, _ in self._cross_off_matching_pairs(_is_same_entry)
        ]

    def _match_entries_with_wrong_fields(self) -> list[EntryWithWrongFields]:
        if not self._identifying_fields:
            return []  # an empty identity would match any two entries
        identity_pairs = self._cross_off_matching_pairs(
            partial(_has_same_identity, identifying_fields=self._identifying_fields)
        )
        # sections with identifying fields hold records
        return [
            _build_entry_with_wrong_fields(
                cast(Record, ground_truth_entry),
                cast(Record, parsed_entry),
                self._identifying_fields,
            )
            for ground_truth_entry, parsed_entry in identity_pairs
        ]

    def score(self) -> SectionScore:
        self._missing_entries = list(self._ground_truth_entries)
        self._extra_entries = list(self._parsed_entries)
        exact_entries = self._match_exact_entries()
        entries_with_wrong_fields = self._match_entries_with_wrong_fields()
        return SectionScore(
            right_cell_count=sum(map(_count_cells, exact_entries))
            + sum(entry.right_field_count for entry in entries_with_wrong_fields),
            parsed_cell_count=sum(map(_count_cells, self._parsed_entries)),
            ground_truth_cell_count=sum(map(_count_cells, self._ground_truth_entries)),
            entries_with_wrong_fields=entries_with_wrong_fields,
            missing_entries=self._missing_entries,
            extra_entries=self._extra_entries,
        )


def score_parsed_cv(ground_truth_cv: ParsedCv, parsed_cv: ParsedCv) -> ParsedCvScore:
    ground_truth_sections = ground_truth_cv.model_dump(mode="json")
    parsed_sections = parsed_cv.model_dump(mode="json")
    return ParsedCvScore(
        {
            section_name: SectionScorer(
                IDENTIFYING_FIELDS.get(section_name, ()),
                ground_truth_section,
                parsed_sections[section_name],
            ).score()
            for section_name, ground_truth_section in ground_truth_sections.items()
        }
    )
