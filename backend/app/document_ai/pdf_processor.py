import fitz  # PyMuPDF
from PIL import Image
import io
from typing import List, Tuple
from pathlib import Path


class PDFProcessor:
    """Process PDF documents using PyMuPDF."""
    
    def __init__(self):
        self.dpi = 300  # Standard for OCR
    
    def get_page_count(self, pdf_bytes: bytes) -> int:
        """Get the number of pages in a PDF."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        doc.close()
        return page_count
    
    def pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        """
        Convert PDF pages to PIL Images.
        
        Args:
            pdf_bytes: Raw PDF file content
            
        Returns:
            List of PIL Image objects, one per page
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Render page to image
            pix = page.get_pixmap(dpi=self.dpi)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
        
        doc.close()
        return images
    
    def image_to_image(self, image_bytes: bytes) -> List[Image.Image]:
        """
        Convert image bytes to PIL Image (for non-PDF files).
        
        Args:
            image_bytes: Raw image file content
            
        Returns:
            List with single PIL Image object
        """
        img = Image.open(io.BytesIO(image_bytes))
        return [img]
    
    def process_document(self, file_bytes: bytes, filename: str) -> Tuple[List[Image.Image], int]:
        """
        Process a document (PDF or image) into images.
        
        Args:
            file_bytes: Raw file content
            filename: Original filename to determine type
            
        Returns:
            Tuple of (list of images, page count)
        """
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        
        if ext == "pdf":
            images = self.pdf_to_images(file_bytes)
        elif ext in ["png", "jpg", "jpeg", "tiff", "bmp"]:
            images = self.image_to_image(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        
        return images, len(images)
