import os
import shutil
from pathlib import Path
from typing import Optional
from app.config import settings


class FileStorage:
    def __init__(self):
        self.storage_path = Path(settings.storage_path)
        self.documents_path = self.storage_path / "documents"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create storage directories if they don't exist."""
        self.documents_path.mkdir(parents=True, exist_ok=True)
    
    def get_document_path(self, document_id: str) -> Path:
        """Get the base path for a document."""
        return self.documents_path / document_id
    
    def get_original_path(self, document_id: str) -> Path:
        """Get the path for the original document file."""
        return self.get_document_path(document_id) / "original"
    
    def get_pages_path(self, document_id: str) -> Path:
        """Get the path for processed page images."""
        return self.get_document_path(document_id) / "pages"
    
    def save_original(self, document_id: str, filename: str, content: bytes) -> Path:
        """Save the original uploaded document."""
        original_path = self.get_original_path(document_id)
        original_path.mkdir(parents=True, exist_ok=True)
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        file_path = original_path / safe_filename
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        return file_path
    
    def save_page(self, document_id: str, page_number: int, image_bytes: bytes) -> Path:
        """Save a processed page image."""
        pages_path = self.get_pages_path(document_id)
        pages_path.mkdir(parents=True, exist_ok=True)
        
        page_path = pages_path / f"page_{page_number:04d}.png"
        with open(page_path, "wb") as f:
            f.write(image_bytes)
        
        return page_path
    
    def get_original_file(self, document_id: str) -> Optional[Path]:
        """Get the original file path for a document."""
        original_path = self.get_original_path(document_id)
        if not original_path.exists():
            return None
        
        files = list(original_path.glob("*"))
        if files:
            return files[0]
        return None
    
    def get_page_files(self, document_id: str) -> list[Path]:
        """Get all page image files for a document."""
        pages_path = self.get_pages_path(document_id)
        if not pages_path.exists():
            return []
        
        return sorted(pages_path.glob("*.png"))
    
    def delete_document(self, document_id: str) -> bool:
        """Delete all files for a document."""
        doc_path = self.get_document_path(document_id)
        if doc_path.exists():
            shutil.rmtree(doc_path)
            return True
        return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        # Remove path separators
        safe_name = filename.replace("/", "").replace("\\", "")
        # Remove leading dots
        safe_name = safe_name.lstrip(".")
        # Keep only safe characters
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
        return safe_name or "document"
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes."""
        return file_path.stat().st_size if file_path.exists() else 0


file_storage = FileStorage()
