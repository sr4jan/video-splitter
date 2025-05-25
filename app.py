from flask import Flask, request, render_template, send_file, redirect, url_for, jsonify
import os
import uuid
import subprocess
import glob
import zipfile
import shutil
import logging
from pathlib import Path
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 200 * 1024 * 1024))
app.config['UPLOAD_CHUNK_SIZE'] = 8 * 1024 * 1024  # 8MB chunks

# Ensure absolute paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = Path(os.getenv('UPLOAD_FOLDER', BASE_DIR / 'uploads'))
OUTPUT_FOLDER = Path(os.getenv('OUTPUT_FOLDER', BASE_DIR / 'output'))

# Create folders if they don't exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

def safe_filename(filename):
    """Generate a safe filename that works on all platforms"""
    # Remove problematic characters
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
    return filename

@app.route('/')
def index():
    """Root route to display the main page"""
    try:
        files = []
        if OUTPUT_FOLDER.exists():
            files = sorted([f.name for f in OUTPUT_FOLDER.iterdir() if f.is_file()])
        return render_template('index.html', files=files)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return "Error loading page", 500

@app.route('/split', methods=['POST'])
def split_video():
    try:
        # Clean up old files
        for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER):
            for item in Path(folder).glob('*'):
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")

        if 'video' not in request.files:
            return "No video file uploaded", 400
        
        video = request.files['video']
        if not video.filename:
            return "No video file selected", 400

        try:
            duration = int(request.form['duration'])
            if duration <= 0:
                return "Duration must be positive", 400
        except (KeyError, ValueError):
            return "Invalid duration value", 400

        # Create a temporary file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(video.filename).suffix) as tmp_file:
            # Save upload in chunks
            while True:
                chunk = video.read(app.config['UPLOAD_CHUNK_SIZE'])
                if not chunk:
                    break
                tmp_file.write(chunk)
            tmp_file.flush()
            
            # Process video
            original_name = safe_filename(Path(video.filename).stem)
            output_pattern = str(OUTPUT_FOLDER / f'part_%03d.mp4')
            
            cmd = [
                'ffmpeg', '-y',
                '-i', tmp_file.name,
                '-c', 'copy',
                '-map', '0',
                '-f', 'segment',
                '-segment_time', str(duration),
                '-reset_timestamps', '1',
                output_pattern
            ]

            try:
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=240  # 4 minute timeout
                )
                process.check_returncode()
            except subprocess.TimeoutExpired:
                return "Video processing timeout", 504
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg error: {e.stderr}")
                return "Error processing video", 500
            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_file.name)
                except:
                    pass

        # Check for output files
        parts = sorted(OUTPUT_FOLDER.glob('part_*.mp4'))
        if not parts:
            return "No video parts were created", 500

        # Create zip file
        zip_filename = f"{original_name}_parts.zip"
        zip_path = OUTPUT_FOLDER / zip_filename
        
        try:
            with zipfile.ZipFile(str(zip_path), 'w') as zipf:
                for part in parts:
                    zipf.write(str(part), part.name)
        except Exception as e:
            logger.error(f"Error creating zip: {e}")
            return "Error creating zip file", 500

        # Get final file list
        files = sorted([f.name for f in OUTPUT_FOLDER.iterdir() if f.is_file()])
        return render_template('index.html', files=files)

    except Exception as e:
        logger.error(f"Error in split_video: {e}")
        return "An unexpected error occurred", 500

@app.route('/clear', methods=['POST'])
def clear_all():
    """Clear all uploaded and generated files"""
    try:
        # Clean both directories
        for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER):
            for item in Path(folder).glob('*'):
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    logger.error(f"Error clearing {item}: {e}")
                    return jsonify({'success': False}), 500
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error in clear_all: {e}")
        return jsonify({'success': False}), 500

@app.route('/output/<filename>')
def download_file(filename):
    """Download a processed file"""
    try:
        file_path = OUTPUT_FOLDER / filename
        if not file_path.exists() or not file_path.is_file():
            return "File not found", 404
            
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error downloading {filename}: {e}")
        return "Error downloading file", 500

if __name__ == '__main__':
    # Clear any leftover files on startup
    for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER):
        for item in Path(folder).glob('*'):
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                logger.error(f"Startup cleanup error: {e}")
    
    app.run(debug=True, host='0.0.0.0')