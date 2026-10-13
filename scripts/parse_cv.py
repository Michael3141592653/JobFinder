"""Print a CV (PDF or Word) as the ParsedCv the LLM reads from it: `just parse-cv <file>`.
Needs Ollama running with LLM_MODEL pulled (`ollama pull <model>`)."""

import asyncio
import sys
from pathlib import Path

from jobfinder.cv.cv_file import CvFile
from jobfinder.cv.cv_parser import CvParser
from jobfinder.cv.text_extraction import CvTextExtractor
from jobfinder.llm.ollama import OllamaClient
from jobfinder.settings import LLMSettings


def main(cv_path: Path) -> None:
    markdown = CvTextExtractor().extract_markdown(CvFile(cv_path.name, cv_path.read_bytes()))
    llm_client = OllamaClient.from_settings(LLMSettings())
    parsed_cv = asyncio.run(CvParser(llm_client).parse(markdown))
    print(parsed_cv.model_dump_json(indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
