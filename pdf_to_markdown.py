import argparse
from pathlib import Path
from mistralai import Mistral
from mistralai import DocumentURLChunk
from mistralai.models import OCRResponse
import sys
import os
from dotenv import load_dotenv
from tqdm import tqdm
import re
from markdown_it import MarkdownIt
from mdit_plain.renderer import RendererPlain
import time
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

class MarkdownConverter:
    def __init__(self, api_key: str, cache_dir: str = ".pdf_cache"):
        self.client = Mistral(api_key=api_key)
        # Initialize the markdown parser with default renderer
        self.md_parser = MarkdownIt()
        # Set up cache directory
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_file_hash(self, file_path: str) -> str:
        """Generate SHA256 hash of file content for caching."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _get_cache_path(self, file_hash: str) -> Path:
        """Get cache file path for a given file hash."""
        return self.cache_dir / f"{file_hash}.json"
    
    def _load_from_cache(self, file_hash: str) -> str:
        """Load markdown text from cache if available."""
        cache_path = self._get_cache_path(file_hash)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    logger.info(f"Loaded PDF conversion from cache: {file_hash[:8]}...")
                    return cache_data['markdown_text']
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return None
    
    def _save_to_cache(self, file_hash: str, markdown_text: str):
        """Save markdown text to cache."""
        cache_path = self._get_cache_path(file_hash)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({'markdown_text': markdown_text}, f)
            logger.info(f"Saved PDF conversion to cache: {file_hash[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def replace_images_in_markdown(self, markdown_str, images_dict):
        for img_name, base64_str in images_dict.items():
            markdown_str = markdown_str.replace(
                f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})"
            )
        return markdown_str

    def markdown_to_text(self, markdown_str):
        """Convert markdown to plain text using regex-based cleaning."""
        try:
            # Use regex-based cleaning for plain text conversion
            text = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_str)  # Remove images
            text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)      # Convert links to text
            text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)  # Remove headers
            text = re.sub(r'^---\s*$', '', text, flags=re.MULTILINE)  # Remove horizontal rules
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)        # Remove bold
            text = re.sub(r'\*(.*?)\*', r'\1', text)            # Remove italic
            text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # Remove code blocks
            text = re.sub(r'`.*?`', '', text)                   # Remove inline code
            text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)  # Remove blockquotes
            text = re.sub(r'^[\*\-]\s+', '', text, flags=re.MULTILINE)  # Remove list markers
            text = re.sub(r'\n\s*\n', '\n\n', text)             # Normalize line breaks
            return text.strip()
        except Exception as e:
            print(f"Error processing text: {str(e)}")
            return markdown_str.strip()

    def get_combined_markdown(self, ocr_response: OCRResponse, embed_images=True):
        markdowns = []
        for page_num, page in enumerate(ocr_response.pages, 1):
            markdowns.append(f"\n## Page {page_num}\n---\n")
            image_data = {img.id: img.image_base64 for img in page.images}
            if embed_images:
                page_content = self.replace_images_in_markdown(page.markdown, image_data)
            else:
                # Remove image markdown lines
                lines = page.markdown.splitlines()
                lines = [line for line in lines if not line.strip().startswith('![')]
                page_content = '\n'.join(lines)
            markdowns.append(page_content)
            markdowns.append("\n")
        return "\n".join(markdowns)

    def convert_to_markdown(self, input_pdf_path: str, use_cache: bool = True):
        """
        Convert PDF to markdown with optional caching.
        
        Args:
            input_pdf_path: Path to PDF file
            use_cache: Whether to use cache (default: True)
            
        Returns:
            OCRResponse object or cached response dict
        """
        pdf_file = Path(input_pdf_path)
        if not pdf_file.is_file():
            raise FileNotFoundError(f"Input PDF file not found: {input_pdf_path}")
        
        # Check cache first
        if use_cache:
            file_hash = self._get_file_hash(input_pdf_path)
            cached_text = self._load_from_cache(file_hash)
            if cached_text:
                # Return a dict indicating cached response
                return {"cached": True, "markdown_text": cached_text}
        
        # OCR - use the existing client instance
        uploaded_file = self.client.files.upload(
            file={
                "file_name": pdf_file.stem,
                "content": pdf_file.read_bytes(),
            },
            purpose="ocr",
        )
        signed_url = self.client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)
        pdf_response = self.client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url.url),
            model="mistral-ocr-latest",
            include_image_base64=True
        )
        
        # Save to cache
        if use_cache:
            file_hash = self._get_file_hash(input_pdf_path)
            markdown_text = self.get_combined_markdown(pdf_response, embed_images=False)
            self._save_to_cache(file_hash, markdown_text)
        
        return pdf_response

def pdf_to_markdown_text(pdf_path: str, converter: MarkdownConverter, with_images=False, use_cache=True) -> str:
    """
    Process a single PDF file and return the markdown text.
    
    Args:
        pdf_path: Path to PDF file
        converter: MarkdownConverter instance
        with_images: Whether to include images in markdown
        use_cache: Whether to use cached conversion (default: True)
        
    Returns:
        Markdown text string
    """
    try:
        ocr_response = converter.convert_to_markdown(pdf_path, use_cache=use_cache)
        
        # Handle cached response
        if isinstance(ocr_response, dict) and ocr_response.get("cached"):
            logger.info(f"Using cached PDF conversion for {Path(pdf_path).name}")
            return ocr_response["markdown_text"]
        
        # Process normal OCR response
        markdown_text = converter.get_combined_markdown(ocr_response, embed_images=with_images)
        return markdown_text
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")
        raise

def process_pdf(pdf_path: Path, converter: MarkdownConverter):
    """Process a single PDF file and generate markdown and text outputs."""
    try:
        out_base = pdf_path.with_suffix('')
        out_md_with_images = f"{out_base}_with_images.md"
        out_md_no_images = f"{out_base}_no_images.md"
        out_txt = f"{out_base}.txt"
        
        markdown_with_images = pdf_to_markdown_text(str(pdf_path), converter, with_images=True)
        markdown_no_images = pdf_to_markdown_text(str(pdf_path), converter, with_images=False)

        # With images
        with open(out_md_with_images, 'w', encoding='utf-8') as f:
            f.write(markdown_with_images)
        
        # Without images
        with open(out_md_no_images, 'w', encoding='utf-8') as f:
            f.write(markdown_no_images)
        
        # Plain text version
        plain_text = converter.markdown_to_text(markdown_no_images)
        with open(out_txt, 'w', encoding='utf-8') as f:
            f.write(plain_text)
            
        return True, f"Successfully processed {pdf_path.name}"
    except Exception as e:
        return False, f"Error processing {pdf_path.name}: {str(e)}"

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Convert PDF(s) to Markdown and plain text using Mistral OCR.")
    parser.add_argument('--input_pdf', required=True, help='Path to the input PDF file or directory containing PDF files')
    args = parser.parse_args()
    
    input_path = Path(args.input_pdf)
    api_key = os.environ.get('MISTRAL_API_KEY')
    if not api_key:
        print("Error: MISTRAL_API_KEY environment variable not set.")
        sys.exit(1)
    
    # Create converter with shared client instance
    converter = MarkdownConverter(api_key=api_key)
    
    if input_path.is_file() and input_path.suffix.lower() == '.pdf':
        # Process single PDF
        success, message = process_pdf(input_path, converter)
        print(message)
    elif input_path.is_dir():
        # Process all PDFs in directory
        pdf_files = list(input_path.glob('*.pdf'))
        if not pdf_files:
            print(f"No PDF files found in {input_path}")
            sys.exit(1)
            
        print(f"Found {len(pdf_files)} PDF files to process")
        success_count = 0
        error_count = 0
        
        for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
            success, message = process_pdf(pdf_file, converter)
            if success:
                success_count += 1
            else:
                error_count += 1
                print(f"\n{message}")
            
            # Add delay between processing files to avoid socket exhaustion
            time.sleep(1)
        
        print(f"\nProcessing complete:")
        print(f"Successfully processed: {success_count} files")
        print(f"Failed to process: {error_count} files")
    else:
        print(f"Error: {input_path} is not a valid PDF file or directory")
        sys.exit(1)

if __name__ == "__main__":
    main() 