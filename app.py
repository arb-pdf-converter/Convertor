from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
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

@app.route('/')
def home():
    return jsonify({
        'status': '🚀 High-Quality PDF to Word (pdf2docx Enhanced)',
        'quality': 'Professional text + images + tables'
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        file = request.files.get('file')
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Upload PDF only'}), 400

        unique_id = str(uuid.uuid4())[:8]
        filename = f"{unique_id}_{secure_filename(file.filename)}"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)

        logger.info(f"Converting {filename} ({os.path.getsize(pdf_path)} bytes)")

        docx_path = pdf_path.replace('.pdf', '.docx')

        # HIGH QUALITY pdf2docx settings
        cv = Converter(pdf_path)
        cv.convert(
            docx_path,
            start=0,
            end=None,
            extract_images=True,      # Keep images
            image_resolution=300,     # High DPI
            # Default preserves: tables, fonts, layout
        )
        cv.close()

        os.remove(pdf_path)

        logger.info(f"✅ {os.path.basename(docx_path)} created")

        return jsonify({
            'success': True,
            'quality': 'high',
            'download_url': f'/api/download/{os.path.basename(docx_path)}',
            'size': os.path.getsize(docx_path)
        })

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return jsonify({'error': 'File expired'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
