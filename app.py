import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from pathlib import Path
from flask_cors import CORS

# Import your PDFToPodcastConverter class
from pdf_podcast_converter import PDFToPodcastConverter

# --- Configuration ---
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('output')
ALLOWED_EXTENSIONS = {'pdf'}

# Ensure folders exist
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__)
# Enable CORS for communication with the Vercel frontend (allow all for deployment simplicity)
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


def allowed_file(filename):
    """Checks if the uploaded file is a PDF."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- API ENDPOINTS ---

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    """Handles PDF upload and conversion."""
    
    # 1. Check for file and required API Key
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file part in the request."}), 400
    
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({"error": "No selected file."}), 400
    
    if not os.getenv("GROQ_API_KEY"):
        return jsonify({"error": "GROQ_API_KEY not set. Cannot run script generation."}), 500

    if file and allowed_file(file.filename):
        pdf_path = None
        try:
            # 2. Securely save the uploaded PDF
            filename = secure_filename(file.filename)
            pdf_path = app.config['UPLOAD_FOLDER'] / filename
            file.save(pdf_path)

            # 3. Parse preferences from the frontend
            preferences_json = request.form.get('preferences', '{}')
            preferences = json.loads(preferences_json)

            # 4. Define unique output filename and path
            base_name = filename.rsplit('.', 1)[0]
            output_filename = f"{base_name}_{int(time.time())}.mp3"
            output_path = app.config['OUTPUT_FOLDER'] / output_filename
            
            # 5. Initialize and run the converter
            converter = PDFToPodcastConverter()
            
            print(f"Starting conversion for {filename} -> {output_filename}")
            
            result = converter.convert_pdf_to_podcast(
                pdf_path=str(pdf_path),
                output_path=str(output_path),
                preferences=preferences
            )

            # 6. Clean up the uploaded PDF immediately after conversion
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

            if result['output_path']:
                # 7. Success response to the frontend
                return jsonify({
                    "message": "Conversion successful",
                    "filename": output_filename,
                    "transcript": result['transcript']
                }), 200
            else:
                return jsonify({"error": "Podcast generation failed to produce an output file."}), 500

        except Exception as e:
            # General error handling and cleanup
            print(f"FATAL SERVER ERROR: {e}")
            
            # Ensure file cleanup happens even on error
            if pdf_path and os.path.exists(pdf_path):
                 os.remove(pdf_path)
            
            return jsonify({"error": f"Internal server processing failed: {str(e)}"}), 500

    return jsonify({"error": "Invalid file type or processing error."}), 400


@app.route('/api/download/<filename>', methods=['GET'])
def download_podcast(filename):
    """Serves the final MP3 file back to the frontend for playback and download."""
    
    # Use send_from_directory for secure file serving
    return send_from_directory(
        app.config['OUTPUT_FOLDER'], 
        filename, 
        as_attachment=False, 
        mimetype='audio/mpeg'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
