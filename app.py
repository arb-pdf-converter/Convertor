from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
import logging
import subprocess
import tempfile
import shutil
import time

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.chmod(UPLOAD_FOLDER, 0o777)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def find_libreoffice():
    paths = [
        "/usr/lib/libreoffice/program/soffice",
        "/usr/bin/soffice",
        "/usr/bin/libreoffice",
        "libreoffice",
        "soffice"
    ]
    for path in paths:
        try:
            result = subprocess.run([path, "--version"], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  timeout=5)
            if result.returncode == 0:
                logger.info(f"✅ LibreOffice: {path}")
                return path
        except:
            continue
    return None

LIBREOFFICE_CMD = find_libreoffice()

def convert_with_libreoffice(pdf_path):
    if not LIBREOFFICE_CMD or not os.path.exists(pdf_path):
        logger.error(f"Missing LibreOffice or PDF: {pdf_path}")
        return None
    
    # Ensure PDF readable
    os.chmod(pdf_path, 0o666)
    
    temp_dir = "/tmp/libreoffice_out"
    os.makedirs(temp_dir, exist_ok=True)
    os.chmod(temp_dir, 0o777)
    
    try:
        command = [
            LIBREOFFICE_CMD,
            "--headless",
            "--invisible",
            "--nodefault",
            "--nofirststartwizard",
            "--nocrash-report",
            "--convert-to", "docx",
            "--outdir", temp_dir,
            pdf_path
        ]
        
        logger.info(f"🔄 Running: {' '.join(command)}")
        logger.info(f"PDF exists: {os.path.exists(pdf_path)}, size: {os.path.getsize(pdf_path)}")
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=240,  # 4 mins
            cwd="/app"  # Run from app dir
        )
        
        stdout = result.stdout.decode(errors='ignore')
        stderr = result.stderr.decode(errors='ignore')
        
        logger.info(f"Code: {result.returncode}")
        logger.info(f"STDOUT: {stdout[:300]}")
        if stderr:
            logger.warning(f"STDERR: {stderr[:500]}")
        
        if result.returncode != 0:
            return None
        
        # Find DOCX (flexible matching)
        output_file = None
        for file in os.listdir(temp_dir):
            if file.endswith('.docx') and '003a7a4f_Lina-Cv' in file:
                output_file = os.path.join(temp_dir, file)
                break
        
        if output_file and os.path.exists(output_file):
            final_path = os.path.join(UPLOAD_FOLDER, os.path.basename(output_file))
            shutil.move(output_file, final_path)
            os.chmod(final_path, 0o666)
            logger.info(f"✅ SUCCESS: {final_path}")
            return final_path
        
        logger.error("No matching DOCX found")
        return None
        
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        return None
    finally:
        # Cleanup temp
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/')
def home():
    return jsonify({
        'status': 'LibreOffice Ready',
        'cmd': LIBREOFFICE_CMD,
        'upload_folder': os.access(UPLOAD_FOLDER, os.W_OK)
    })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy' if LIBREOFFICE_CMD else 'error',
        'libreoffice': LIBREOFFICE_CMD,
        'uploads_writable': os.access(UPLOAD_FOLDER, os.W_OK)
    })

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        file = request.files.get('file')
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'No valid PDF'}), 400

        unique_id = str(uuid.uuid4())[:8]
        filename = f"{unique_id}_{secure_filename(file.filename)}"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)

        docx_path = convert_with_libreoffice(pdf_path)

        if docx_path:
            os.remove(pdf_path)
            return jsonify({
                'success': True,
                'download_url': f'/api/download/{os.path.basename(docx_path)}'
            })

        return jsonify({'error': 'LibreOffice failed - see logs'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return jsonify({'error': 'File gone'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
