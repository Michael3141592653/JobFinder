"""Score the CV parser on the golden set: `just eval-cv`. Each CV in cases/ with a
<name>.ground_truth.json beside it is a case; your own CVs go in cases/private/, which git ignores.
Runs the real model: needs Ollama running."""

import asyncio
import json
import sys
from pathlib import Path

from evals.cv_parsing.scoring import EntryWithWrongFields, ParsedCvScore, score_parsed_cv
from jobfinder.cv.cv_file import CvFile
from jobfinder.cv.cv_parser import CvParser
from jobfinder.cv.parsed_cv import ParsedCv
from jobfinder.cv.text_extraction import SUPPORTED_SUFFIXES, CvTextExtractor
from jobfinder.llm.ollama import OllamaClient
from jobfinder.settings import LLMSettings

CASES = Path(__file__).parent / "cases"
GROUND_TRUTH_SUFFIX = ".ground_truth.json"


def _find_cv_paths() -> list[Path]:
    """Every CV that has a ground truth; one without isn't a case."""
    return [
        cv_path
        for cv_path in sorted(CASES.rglob("*"))
        if cv_path.suffix.lower() in SUPPORTED_SUFFIXES
        and cv_path.with_suffix(GROUND_TRUTH_SUFFIX).exists()
    ]


def _load_ground_truth_cv(cv_path: Path) -> ParsedCv:
    ground_truth_text = cv_path.with_suffix(GROUND_TRUTH_SUFFIX).read_text(encoding="utf-8")
    return ParsedCv.model_validate_json(ground_truth_text)


def _extract_markdowns(cv_paths: list[Path]) -> list[str]:
    text_extractor = CvTextExtractor()
    return [
        text_extractor.extract_markdown(CvFile(cv_path.name, cv_path.read_bytes()))
        for cv_path in cv_paths
    ]


async def _parse_markdowns(markdowns: list[str]) -> list[ParsedCv]:
    """In one event loop: the Ollama client's connections belong to the loop that opened them."""
    cv_parser = CvParser(OllamaClient.from_settings(LLMSettings()))
    return [await cv_parser.parse(markdown) for markdown in markdowns]


def _print_entry_with_wrong_fields(
    section_name: str, entry_with_wrong_fields: EntryWithWrongFields
) -> None:
    print(
        f"  {section_name} found, {entry_with_wrong_fields.right_field_count}"
        f"/{entry_with_wrong_fields.field_count} fields right: {entry_with_wrong_fields.name}"
    )
    field_differences = entry_with_wrong_fields.field_differences
    for field_name, (ground_truth_value, parsed_value) in field_differences.items():
        print(
            f"    {field_name}: ground truth {json.dumps(ground_truth_value)},"
            f" parsed {json.dumps(parsed_value)}"
        )


def _print_parsed_cv_score(cv_name: str, parsed_cv_score: ParsedCvScore) -> None:
    print(
        f"{cv_name}  F1 {parsed_cv_score.f1:.3f}"
        f"  precision {parsed_cv_score.right_cell_count}/{parsed_cv_score.parsed_cell_count}"
        f"  recall {parsed_cv_score.right_cell_count}/{parsed_cv_score.ground_truth_cell_count}"
    )
    for section_name, section_score in parsed_cv_score.section_scores.items():
        for entry_with_wrong_fields in section_score.entries_with_wrong_fields:
            _print_entry_with_wrong_fields(section_name, entry_with_wrong_fields)
        for missing_entry in section_score.missing_entries:
            print(f"  {section_name} missing: {json.dumps(missing_entry)}")
        for extra_entry in section_score.extra_entries:
            print(f"  {section_name} extra:   {json.dumps(extra_entry)}")


def main() -> None:
    cv_paths = _find_cv_paths()
    if not cv_paths:
        sys.exit(f"No case in {CASES}: put a <name>{GROUND_TRUTH_SUFFIX} beside each CV")
    # first: a typo in a hand-written ground truth fails before the slow steps, not as a miss
    ground_truth_cvs = [_load_ground_truth_cv(cv_path) for cv_path in cv_paths]
    markdowns = _extract_markdowns(cv_paths)
    parsed_cvs = asyncio.run(_parse_markdowns(markdowns))
    for cv_path, ground_truth_cv, parsed_cv in zip(
        cv_paths, ground_truth_cvs, parsed_cvs, strict=True
    ):
        _print_parsed_cv_score(cv_path.name, score_parsed_cv(ground_truth_cv, parsed_cv))


if __name__ == "__main__":
    main()
