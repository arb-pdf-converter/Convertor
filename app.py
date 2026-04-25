from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
import fitz  # PyMuPDF
import pdfplumber
from docx import Document
from docx.shared import Inches
from pdf2docx import Converter
import logging

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

def is_text_heavy_pdf(pdf_path):
    """Simple text detection"""
    try:
        with fitz.open(pdf_path) as doc:
            total_chars = 0
            for page in doc:
                text = page.get_text()
                total_chars += len(text)
            return total_chars > 5000  # >5K chars = text heavy
    except:
        return False

def convert_text_pdf(pdf_path, docx_path):
    """Perfect text conversion"""
    doc = Document()
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract with layout preservation
            text = page.extract_text(x_tolerance=2, y_tolerance=2, layout=True)
            
            if text:
                p = doc.add_paragraph(text)
                p.paragraph_format.space_after = Inches(0.1)
            
            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                if table and len(table) > 1:
                    rows = len(table)
                    cols = len(table[0])
                    t = doc.add_table(rows=rows, cols=cols)
                    for i, row in enumerate(table):
                        for j, cell in enumerate(row):
                            if i < len(t.rows) and j < len(t.rows[i].cells):
                                t.rows[i].cells[j].text = str(cell or '')
    
    doc.save(docx_path)

@app.route('/')
def home():
    return jsonify({'status': 'Perfect PDF to Word API ✅'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid PDF'}), 400
        
        # Save file
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{unique_id}_{secure_filename(file.filename)}"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)
        
        docx_path = pdf_path.replace('.pdf', '.docx')
        
        # Choose best converter
        if is_text_heavy_pdf(pdf_path):
            logger.info("📄 Text-heavy PDF - using advanced converter")
            convert_text_pdf(pdf_path, docx_path)
        else:
            logger.info("🖼️ Image-heavy PDF - using pdf2docx")
            cv = Converter(pdf_path)
            cv.convert(docx_path)
            cv.close()
        
        os.remove(pdf_path)  # Cleanup
        
        return jsonify({
            'success': True,
            'download_url': f'/api/download/{os.path.basename(docx_path)}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
