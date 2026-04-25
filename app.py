from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return jsonify({'status': '🚀 PDF to Word API - Working!'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file'}), 400

        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())[:8]
        safe_name = f"{unique_id}_{filename}"
        pdf_path = os.path.join(UPLOAD_FOLDER, safe_name)
        file.save(pdf_path)

        # Simulate conversion (replace with real logic later)
        docx_path = pdf_path.replace('.pdf', '.docx')
        open(docx_path, 'w').write("High-quality DOCX content here\n")

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
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
