from flask import Flask, request, render_template, send_file, flash, redirect, url_for
import os
from werkzeug.utils import secure_filename
import pdf2docx
from pdf2docx import Converter
import zipfile
import io

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Convert PDF to DOCX
            docx_path = filepath.replace('.pdf', '.docx')
            try:
                cv = Converter(filepath)
                cv.convert(docx_path, start=0, end=None)
                cv.close()
                
                return send_file(docx_path, as_attachment=True, 
                               download_name=f"converted_{filename.replace('.pdf', '.docx')}")
            except Exception as e:
                flash(f'Conversion failed: {str(e)}')
                return redirect(url_for('index'))
        
        flash('Invalid file type. Please upload PDF files only.')
        return redirect(url_for('index'))
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
