"""Print a CV (PDF or Word) as the ParsedCv the LLM reads from it: `just parse-cv <file>`.
Needs Ollama running with the model pulled (`ollama pull qwen3:8b`)."""

import asyncio
import sys
from pathlib import Path

from jobfinder.cv.cv_file import CvFile
from jobfinder.cv.cv_parser import CvParser
from jobfinder.cv.text_extraction import CvTextExtractor
from jobfinder.llm.ollama import OllamaClient

# ponytail: hard-coded until the OLLAMA_URL, LLM_MODEL and LLM_CONTEXT_LENGTH settings exist
OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "qwen3:8b"
LLM_CONTEXT_LENGTH = 8192


def main(cv_path: Path) -> None:
    markdown = CvTextExtractor().extract_markdown(CvFile(cv_path.name, cv_path.read_bytes()))
    llm_client = OllamaClient(OLLAMA_URL, LLM_MODEL, LLM_CONTEXT_LENGTH)
    parsed_cv = asyncio.run(CvParser(llm_client).parse(markdown))
    print(parsed_cv.model_dump_json(indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
