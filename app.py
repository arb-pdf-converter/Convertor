from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
import logging
import subprocess

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


def convert_with_libreoffice(pdf_path, output_dir):
    try:
        command = [
            "soffice",
            "--headless",
            "--convert-to", "docx",
            "--outdir", output_dir,
            "-env:UserInstallation=file:///tmp/LibreOffice_Conversion",
            os.path.abspath(pdf_path)
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )

        print("STDOUT:", result.stdout.decode())
        print("STDERR:", result.stderr.decode())

        if result.returncode != 0:
            logger.error("LibreOffice returned non-zero exit code")
            return None

        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        return os.path.join(output_dir, base_name + ".docx")

        except Exception as e:
            logger.error(f"LibreOffice exception: {e}")
            return None

        subprocess.run(command, check=True, timeout=60)

        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        return os.path.join(output_dir, base_name + ".docx")

    except subprocess.TimeoutExpired:
        logger.error("Conversion timed out")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"LibreOffice failed: {e}")
        return None


@app.route('/')
def home():
    return jsonify({'status': '🚀 PDF to Word API (LibreOffice) ✅'})


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

        # Convert using LibreOffice
        docx_path = convert_with_libreoffice(pdf_path, UPLOAD_FOLDER)

        if not docx_path or not os.path.exists(docx_path):
            return jsonify({'error': 'Conversion failed'}), 500

        # Remove original PDF
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        return jsonify({
            'success': True,
            'pdf_type': 'libreoffice',
            'download_url': f'/api/download/{os.path.basename(docx_path)}'
        })

    except Exception as e:
        logger.error(f"Conversion error: {e}")
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
