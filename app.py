from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
import logging
import subprocess
import tempfile

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

def convert_with_libreoffice(pdf_path):
    """Convert PDF to DOCX using LibreOffice - FIXED"""
    try:
        # Create temp output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            command = [
                "libreoffice",  # Changed from 'soffice'
                "--headless",
                "--convert-to", "docx",
                "--outdir", temp_dir,
                pdf_path
            ]
            
            logger.info(f"Running LibreOffice: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,  # 2 minutes timeout
                capture_output=True
            )
            
            logger.info(f"LibreOffice stdout: {result.stdout.decode()}")
            logger.info(f"LibreOffice stderr: {result.stderr.decode()}")
            
            if result.returncode != 0:
                logger.error(f"LibreOffice failed with code {result.returncode}")
                return None
            
            # Find output DOCX file
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.docx'):
                        docx_path = os.path.join(root, file)
                        # Move to uploads folder
                        final_path = os.path.join(UPLOAD_FOLDER, file)
                        os.rename(docx_path, final_path)
                        return final_path
            
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("LibreOffice conversion timed out")
        return None
    except Exception as e:
        logger.error(f"LibreOffice error: {str(e)}")
        return None

@app.route('/')
def home():
    return jsonify({'status': '🚀 LibreOffice PDF to Word API ✅'})

@app.route('/api/health')
def health():
    # Test LibreOffice
    try:
        result = subprocess.run(["libreoffice", "--version"], 
                              capture_output=True, timeout=10)
        version = result.stdout.decode().strip()
        return jsonify({'status': 'healthy', 'libreoffice': version})
    except:
        return jsonify({'status': 'error', 'libreoffice': 'not found'})

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file or file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Upload valid PDF'}), 400

        # Save uploaded PDF
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{unique_id}_{secure_filename(file.filename)}"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)

        logger.info(f"Starting conversion: {filename}")

        # Convert with LibreOffice
        docx_path = convert_with_libreoffice(pdf_path)

        if not docx_path or not os.path.exists(docx_path):
            return jsonify({'error': 'LibreOffice conversion failed'}), 500

        # Cleanup PDF
        os.remove(pdf_path)

        return jsonify({
            'success': True,
            'message': 'High-quality LibreOffice conversion complete!',
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
        return send_file(filepath, 
                        as_attachment=True,
                        download_name=filename,
                        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    return jsonify({'error': 'File expired'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
