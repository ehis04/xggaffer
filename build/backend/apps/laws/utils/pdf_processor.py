import io
from pdf2image import convert_from_path, convert_from_bytes
from pypdf import PdfReader
import base64

class PDFProcessor:
    
    @staticmethod
    def extract_text(pdf_path):
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n\n"
        return text
    
    @staticmethod
    def pdf_to_images(pdf_path, dpi=150):
        try:
            images = convert_from_path(pdf_path, dpi=dpi)
            return images
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return []
    
    @staticmethod
    def image_to_base64(image):
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    @staticmethod
    def split_pdf_by_law(pdf_path):
        reader = PdfReader(pdf_path)
        law_sections = []
        
        current_law = None
        start_page = 0
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            
            import re
            law_match = re.search(r'LAW\s+(\d+)', text, re.IGNORECASE)
            
            if law_match:
                if current_law is not None:
                    law_sections.append((current_law, start_page, i - 1))
                
                current_law = int(law_match.group(1))
                start_page = i
        
        if current_law is not None:
            law_sections.append((current_law, start_page, len(reader.pages) - 1))
        
        return law_sections