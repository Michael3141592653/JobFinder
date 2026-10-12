import re
from io import BytesIO
from pathlib import Path

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.settings import settings
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.exceptions import ConversionError
from docling_core.types.doc import DoclingDocument, NodeItem, TextItem

from jobfinder.cv.cv_file import CvFile

# Where `uv run docling-tools models download` puts them: read locally, never downloaded on use.
DOCLING_MODELS = settings.cache_dir / "models"
SUPPORTED_SUFFIXES = {".pdf", ".docx"}

_DATE = r"(?:(?:\d{1,2}[/.]|[a-z]{3,9}\.?\s+)?\d{4})"  # "2023", "03/2025", "Mar 2021"
DATE_RANGE = re.compile(
    rf"{_DATE}\s*(?:-|–|—|to)\s*(?:{_DATE}|present|current|now|today|ongoing)", re.IGNORECASE
)


class CvConversionError(Exception):
    pass


class UnsupportedCvFormatError(CvConversionError):
    def __init__(self, file_name: str) -> None:
        super().__init__(f"{file_name}: send the CV as .pdf or .docx (save an old .doc as .docx)")


class CvUnreadableError(CvConversionError):
    def __init__(self, file_name: str) -> None:
        super().__init__(f"{file_name} can't be read: is it a damaged or protected file?")


class CvWithoutTextError(CvConversionError):
    def __init__(self, file_name: str) -> None:
        super().__init__(f"{file_name} has no text")


def _get_texts_with_a_position(document: DoclingDocument) -> list[TextItem]:
    """Only a PDF's texts have one: a page and a box. A DOCX's have none."""
    return [
        item for item, _ in document.iterate_items() if isinstance(item, TextItem) and item.prov
    ]


def _find_title_left_of(date_range: TextItem, texts: list[TextItem]) -> TextItem | None:
    """The nearest text on the same line, left of the date range: the title it belongs to."""
    date_place = date_range.prov[0]
    on_its_left = [
        item
        for item in texts
        if item is not date_range
        and item.prov[0].page_no == date_place.page_no
        and item.prov[0].bbox.r <= date_place.bbox.l
        and item.prov[0].bbox.y_overlap_with(date_place.bbox) > date_place.bbox.height / 2
    ]
    return max(on_its_left, key=lambda item: item.prov[0].bbox.r, default=None)


def _move_dates_onto_their_titles(document: DoclingDocument) -> None:
    """Right-aligned dates ("Engineer ...... 2021 - Present") line up like a narrow column, so
    the layout model reads them after everything else: put each back after its title."""
    texts = _get_texts_with_a_position(document)
    date_ranges = [text for text in texts if DATE_RANGE.fullmatch(text.text.strip())]
    moved_date_ranges: list[NodeItem] = []
    for date_range in date_ranges:
        title = _find_title_left_of(date_range, texts)
        if title is not None:
            title.text = f"{title.text} | {date_range.text.strip()}"
            moved_date_ranges.append(date_range)
    if moved_date_ranges:
        document.delete_items(node_items=moved_date_ranges)


def _raise_if_unsupported(file_name: str) -> None:
    if Path(file_name).suffix.lower() not in SUPPORTED_SUFFIXES:
        raise UnsupportedCvFormatError(file_name)


def _export_markdown(document: DoclingDocument, file_name: str) -> str:
    # for the LLM, not a renderer: escaping would turn "R&D" into "R&amp;D"
    markdown = document.export_to_markdown(
        escape_html=False, escape_underscores=False, image_placeholder=""
    ).strip()
    if not markdown:
        raise CvWithoutTextError(file_name)
    return markdown


class CvTextExtractor:
    """Build once: the first file loads the layout model (about 6 s)."""

    def __init__(self, models_path: Path = DOCLING_MODELS) -> None:
        pdf_options = PdfPipelineOptions(
            artifacts_path=models_path,
            accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU),
            # it takes CVs laid out as tables for data tables and shuffles their cells: one
            # job went missing in the RenderCV classic template
            do_table_structure=False,
        )
        self._converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF, InputFormat.DOCX],
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)},
        )

    def _convert_to_docling_document(self, cv_file: CvFile) -> DoclingDocument:
        document_stream = DocumentStream(name=cv_file.file_name, stream=BytesIO(cv_file.file_bytes))
        try:
            return self._converter.convert(document_stream).document
        except ConversionError as error:
            raise CvUnreadableError(cv_file.file_name) from error

    def extract_markdown(self, cv_file: CvFile) -> str:
        """The CV as Markdown. CPU work: call it in a thread."""
        _raise_if_unsupported(cv_file.file_name)
        document = self._convert_to_docling_document(cv_file)
        _move_dates_onto_their_titles(document)
        return _export_markdown(document, cv_file.file_name)
