from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pdf_podcast_converter import PDFToPodcastConverter
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Initialize converter
converter = PDFToPodcastConverter()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'NoteCast API is running'})

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        
        pdf_file = request.files['pdf']
        
        # Get user preferences
        preferences = {}
        if 'preferences' in request.form:
            try:
                preferences = json.loads(request.form['preferences'])
                print(f"User preferences: {preferences}")
            except json.JSONDecodeError:
                print("Could not parse preferences, using defaults")
                preferences = {}
        
        if pdf_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(pdf_file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        filename = secure_filename(pdf_file.filename)
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        pdf_file.save(pdf_path)
        
        output_filename = filename.replace('.pdf', '.mp3')
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        print(f"\n{'='*60}")
        print(f"Converting: {filename}")
        print(f"Output path: {output_path}")
        print(f"Preferences: {preferences}")
        print(f"{'='*60}\n")
        
        # Convert to podcast with preferences
        result = converter.convert_pdf_to_podcast(
            pdf_path=pdf_path,
            output_path=output_path,
            max_pages=3,
            preferences=preferences
        )
        
        # Get the actual output file
        actual_output = result['output_path']
        
        print(f"\n{'='*60}")
        print(f"Conversion complete!")
        print(f"Result path: {actual_output}")
        print(f"File exists: {os.path.exists(actual_output)}")
        
        if os.path.exists(actual_output):
            file_size = os.path.getsize(actual_output)
            print(f"File size: {file_size} bytes")
            
            # Copy to output folder with expected name if needed
            if actual_output != output_path:
                import shutil
                shutil.copy(actual_output, output_path)
                print(f"Copied to: {output_path}")
            
            actual_filename = os.path.basename(output_path)
        else:
            print(f"✗ File not found at: {actual_output}")
            print(f"Files in output folder: {os.listdir(OUTPUT_FOLDER)}")
            return jsonify({'error': 'Audio file not created'}), 500
        
        print(f"Returning filename: {actual_filename}")
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': True,
            'filename': actual_filename,
            'transcript': result['transcript']
        })
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR during conversion:")
        print(f"{str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_podcast(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, secure_filename(filename))
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, mimetype='audio/mpeg', as_attachment=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting NoteCast API Server...")
    print("📍 Server running on http://localhost:5000")
    print("📄 Upload endpoint: http://localhost:5000/api/convert")
    app.run(debug=True, port=5000, host='0.0.0.0')