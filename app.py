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
from datetime import datetime

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

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("FFmpeg is not available!")
        return False

def safe_filename(filename):
    """Generate a safe filename that works on all platforms"""
    # Remove problematic characters
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
    return filename

@app.route('/')
def index():
    """Root route to display the main page"""
    try:
        if not check_ffmpeg():
            return render_template('index.html', error="FFmpeg is not available on the server")
            
        files = []
        if OUTPUT_FOLDER.exists():
            files = sorted([f.name for f in OUTPUT_FOLDER.iterdir() if f.is_file()])
        return render_template('index.html', files=files)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return render_template('index.html', error="Error loading page")

@app.route('/split', methods=['POST'])
def split_video():
    try:
        if not check_ffmpeg():
            return "FFmpeg is not available on the server", 500

        # Log request details
        logger.info(f"Split request received at {datetime.utcnow()}")
        logger.info(f"Files in request: {list(request.files.keys())}")
        logger.info(f"Form data: {list(request.form.keys())}")

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
            logger.error("No video file in request")
            return "No video file uploaded", 400
        
        video = request.files['video']
        if not video.filename:
            logger.error("No filename in video file")
            return "No video file selected", 400

        # Log file details
        logger.info(f"Uploaded file: {video.filename}")
        
        try:
            duration = int(request.form['duration'])
            if duration <= 0:
                return "Duration must be positive", 400
        except (KeyError, ValueError) as e:
            logger.error(f"Duration error: {e}")
            return "Invalid duration value", 400

        # Create a temporary file for upload
        temp_dir = Path(tempfile.gettempdir())
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        tmp_path = temp_dir / f"upload_{uuid.uuid4()}{Path(video.filename).suffix}"
        logger.info(f"Temporary file path: {tmp_path}")

        try:
            # Save upload in chunks
            with open(tmp_path, 'wb') as tmp_file:
                while True:
                    chunk = video.read(app.config['UPLOAD_CHUNK_SIZE'])
                    if not chunk:
                        break
                    tmp_file.write(chunk)
            
            # Process video
            original_name = safe_filename(Path(video.filename).stem)
            output_pattern = str(OUTPUT_FOLDER / f'part_%03d.mp4')
            
            cmd = [
                'ffmpeg', '-y',
                '-i', str(tmp_path),
                '-c', 'copy',
                '-map', '0',
                '-f', 'segment',
                '-segment_time', str(duration),
                '-reset_timestamps', '1',
                output_pattern
            ]

            logger.info(f"FFmpeg command: {' '.join(cmd)}")

            try:
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=240  # 4 minute timeout
                )
                process.check_returncode()
                logger.info("FFmpeg processing completed successfully")
            except subprocess.TimeoutExpired:
                logger.error("FFmpeg processing timeout")
                return "Video processing timeout", 504
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg error: {e.stderr}")
                return f"Error processing video: {e.stderr}", 500

        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            return "Error processing upload", 500
        finally:
            # Clean up temp file
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception as e:
                logger.error(f"Error cleaning up temp file: {e}")

        # Check for output files
        parts = sorted(OUTPUT_FOLDER.glob('part_*.mp4'))
        if not parts:
            logger.error("No output parts were created")
            return "No video parts were created", 500

        logger.info(f"Created {len(parts)} video parts")

        # Create zip file
        zip_filename = f"{original_name}_parts.zip"
        zip_path = OUTPUT_FOLDER / zip_filename
        
        try:
            with zipfile.ZipFile(str(zip_path), 'w') as zipf:
                for part in parts:
                    zipf.write(str(part), part.name)
            logger.info(f"Created zip file: {zip_filename}")
        except Exception as e:
            logger.error(f"Error creating zip: {e}")
            return "Error creating zip file", 500

        # Get final file list
        files = sorted([f.name for f in OUTPUT_FOLDER.iterdir() if f.is_file()])
        logger.info(f"Final files: {files}")
        return render_template('index.html', files=files)

    except Exception as e:
        logger.error(f"Error in split_video: {e}")
        return "An unexpected error occurred", 500

@app.route('/clear', methods=['POST'])
def clear_all():
    """Clear all uploaded and generated files"""
    try:
        logger.info("Clear request received")
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
        
        logger.info("Clear completed successfully")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error in clear_all: {e}")
        return jsonify({'success': False}), 500

@app.route('/output/<filename>')
def download_file(filename):
    """Download a processed file"""
    try:
        logger.info(f"Download request for: {filename}")
        file_path = OUTPUT_FOLDER / filename
        if not file_path.exists() or not file_path.is_file():
            logger.error(f"File not found: {filename}")
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
    # Check FFmpeg availability
    if not check_ffmpeg():
        logger.error("FFmpeg is not available! The application may not work correctly.")
    
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