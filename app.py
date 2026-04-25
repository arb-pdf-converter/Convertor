from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
import fitz  # PyMuPDF for text extraction
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pdfplumber
import camelot
import pandas as pd
from pdf2docx import Converter
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def detect_pdf_type(pdf_path):
    """Detect if PDF has images, tables, or mostly text"""
    with fitz.open(pdf_path) as doc:
        text_pages = 0
        image_pages = 0
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            images = page.get_images()
            
            if len(text.strip()) > 100:  # Mostly text
                text_pages += 1
            if images:
                image_pages += 1
        
        if text_pages / total_pages > 0.7:
            return "text_heavy"
        elif image_pages / total_pages > 0.3:
            return "image_heavy"
        else:
            return "mixed"

def convert_text_pdf(pdf_path, docx_path):
    """Advanced text PDF conversion - preserves formatting"""
    logger.info("🔤 Using advanced text converter")
    
    doc = Document()
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract text with layout info
            text = page.extract_text(layout=True)
            
            if text:
                # Create paragraph with original formatting
                p = doc.add_paragraph()
                p.add_run(text)
                
                # Try to preserve font size/spacing
                p.paragraph_format.space_after = Inches(0.1)
                p.paragraph_format.line_spacing = 1.15
            
            # Extract tables
            tables = page.extract_tables()
            for table_data in tables:
                if table_data:
                    df = pd.DataFrame(table_data[1:], columns=table_data[0])
                    table = doc.add_table(rows=1, cols=len(df.columns))
                    table.style = 'Table Grid'
                    
                    hdr_cells = table.rows[0].cells
                    for i, col in enumerate(df.columns):
                        hdr_cells[i].text = str(col)
                    
                    for _, row in df.iterrows():
                        row_cells = table.add_row().cells
                        for i, val in enumerate(row):
                            row_cells[i].text = str(val)
    
    doc.save(docx_path)
    logger.info(f"✅ Text conversion complete: {len(pdf.pages)} pages")

def convert_image_pdf(pdf_path, docx_path):
    """Fallback to pdf2docx for image-heavy PDFs"""
    logger.info("🖼️ Using pdf2docx for image-heavy PDF")
    cv = Converter(pdf_path)
    cv.convert(docx_path, start=0, end=None)
    cv.close()

@app.route('/')
def home():
    return jsonify({
        'message': '🚀 Perfect PDF to Word API (Text + Images)',
        'engines': ['pdf2docx (images)', 'PyMuPDF+pdfplumber (text)']
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        logger.info("📥 Convert request received")
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files allowed'}), 400
        
        # Save uploaded file
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{unique_id}_{secure_filename(file.filename)}"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)
        
        logger.info(f"📄 Saved: {pdf_path}")
        
        # Detect PDF type and choose best converter
        pdf_type = detect_pdf_type(pdf_path)
        logger.info(f"📊 Detected PDF type: {pdf_type}")
        
        docx_path = pdf_path.replace('.pdf', '.docx')
        
        if pdf_type == "text_heavy":
            convert_text_pdf(pdf_path, docx_path)
        else:
            convert_image_pdf(pdf_path, docx_path)
        
        # Cleanup PDF
        os.remove(pdf_path)
        
        return jsonify({
            'success': True,
            'message': f'Perfect conversion using {pdf_type} engine!',
            'download_url': f'/api/download/{os.path.basename(docx_path)}',
            'filename': os.path.basename(docx_path),
            'pdf_type': pdf_type
        })
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True,
                        download_name=filename,
                        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    return jsonify({'error': 'File expired'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
