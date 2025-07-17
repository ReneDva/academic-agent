import logging
from PyPDF2 import PdfReader
from typing import List, Tuple


class PDFProcessor:
    """
    Provides methods for validating and extracting text from PDF files.
    """

    @staticmethod
    def allowed_file(filename: str, allowed_extensions: set) -> bool:
        """
        Verifies the file has a permitted extension.

        Args:
            filename (str): Name of the uploaded file.
            allowed_extensions (set): Allowed file extensions.

        Returns:
            bool: True if file extension is valid.
        """
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

    @staticmethod
    def extract_text_per_page(file_stream) -> List[Tuple[int, str]]:
        """
        Extracts text from each page of a PDF.

        Args:
            file_stream: File-like object containing PDF data.

        Returns:
            List[Tuple[int, str]]: A list of tuples with page number and extracted text.
        """
        pdf_reader = PdfReader(file_stream)
        page_texts = []

        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                clean_text = page_text.strip() if page_text else ""
                if not clean_text:
                    logging.warning(f"Page {page_num + 1} is empty or unreadable.")
                    clean_text = "[No extractable text found]"
                page_texts.append((page_num + 1, clean_text))
            except Exception as e:
                logging.warning(f"Error extracting text from page {page_num + 1}: {e}")
                page_texts.append((page_num + 1, "[Text extraction failed]"))

        return page_texts
