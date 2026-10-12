from dataclasses import dataclass


@dataclass(frozen=True)
class CvFile:
    """The CV as uploaded: a PDF or DOCX."""

    file_name: str
    file_bytes: bytes
