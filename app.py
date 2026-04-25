from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import pdf2docx
from pdf2docx import Converter
import uuid
import shutil

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

# ROOT ENDPOINT - Test this first!
@app.route('/')
def home():
    return jsonify({
        'message': '🚀 PDF to Word API is LIVE!',
        'version': '1.0.0',
        'endpoints': {
            'health': '/api/health',
            'convert': '/api/convert (POST)',
            'download': '/api/download/<filename>'
        },
        'status': 'ready'
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': 'ok'})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        print("📥 Received convert request")  # Debug log
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            print(f"📄 Processing: {file.filename}")  # Debug log
            
            # Unique filename
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{unique_id}_{secure_filename(file.filename)}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            print(f"💾 Saved PDF: {filepath}")  # Debug log
            
            # Convert to DOCX
            docx_path = filepath.replace('.pdf', '.docx')
            print("🔄 Starting conversion...")  # Debug log
            
            cv = Converter(filepath)
            cv.convert(docx_path, start=0, end=None)
            cv.close()
            
            # Clean up PDF
            os.remove(filepath)
            
            print(f"✅ Converted to: {docx_path}")  # Debug log
            
            return jsonify({
                'success': True,
                'message': 'Conversion successful!',
                'download_url': f'/api/download/{os.path.basename(docx_path)}',
                'filename': os.path.basename(docx_path)
            })
        else:
            return jsonify({'error': 'Invalid file type. Only PDF allowed'}), 400
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")  # Debug log
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    try:
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True,
                           download_name=filename,
                           mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        return jsonify({'error': 'File not found or expired'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
