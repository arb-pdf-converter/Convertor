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
    """Detect if PDF is text-heavy"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_chars = 0
            for page in pdf.pages[:3]:
                text = page.extract_text()
                if text:
                    total_chars += len(text)
            return total_chars > 1500
    except:
        return False

def perfect_text_extract(pdf_path, docx_path):
    """Perfect text extraction - FIXED version"""
    logger.info("✨ Perfect text extraction")
    
    doc = Document()
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract words for layout preservation
                words = page.extract_words()
                
                if words:
                    # Group by Y position (lines)
                    lines = {}
                    for word in words:
                        y_pos = round(word['top'], 1)
                        if y_pos not in lines:
                            lines[y_pos] = []
                        lines[y_pos].append(word['text'])
                    
                    # Create paragraphs
                    for y_pos in sorted(lines.keys()):
                        line_text = ' '.join(lines[y_pos])
                        if len(line_text.strip()) > 2:
                            p = doc.add_paragraph(line_text.strip())
                            p.paragraph_format.space_after = Inches(0.08)
                
                # Extract tables (NO 'simple=True')
                try:
                    tables = page.extract_tables()
                    for table_idx, table in enumerate(tables or []):
                        if table and len(table) > 1 and len(table[0]) > 1:
                            rows = len(table)
                            cols = max((len(r) for r in table), default=1)
                            t = doc.add_table(rows=rows, cols=cols)
                            
                            for i, row in enumerate(table):
                                for j, cell in enumerate(row or []):
                                    if i < len(t.rows) and j < len(t.rows[i].cells):
                                        t.rows[i].cells[j].text = str(cell).strip() if cell else ''
                except:
                    logger.info("No tables found or table extraction skipped")
    
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        # Fallback to pdf2docx
        cv = Converter(pdf_path)
        cv.convert(docx_path)
        cv.close()
        return
    
    doc.save(docx_path)
    logger.info("✅ Text extraction complete!")

@app.route('/')
def home():
    return jsonify({'status': '🚀 Perfect PDF to Word API ✅'})

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
            return jsonify({'error': 'Upload valid PDF'}), 400
        
        # Save file
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
            logger.info("Using pdf2docx")
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
            'download_url': f'/api/download/{os.path.basename(docx_path)}'
        })
        
    except Exception as e:
        logger.error(f"Conversion error: {e}")
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
