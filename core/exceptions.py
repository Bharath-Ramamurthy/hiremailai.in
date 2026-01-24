class SendEmailError(Exception):
    """Raised when sending an email fails."""

class PromptNotFoundError(Exception):
    """Raised when a required prompt is missing."""

class PDFGenerationError(Exception):
    """Raised when PDF generation fails."""

class ExtractTextError(Exception):
    """Raised when text extraction from a PDF fails."""

class OpenAIConnectorError(Exception):
    """Raised when an OpenAI connector operation fails."""

class HuggingFaceConnectorError(Exception):
    """Raised when a HuggingFace connector operation fails."""

class HTTPConnectorError(Exception):
    """Raised when an HTTP connector operation fails."""

class DiagnosticToolError(Exception):
    """Raised when a diagnostic tool fails or misconfigures a connector."""
    
class TexFileReadError(Exception):
 """Custom exception for errors in reading .tex files."""

