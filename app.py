from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
import logging
import subprocess
import tempfile
import shutil

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

def test_libreoffice():
    """Find working LibreOffice command"""
    commands = ["libreoffice", "soffice"]
    for cmd in commands:
        try:
            result = subprocess.run([cmd, "--version"], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  timeout=10)
            if result.returncode == 0:
                logger.info(f"✅ LibreOffice: {cmd}")
                return cmd
        except:
            continue
    return None

LIBREOFFICE_CMD = test_libreoffice()

def convert_with_libreoffice(pdf_path):
    """FIXED: No capture_output conflict"""
    if not LIBREOFFICE_CMD:
        return None
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            command = [
                LIBREOFFICE_CMD,
                "--headless",
                "--invisible",
                "--nodefault",
                "--nofirststartwizard",
                "--convert-to", "docx",
                "--outdir", temp_dir,
                pdf_path
            ]
            
            logger.info(f"🔄 Command: {' '.join(command)}")
            
            # FIXED: Use stdout/stderr PIPE only (no capture_output)
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=180
            )
            
            stdout = result.stdout.decode('utf-8', errors='ignore')
            stderr = result.stderr.decode('utf-8', errors='ignore')
            
            logger.info(f"Return code: {result.returncode}")
            logger.info(f"STDOUT ({len(stdout)} chars): {stdout[:200]}...")
            if stderr:
                logger.warning(f"STDERR: {stderr}")
            
            if result.returncode != 0:
                logger.error(f"LibreOffice failed (code {result.returncode})")
                return None
            
            # Find and move DOCX
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.docx'):
                        src_path = os.path.join(root, file)
                        dst_path = os.path.join(UPLOAD_FOLDER, file)
                        shutil.move(src_path, dst_path)
                        logger.info(f"✅ DOCX: {dst_path} ({os.path.getsize(dst_path)} bytes)")
                        return dst_path
            
            logger.error("No DOCX output found")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("Timeout (3 mins)")
        return None
    except Exception as e:
        logger.error(f"Exception: {str(e)}")
        return None

@app.route('/')
def home():
    return jsonify({
        'status': '🚀 LibreOffice PDF → Word',
        'libreoffice': LIBREOFFICE_CMD or 'missing'
    })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy' if LIBREOFFICE_CMD else 'error',
        'command': LIBREOFFICE_CMD
    })

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400

        file = request.files['file']
        if not file or file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid PDF'}), 400

        unique_id = str(uuid.uuid4())[:8]
        filename = f"{unique_id}_{secure_filename(file.filename)}"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)

        logger.info(f"📥 PDF: {filename} ({os.path.getsize(pdf_path)} bytes)")

        docx_path = convert_with_libreoffice(pdf_path)

        if not docx_path or not os.path.exists(docx_path):
            return jsonify({'error': 'Conversion failed - check logs'}), 500

        os.remove(pdf_path)
        
        return jsonify({
            'success': True,
            'download_url': f'/api/download/{os.path.basename(docx_path)}',
            'filename': os.path.basename(docx_path),
            'size': os.path.getsize(docx_path)
        })

    except Exception as e:
        logger.error(f"API error: {str(e)}")
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
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
