from flask import Flask, request, render_template, send_file, redirect, url_for, jsonify
import os
import uuid
import subprocess
import glob
import zipfile
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB limit

# Ensure absolute paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
OUTPUT_FOLDER = BASE_DIR / 'output'

# Create folders if they don't exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

def delete_directory_contents(directory):
    """Delete all files and subdirectories in the given directory."""
    directory = Path(directory)
    try:
        if directory.exists():
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        return True
    except Exception as e:
        logger.error(f"Error clearing directory {directory}: {e}")
        return False

@app.route('/')
def index():
    # Get list of files in output directory
    try:
        files = []
        if OUTPUT_FOLDER.exists():
            files = sorted([f.name for f in OUTPUT_FOLDER.iterdir() if f.is_file()])
        return render_template('index.html', files=files)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return render_template('index.html', files=[])

@app.route('/split', methods=['POST'])
def split_video():
    try:
        # Clear existing files first
        delete_directory_contents(UPLOAD_FOLDER)
        delete_directory_contents(OUTPUT_FOLDER)

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

        # Save upload with safe filename
        original_name = Path(video.filename).stem
        filename = f"{uuid.uuid4().hex}_{Path(video.filename).name.replace(' ', '_')}"
        video_path = UPLOAD_FOLDER / filename
        
        video.save(str(video_path))

        # Split using FFmpeg
        segment_pattern = str(OUTPUT_FOLDER / 'part_%03d.mp4')
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-c', 'copy',
            '-map', '0',
            '-f', 'segment',
            '-segment_time', str(duration),
            '-reset_timestamps', '1',
            segment_pattern
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
            video_path.unlink()
        except Exception as e:
            logger.error(f"Error removing upload: {e}")

        # Get final file list
        files = sorted([f.name for f in OUTPUT_FOLDER.iterdir() if f.is_file()])
        return render_template('index.html', files=files)

    except Exception as e:
        logger.error(f"Error in split_video: {e}")
        return "An unexpected error occurred", 500

@app.route('/clear', methods=['POST'])
def clear_all():
    try:
        # Clear both directories
        upload_success = delete_directory_contents(UPLOAD_FOLDER)
        output_success = delete_directory_contents(OUTPUT_FOLDER)

        if not (upload_success and output_success):
            return jsonify({'success': False}), 500

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error in clear_all: {e}")
        return jsonify({'success': False}), 500

@app.route('/output/<filename>')
def download_file(filename):
    try:
        file_path = OUTPUT_FOLDER / filename
        if not file_path.exists() or not file_path.is_file():
            return "File not found", 404
        return send_file(str(file_path), as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return "Error downloading file", 500

if __name__ == '__main__':
    # Clear any leftover files on startup
    delete_directory_contents(UPLOAD_FOLDER)
    delete_directory_contents(OUTPUT_FOLDER)
    
    app.run(debug=True, host='0.0.0.0')