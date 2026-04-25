from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
import pdfplumber
from docx import Document
from docx.shared import Inches
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

def pdf_to_docx(pdf_path, docx_path):
    """Pure Python PDF → DOCX - Perfect text extraction"""
    doc = Document()
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract text (preserves layout)
            text = page.extract_text()
            if text:
                p = doc.add_paragraph(text)
                p.paragraph_format.space_after = Inches(0.1)
            
            # Extract tables
            tables = page.extract_tables()
            for table in tables or []:
                if table and len(table) > 1:
                    rows, cols = len(table), len(table[0])
                    t = doc.add_table(rows=rows, cols=cols)
                    for i, row in enumerate(table):
                        for j, cell in enumerate(row):
                            t.rows[i].cells[j].text = str(cell or '')
    
    doc.save(docx_path)

@app.route('/')
def home():
    return jsonify({'status': 'Pure Python PDF → Word ✅'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        file = request.files.get('file')
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Upload PDF'}), 400

        unique_id = str(uuid.uuid4())[:8]
        filename = f"{unique_id}_{secure_filename(file.filename)}"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)

        docx_path = pdf_path.replace('.pdf', '.docx')
        pdf_to_docx(pdf_path, docx_path)

        os.remove(pdf_path)

        return jsonify({
            'success': True,
            'download_url': f'/api/download/{os.path.basename(docx_path)}',
            'size': os.path.getsize(docx_path)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER,
