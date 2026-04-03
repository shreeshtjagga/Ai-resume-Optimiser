import io
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = _extract_with_pdfplumber(file_bytes)

    if not text:
        logger.warning("pdfplumber returned no text, falling back to PyPDF2.")
        text = _extract_with_pypdf2(file_bytes)

    if not text:
        raise ValueError(
            "No extractable text found. The PDF may be scanned or image-based. "
            "Please upload a text-selectable PDF or a DOCX file."
        )

    return text


def _extract_with_pdfplumber(file_bytes: bytes) -> str:
    try:
        import pdfplumber  # optional but preferred

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
                if page_text:
                    pages.append(page_text.strip())
            return "\n\n".join(pages).strip()
    except ImportError:
        logger.info("pdfplumber not installed; skipping.")
        return ""
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
        return ""


def _extract_with_pypdf2(file_bytes: bytes) -> str:
    try:
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text.strip())
        return "\n\n".join(pages).strip()
    except Exception as e:
        logger.warning(f"PyPDF2 extraction failed: {e}")
        return ""