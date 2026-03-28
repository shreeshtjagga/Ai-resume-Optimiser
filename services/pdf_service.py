import PyPDF2
import io
 
 
def extract_text_from_pdf(file_bytes: bytes) -> str:
    
    text = ""
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()