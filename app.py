from flask import Flask, request, render_template, send_file, redirect, url_for
import os, uuid, subprocess, glob, zipfile, shutil
import logging
from time import sleep

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB limit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')

# Create folders if they don't exist
for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER):
    os.makedirs(folder, exist_ok=True)

def force_remove_file(path):
    """Helper function to forcefully remove a file with retries"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if os.path.isfile(path):
                os.unlink(path)  # Use unlink instead of remove
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            return True
        except (OSError, PermissionError) as e:
            if attempt < max_retries - 1:
                sleep(0.1)  # Short delay before retry
                continue
            logger.error(f"Failed to remove {path} after {max_retries} attempts: {e}")
            return False

def clean_folder(folder):
    """Helper function to clean a folder with proper error handling"""
    success = True
    if not os.path.exists(folder):
        return True
        
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if not force_remove_file(path):
            success = False
            
    return success

@app.route('/')
def index():
    files = []
    if os.path.exists(OUTPUT_FOLDER):
        files = sorted([f for f in os.listdir(OUTPUT_FOLDER) if os.path.isfile(os.path.join(OUTPUT_FOLDER, f))])
    return render_template('index.html', files=files)

@app.route('/split', methods=['POST'])
def split_video():
    try:
        # Clean up old files before processing
        for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER):
            clean_folder(folder)

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
        original_name = os.path.splitext(video.filename)[0]
        filename = f"{uuid.uuid4().hex}_{video.filename.replace(' ', '_')}"
        video_path = os.path.join(UPLOAD_FOLDER, filename)
        
        video.save(video_path)

        # Split using FFmpeg segment muxer
        segment_pattern = os.path.join(OUTPUT_FOLDER, 'part_%03d.mp4')
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-c', 'copy', '-map', '0',
            '-f', 'segment',
            '-segment_time', str(duration),
            '-reset_timestamps', '1',
            segment_pattern
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            # Clean up the uploaded file if FFmpeg fails
            force_remove_file(video_path)
            return "Error processing video", 500

        # Clean up the uploaded file after successful processing
        force_remove_file(video_path)

        # Check if any parts were created
        parts = sorted(glob.glob(os.path.join(OUTPUT_FOLDER, 'part_*.mp4')))
        if not parts:
            return "No video parts were created", 500

        # Zip all parts using original base name
        zip_filename = f"{original_name}_parts.zip"
        zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
        try:
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for part in parts:
                    zipf.write(part, os.path.basename(part))
        except (zipfile.BadZipFile, OSError) as e:
            logger.error(f"Error creating zip file: {str(e)}")
            return "Error creating zip file", 500

        # List files: individual parts + zip
        files = sorted([f for f in os.listdir(OUTPUT_FOLDER) if os.path.isfile(os.path.join(OUTPUT_FOLDER, f))])
        return render_template('index.html', files=files)

    except Exception as e:
        logger.error(f"Unexpected error in split_video: {str(e)}")
        return "An unexpected error occurred", 500

@app.route('/clear', methods=['POST'])
def clear_all():
    try:
        # First, close any open file handles
        import gc
        gc.collect()  # Force garbage collection to close any lingering file handles
        
        # Remove all uploads and outputs with retry mechanism
        success = True
        for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER):
            if not clean_folder(folder):
                success = False
                logger.error(f"Failed to clean folder: {folder}")
        
        if not success:
            return "Some files could not be cleared", 500
            
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in clear_all: {str(e)}")
        return "Error clearing files", 500

@app.route('/output/<filename>')
def download_file(filename):
    try:
        path = os.path.join(OUTPUT_FOLDER, filename)
        if not os.path.exists(path):
            return "File not found", 404
        if not os.path.isfile(path):
            return "Not a file", 400
        return send_file(path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {str(e)}")
        return "Error downloading file", 500

if __name__ == '__main__':
    # Clean up any leftover files on startup
    for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER):
        clean_folder(folder)
    
    app.run(debug=True, host='0.0.0.0')