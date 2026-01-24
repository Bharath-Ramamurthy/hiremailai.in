import subprocess
import os
from datetime import datetime
from core.logger import get_logger
import re
from core.exceptions import PDFGenerationError

logger = get_logger(__name__)

import re

def sanitize_latex_output(latex_code: str) -> str:
 

    # --- Convert escaped newlines to actual newlines ---
    latex_code = latex_code.replace("\\n", "\n")

    # --- Fix \usepackage{\command} → \usepackage{command} ---
    latex_code = re.sub(r'\\usepackage\{\\(\w+)\}', r'\\usepackage{\1}', latex_code)

    # --- Convert '\%' at start of line to '%' (proper comment) ---
    latex_code = re.sub(r'(?m)^[ \t]*\\%(?=\s|$)', '%', latex_code)

    # --- General fix for missing backslashes in LaTeX commands ---
    # Common LaTeX commands
    known_commands = {
        "noindent", "normalsize", "small", "tiny", "large", "Large", "LARGE", "huge", "Huge",
        "textbf", "textit", "underline", "emph", "item", "section", "subsection", "subsubsection",
        "paragraph", "subparagraph", "texttt", "textsc", "centering", "raggedright", "raggedleft",
        "today", "vspace", "hspace", "newline", "linebreak", "newpage", "clearpage", "tableofcontents",
        "maketitle", "author", "title", "date", "begin", "end", "includegraphics", "caption",
        "label", "ref", "cite", "url", "footnote", "itemize", "enumerate", "flushleft",
        "flushright", "center", "rule", "bfseries", "itshape", "ttfamily", "scshape",
        "textwidth", "textheight", "linewidth", "parindent", "baselineskip", "textcolor",
        "color", "pagebreak", "nopagebreak", "hfill", "vfill", "hline", "cline"
    }

    # Fix missing backslashes
    pattern = re.compile(r'(?<!\\)(?<=\s|^|\{)(' + "|".join(re.escape(cmd) for cmd in known_commands) + r')(?=\s|\\|{|$)')
    latex_code = pattern.sub(r'\\\1', latex_code)

    # --- Fix misused math-mode vertical bars --- 
    # Replace any variant of $ \vert $ with $|$
    latex_code = re.sub(r'\$\s*\\?vert\s*\$', r'$|$', latex_code)
    latex_code = re.sub(r'\$\s*\|\s*\$', r'$|$', latex_code)

    # --- Flatten nested \textbf recursively ---
    def flatten_textbf(text):
        prev = None
        while prev != text:
            prev = text
            text = re.sub(r'\\textbf\{([^{}]*?)\\textbf\{(.*?)\}([^{}]*?)\}', r'\\textbf{\1\2\3}', text, flags=re.S)
        return text
    latex_code = flatten_textbf(latex_code)

    # --- Correct \begin{\env} and \end{\env} ---
    latex_code = re.sub(r'\\begin\{\\(\w+)\}', r'\\begin{\1}', latex_code)
    latex_code = re.sub(r'\\end\{\\(\w+)\}', r'\\end{\1}', latex_code)

    # --- Fix common typos like \end-to-\end → end-to-end ---
    latex_code = re.sub(r'\\end-to-\\end', r'end-to-end', latex_code)

    # --- Remove redundant \noindent inside list environments ---
    for env in ["itemize", "enumerate"]:
        latex_code = re.sub(
            rf'\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}',
            lambda m: f"\\begin{{{env}}}" + re.sub(r'\\noindent', '', m.group(1)) + f"\\end{{{env}}}",
            latex_code,
            flags=re.S
        )

    # --- Remove comments safely ---
    latex_code = re.sub(r'(?m)(?<!\\)%.*$', '', latex_code)

    # --- Escape unescaped LaTeX special characters ---
    latex_code = re.sub(r'(?<!\\)&', r'\&', latex_code)
    latex_code = re.sub(r'(?<!\\)_', r'\_', latex_code)
    latex_code = re.sub(r'(?<!\\)#', r'\#', latex_code)

    # --- Escape stray $ signs (not part of math) ---
    latex_code = re.sub(r'(?<!\$)\$(?!\$)', r'\$', latex_code)

    # --- Ensure LaTeX document structure ---
    if not re.search(r'\\documentclass', latex_code):
        latex_code = "\\documentclass[11pt,a4paper]{article}\n" + latex_code
    if not re.search(r'\\begin\{document\}', latex_code):
        latex_code += "\n\\begin{document}"
    if not re.search(r'\\end\{document\}', latex_code):
        latex_code += "\n\\end{document}"

    # --- Auto-close unclosed environments ---
    open_envs = re.findall(r'\\begin\{(\w+)\}', latex_code)
    for env in open_envs:
        if not re.search(r'\\end\{' + re.escape(env) + r'\}', latex_code):
            latex_code += f"\n\\end{{{env}}}"

    # --- Balance braces ---
    diff = latex_code.count("{") - latex_code.count("}")
    if diff > 0:
        latex_code += "}" * diff

    # --- Normalize spacing ---
    latex_code = re.sub(r'\n{3,}', '\n\n', latex_code)
    latex_code = re.sub(r'[ \t]+', ' ', latex_code)
    latex_code = re.sub(r' *\n *', '\n', latex_code)
    latex_code = latex_code.strip()

    return latex_code




