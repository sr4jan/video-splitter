from flask import Flask, request, render_template, send_file, redirect, url_for, jsonify, session
import os
import uuid
import subprocess
import glob
import zipfile
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB limit
app.config['SECRET_KEY'] = os.urandom(24)

# Ensure absolute paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
OUTPUT_FOLDER = BASE_DIR / 'output'

# Create folders if they don't exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

def get_user_folder():
    """Get the output folder for the current user"""
    user_id = str(uuid.uuid4())
    user_folder = OUTPUT_FOLDER / user_id
    user_folder.mkdir(parents=True, exist_ok=True)
    return user_folder

def delete_files(directory):
    """Delete all files and subdirectories in the given directory"""
    try:
        # Convert to Path object if it's a string
        directory = Path(directory)
        
        # Check if directory exists
        if not directory.exists():
            return True
            
        # Delete all files and subdirectories
        for item in directory.iterdir():
            try:
                if item.is_file():
                    item.unlink(missing_ok=True)
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
            except Exception as e:
                logger.error(f"Error deleting {item}: {e}")
                return False
                
        return True
    except Exception as e:
        logger.error(f"Error in delete_files: {e}")
        return False

@app.route('/')
def index():
    try:
        files = []
        output_files = list(OUTPUT_FOLDER.glob('**/*.mp4')) + list(OUTPUT_FOLDER.glob('**/*.zip'))
        if output_files:
            files = [f.name for f in output_files]
        return render_template('index.html', files=sorted(files))
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return render_template('index.html', files=[])

@app.route('/split', methods=['POST'])
def split_video():
    try:
        # First clear any existing files
        delete_files(OUTPUT_FOLDER)
        delete_files(UPLOAD_FOLDER)

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

        # Save upload
        original_name = Path(video.filename).stem
        filename = f"{uuid.uuid4().hex}_{Path(video.filename).name.replace(' ', '_')}"
        video_path = UPLOAD_FOLDER / filename
        
        video.save(str(video_path))

        # Split using FFmpeg
        output_pattern = str(OUTPUT_FOLDER / 'part_%03d.mp4')
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
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
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            return "Error processing video", 500

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

        # Clean up upload
        try:
            video_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Error removing upload: {e}")

        # Get final file list
        files = []
        output_files = list(OUTPUT_FOLDER.glob('**/*.mp4')) + list(OUTPUT_FOLDER.glob('**/*.zip'))
        if output_files:
            files = [f.name for f in output_files]
        return render_template('index.html', files=sorted(files))

    except Exception as e:
        logger.error(f"Error in split_video: {e}")
        return "An unexpected error occurred", 500

@app.route('/clear', methods=['POST'])
def clear_all():
    try:
        logger.info("Starting clear_all operation")
        
        # Delete all files in output folder
        if not delete_files(OUTPUT_FOLDER):
            logger.error("Failed to clear output folder")
            return jsonify({'success': False}), 500
            
        # Delete all files in upload folder
        if not delete_files(UPLOAD_FOLDER):
            logger.error("Failed to clear upload folder")
            return jsonify({'success': False}), 500
            
        logger.info("Successfully cleared all folders")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error in clear_all: {e}")
        return jsonify({'success': False}), 500

@app.route('/output/<filename>')
def download_file(filename):
    try:
        # Look for the file in output folder and its subdirectories
        for file_path in OUTPUT_FOLDER.rglob(filename):
            if file_path.is_file():
                return send_file(str(file_path), as_attachment=True)
        return "File not found", 404
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return "Error downloading file", 500

if __name__ == '__main__':
    # Clear any leftover files on startup
    delete_files(UPLOAD_FOLDER)
    delete_files(OUTPUT_FOLDER)
    
    app.run(debug=True, host='0.0.0.0')