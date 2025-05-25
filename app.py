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
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Use a strong secret key for sessions - in production, this should be an environment variable
app.config['SECRET_KEY'] = '871e96e707a36f5c468ed2df34c6d9c5'  # Generate a proper secret key
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB limit
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # Session expires after 1 hour

# Ensure absolute paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
OUTPUT_FOLDER = BASE_DIR / 'output'

# Create folders if they don't exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

def init_session():
    """Initialize session if not already done"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session.permanent = True
        logger.info(f"Created new session: {session['user_id']}")

def get_user_folder():
    """Get user-specific folder"""
    init_session()
    user_folder = OUTPUT_FOLDER / session['user_id']
    user_folder.mkdir(parents=True, exist_ok=True)
    return user_folder

def cleanup_old_sessions():
    """Clean up old session folders"""
    try:
        current_time = datetime.utcnow()
        for folder in OUTPUT_FOLDER.iterdir():
            if folder.is_dir():
                try:
                    # Check if folder name is a valid UUID
                    uuid.UUID(folder.name)
                    folder_time = datetime.fromtimestamp(folder.stat().st_mtime)
                    # Delete folders older than 1 hour
                    if current_time - folder_time > timedelta(hours=1):
                        shutil.rmtree(folder)
                        logger.info(f"Cleaned up old session folder: {folder}")
                except (ValueError, AttributeError):
                    continue
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")

def delete_folder_contents(folder):
    """Delete contents of a folder"""
    try:
        for item in folder.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                logger.error(f"Error deleting {item}: {e}")
        return True
    except Exception as e:
        logger.error(f"Error deleting folder contents: {e}")
        return False

@app.before_request
def before_request():
    """Run before each request"""
    init_session()
    cleanup_old_sessions()

@app.route('/')
def index():
    try:
        user_folder = get_user_folder()
        files = []
        if user_folder.exists():
            files = sorted([f.name for f in user_folder.iterdir() if f.is_file()])
        return render_template('index.html', files=files)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return render_template('index.html', files=[])

@app.route('/split', methods=['POST'])
def split_video():
    try:
        user_folder = get_user_folder()
        
        # Clear existing files for this user
        delete_folder_contents(user_folder)

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
        video_path = user_folder / filename
        
        video.save(str(video_path))

        # Split using FFmpeg
        output_pattern = str(user_folder / 'part_%03d.mp4')
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

        # Clean up original video
        try:
            video_path.unlink()
        except Exception as e:
            logger.error(f"Error removing upload: {e}")

        # Check for output files
        parts = sorted(user_folder.glob('part_*.mp4'))
        if not parts:
            return "No video parts were created", 500

        # Create zip file
        zip_filename = f"{original_name}_parts.zip"
        zip_path = user_folder / zip_filename
        
        try:
            with zipfile.ZipFile(str(zip_path), 'w') as zipf:
                for part in parts:
                    zipf.write(str(part), part.name)
        except Exception as e:
            logger.error(f"Error creating zip: {e}")
            return "Error creating zip file", 500

        # Get final file list
        files = sorted([f.name for f in user_folder.iterdir() if f.is_file()])
        return render_template('index.html', files=files)

    except Exception as e:
        logger.error(f"Error in split_video: {e}")
        return "An unexpected error occurred", 500

@app.route('/clear', methods=['POST'])
def clear_all():
    try:
        user_folder = get_user_folder()
        if not delete_folder_contents(user_folder):
            return jsonify({'success': False}), 500
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error in clear_all: {e}")
        return jsonify({'success': False}), 500

@app.route('/output/<filename>')
def download_file(filename):
    try:
        user_folder = get_user_folder()
        file_path = user_folder / filename
        
        # Security check: ensure file is in user's folder
        if not file_path.exists() or not file_path.is_file():
            return "File not found", 404
        
        try:
            file_path.relative_to(user_folder)
        except ValueError:
            return "Access denied", 403
            
        return send_file(str(file_path), as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return "Error downloading file", 500

if __name__ == '__main__':
    # Clean up all sessions on startup
    cleanup_old_sessions()
    
    app.run(debug=True, host='0.0.0.0')