def create_pdf_from_latex(latex_code_raw, output_filename="document.pdf", output_dir=None):
    """
    Compiles LaTeX code into a PDF file using pdflatex.

    Args:
        latex_code (str): The raw LaTeX code to compile.
                          It is assumed this string is a complete LaTeX document.
        output_filename (str): The desired name for the output PDF file.
    """
    if output_dir is None:
        output_dir = os.getenv("DATA_DIR")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)


    # Use a unique temporary .tex file name to avoid conflicts
    timestamp_for_temp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_tex_base = f"temp_{timestamp_for_temp}"
    temp_tex_file = os.path.join(output_dir, f"{temp_tex_base}.tex")
    
    pdf_output_path = os.path.join(output_dir, output_filename)


   
    #latex_code =  sanitize_latex_output(latex_code_raw)

    with open(temp_tex_file, "w", encoding="utf-8") as f:
        f.write(latex_code_raw)

    try:
        compile_command = [
            "pdflatex",
            "-interaction=nonstopmode",  # Don't prompt for input on errors
            "-output-directory", output_dir,  # Place output files in generated_docs
            temp_tex_file
        ]
        result = subprocess.run(compile_command, check=True, capture_output=True, text=True)

        # The output PDF will have the same base name as the .tex file
        generated_pdf_name = f"{temp_tex_base}.pdf"
        generated_pdf_path = os.path.join(output_dir, generated_pdf_name)

        if os.path.exists(generated_pdf_path):
            if generated_pdf_path != pdf_output_path:
                os.rename(generated_pdf_path, pdf_output_path)
            print(f"PDF created successfully: {pdf_output_path}")
        else:
            logger.error("PDF output not found after compilation.")
            raise RuntimeError("PDF output not found after compilation.")

        # Clean up temporary files (aux, log, etc. generated by pdflatex)
        temp_files_to_clean = [
            f"{temp_tex_base}.aux",
            f"{temp_tex_base}.log",
            f"{temp_tex_base}.fls",
            f"{temp_tex_base}.fdb_latexmk"  # Generated by latexmk if used
        ]
        for ext in temp_files_to_clean:
            file_to_remove = os.path.join(output_dir, ext)
            if os.path.exists(file_to_remove):
                os.remove(file_to_remove)
        
        os.remove(temp_tex_file)  # Remove the .tex file itself

        return pdf_output_path

    except subprocess.CalledProcessError as e:
        logger.error(f"LaTeX compilation failed returncode={e.returncode} STDOUT={e.stdout} STDERR={e.stderr}")

        # Attempt to clean up temp .tex file even if compilation failed
        if os.path.exists(temp_tex_file):
            os.remove(temp_tex_file)
        raise  # Re-raise the exception after logging

    except Exception as e:
        logger.error(f"Latex to PDF Generation Error occurred: {e}")
        if os.path.exists(temp_tex_file):
            os.remove(temp_tex_file)
        raise PDFGenerationError(f"Latex to PDF Generation Error due to: {e}")


def generate_pdf(latex_code: str, file_name: str, output_dir: str) -> str:
    """
    Generates a PDF from provided LaTeX code for a resume.
    Ensures proper logging, directory handling, and error management.

    Args:
        latex_code (str): The complete LaTeX code for the resume.

    Returns:
        str: The path to the generated PDF file.

    Raises:
        ValueError: If latex_code is empty.
        RuntimeError: If PDF generation fails.
    """

    if not latex_code or not latex_code.strip():
        logger.error("Empty LaTeX code received for PDF generation.")
        raise ValueError("LaTeX code cannot be empty.")

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{file_name}_{timestamp}.pdf"

        os.makedirs(output_dir, exist_ok=True)
        
        file_path = create_pdf_from_latex(latex_code, output_filename, output_dir)
        if not os.path.exists(file_path):
            raise RuntimeError(f"PDF generation failed: {file_path} not found.")

        return file_path

    except Exception as e:
        logger.critical(f"PDF generation failed: {str(e)}", exc_info=True)
        raise RuntimeError("Failed to generate PDF")
