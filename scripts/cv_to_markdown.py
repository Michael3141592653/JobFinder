"""Print a CV (PDF or Word) as the Markdown the LLM reads: `just cv-markdown <file>`."""

import sys
from pathlib import Path

from jobfinder.cv.text_extraction import CvTextExtractor


def main(cv_path: Path) -> None:
    print(CvTextExtractor().extract_markdown(cv_path.name, cv_path.read_bytes()))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
