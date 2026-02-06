"""Document processing: parsing and chunking"""
import io
from pypdf import PdfReader
import logging
from config import PDF_CHUNK_SIZE, PDF_CHUNK_OVERLAP, TXT_CHUNK_OVERLAP, TXT_CHUNK_SIZE
from langchain_text_splitters import RecursiveCharacterTextSplitter
import hashlib

logger = logging.getLogger(__name__)

class DocumentProcessor:
    @staticmethod
    def process_pdf(content: bytes, filename: str, gcs_uri: str) -> list[dict]:
        """Extract text from pdf and chunk it"""
        text_content = ""
        reader = PdfReader(io.BytesIO(content))
        
        for page in reader.pages:
            text_content += page.extract_text() or ""
        logger.info(f"Extracted {len(text_content)} from pdf: {filename}")

        if not text_content or not text_content.strip():
            return []
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=PDF_CHUNK_SIZE, chunk_overlap=PDF_CHUNK_OVERLAP)

        return DocumentProcessor._create_chunks(text_content, text_splitter, filename, gcs_uri)
    
    @staticmethod
    def process_txt(content: bytes, filename: str, gcs_uri: str) -> list[dict]:
        """Extract text content from text file and chunk it"""
        text_content = content.decode("utf-8")
        logger.info(f"Extracted {len(text_content)} from txt: {filename}")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=TXT_CHUNK_SIZE, chunk_overlap=TXT_CHUNK_OVERLAP)

        return DocumentProcessor._create_chunks(text_content, text_splitter, filename, gcs_uri)
    
    @staticmethod
    def _create_chunks(text_content: str, text_splitter: RecursiveCharacterTextSplitter, filename: str, gcs_uri) -> list[dict]:
        all_chunks = []
        chunk_texts = text_splitter.split_text(text_content)

        for chunk_text in chunk_texts:
            if not chunk_text or not chunk_text.strip():
                continue    # skip empty chunks
            all_chunks.append({
                "id": hashlib.sha256(f"{filename}-{chunk_text}".encode("utf-8")).hexdigest(),
                "data": chunk_text, 
                "filename": filename,
                "gcs_uri": gcs_uri
            })
        logger.info(f"Created {len(all_chunks)} from {filename}")
        return all_chunks


            
        