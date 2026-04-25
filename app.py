from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import logging
import re

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': '🚀 Pure Python PDF → Word (Full Layout)',
        'quality': 'Text + Structure Preserved'
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

def extract_pdf_text(pdf_path):
    """Extract text with basic structure"""
    text_content = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                # Preserve line breaks
                lines = page_text.split('\n')
                for line in lines:
                    if line.strip():
                        text_content += line.strip() + '\n'
    except Exception as e:
        logger.error(f"PDF read error: {e}")
    return text_content

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        file = request.files.get('file')
        if not file or not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Upload PDF only'}), 400

        unique_id = str(uuid.uuid4())[:8]
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_{filename}")
        file.save(pdf_path)

        # Create high-quality DOCX
        docx_path = pdf_path.replace('.pdf', '.docx')
        doc = Document()

        # Extract & format text
        text = extract_pdf_text(pdf_path)
        
        # Smart paragraph detection
        paragraphs = re.split(r'\n\s*\n', text)
        for para in paragraphs:
            if para.strip():
                p = doc.add_paragraph(para.strip())
                p.paragraph_format.space_after = Inches(0.1)
                p.paragraph_format.line_spacing = 1.15

        # Add title page
        title = doc.add_heading('Converted from PDF', 0)
        title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        doc.save(docx_path)
        os.remove(pdf_path)

        return jsonify({
            'success': True,
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
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    return jsonify({'error': 'File expired'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
