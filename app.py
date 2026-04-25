from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
import pdfplumber
from docx import Document
from docx.shared import Inches
from pdf2docx import Converter
import logging
import re

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_text_pdf(pdf_path):
    """Smart text detection without heavy deps"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            sample_text = ""
            for page in pdf.pages[:2]:  # First 2 pages
                text = page.extract_text()
                if text and len(text.strip()) > 200:
                    sample_text += text
            return len(sample_text) > 1000
    except:
        return False

def perfect_text_extract(pdf_path, docx_path):
    """Pure Python perfect text extraction"""
    logger.info("✨ Perfect text extraction mode")
    
    doc = Document()
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract text with layout awareness
            words = page.extract_words()
            
            if words:
                # Group words by line (Y-coordinate)
                lines = {}
                for word in words:
                    y = round(word['top'], 2)
                    if y not in lines:
                        lines[y] = []
                    lines[y].append(word['text'])
                
                # Create paragraphs from lines
                for y in sorted(lines):
                    line_text = ' '.join(lines[y]).strip()
                    if line_text and len(line_text) > 3:
                        p = doc.add_paragraph(line_text)
                        p.paragraph_format.space_after = Inches(0.1)
            
            # Simple table detection (text blocks)
            tables = page.extract_tables(simple=True)
            for table in tables or []:
                if table and len(table) > 1:
                    # Create table from text blocks
                    rows = len(table)
                    cols = max(len(row) for row in table) if table else 1
                    t = doc.add_table(rows=rows, cols=cols)
                    
                    for i, row in enumerate(table):
                        for j, cell in enumerate(row or []):
                            if i < len(t.rows) and j < len(t.rows[i].cells):
                                t.rows[i].cells[j].text = str(cell).strip()
    
    doc.save(docx_path)
    logger.info("✅ Perfect text extraction complete!")

@app.route('/')
def home():
    return jsonify({
        'status': '🚀 Ultra-Light PDF to Word - Perfect Text + Images',
        'ready': True
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Please upload a valid PDF'}), 400
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{unique_id}_{secure_filename(file.filename)}"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)
        
        docx_path = pdf_path.replace('.pdf', '.docx')
        
        # Smart conversion
        if is_text_pdf(pdf_path):
            perfect_text_extract(pdf_path, docx_path)
            pdf_type = "text_perfect"
        else:
            logger.info("Using pdf2docx for layout")
            cv = Converter(pdf_path)
            cv.convert(docx_path)
            cv.close()
            pdf_type = "layout"
        
        # Cleanup
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        return jsonify({
            'success': True,
            'pdf_type': pdf_type,
            'message': f'Converted using {pdf_type} engine',
            'download_url': f'/api/download/{os.path.basename(docx_path)}',
            'filename': os.path.basename(docx_path)
        })
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True,
                        download_name=filename,
                        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    return jsonify({'error': 'File expired (re-upload to convert again)'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
