import tiktoken
import tempfile
from pathlib import Path

from pypdf import PdfReader
from docx import Document as DocxDocument
from fastapi import UploadFile

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks based on token count"""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)
        start += chunk_size - overlap

    return chunks

def parse_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def parse_docx(file_path: str) -> str:
    """Extract text from DOCX file"""
    doc = DocxDocument(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def parse_txt(file_path: str) -> str:
    """Read text from TXT file"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def parse_file(file_path: str, content_type: str) -> str:
    """Route to correct parser based on content type"""
    if content_type == "application/pdf":
        return parse_pdf(file_path)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return parse_docx(file_path)
    elif content_type == "text/plain":
        return parse_txt(file_path)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")


async def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded file to temp location, return file path"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload_file.filename).suffix) as tmp_file:
        content = await upload_file.read()
        tmp_file.write(content)
        return tmp_file.name