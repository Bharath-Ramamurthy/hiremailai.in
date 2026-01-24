import pdfplumber
from core.logger import get_logger
from core.exceptions import ExtractTextError, TexFileReadError
logger = get_logger(__name__)



def extract_text_from_pdf(pdf_file) -> str:
    """
    Extracts text content from the uploaded PDF resume.
    
    Args:
        file path string the PDF.
        
    Returns:
        Extracted plain text as a string.
    """
    try:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text.strip()
        
    except Exception as error:
        
        logger.error(f"Text extraction failed due to: {error}")
        raise ExtractTextError(f"Text extraction failed due to: {error}")
        

def read_tex_file(tex_file):
    """
    Reads a LaTeX (.tex) file from either a file path or a Streamlit UploadedFile.
    Returns the file content as a UTF-8 string.
    """
    try:
        # Case 1: Streamlit UploadedFile (file-like object)
        if hasattr(tex_file, "read"):
            tex_file.seek(0)  # Reset pointer (important for Streamlit)
            content = tex_file.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            return content  

        # Case 2: Path string
        elif isinstance(tex_file, str) and tex_file.endswith(".tex"):
            with open(tex_file, "r", encoding="utf-8") as f:
                return f.read()

        else:
            raise TexFileReadError("Unsupported file input type.")

    except Exception as e:
        raise TexFileReadError(f"Failed to read .tex file: {e}")
