# Video Splitter 📹

A Flask-based web application that allows users to split video files into smaller segments of equal duration. Try it live at [https://video-splitter-fbxx.onrender.com/](https://video-splitter-fbxx.onrender.com/)

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- 🎥 Split videos into equal duration segments
- 📦 Automatically zip all segments for easy download
- 🖥️ Modern, responsive web interface
- 🔄 Drag and drop file upload support
- 👀 Video preview before splitting
- 📊 Progress tracking during processing
- 🔒 Secure file handling
- 👤 Session-based user management
- 🔐 Private file access per session
- ⏲️ Automatic session cleanup

## Prerequisites

- Python 3.8 or higher
- FFmpeg installed on your system
- Modern web browser (Chrome, Firefox, Safari, Edge)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/sr4jan/video-splitter.git
cd video-splitter
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required Python packages:
```bash
pip install flask
```

4. Ensure FFmpeg is installed:
- **Linux**:
  ```bash
  sudo apt-get update
  sudo apt-get install ffmpeg
  ```
- **macOS**:
  ```bash
  brew install ffmpeg
  ```
- **Windows**:
  Download from [FFmpeg official website](https://ffmpeg.org/download.html)

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Using the application:
   - Drop a video file or click to select one
   - Set the desired duration for each segment (in seconds)
   - Click "Split Video" to process
   - Download individual parts or the complete ZIP file

## Configuration

The application has some configurable parameters in `app.py`:

- `MAX_CONTENT_LENGTH`: Maximum upload file size (default: 200MB)
- `UPLOAD_FOLDER`: Directory for temporary video storage
- `OUTPUT_FOLDER`: Directory for processed video segments

## Project Structure

```
modern-video-splitter/
├── app.py                 # Main Flask application
├── static/
│   ├── styles.css        # Main stylesheet
│   └── components.css    # Component-specific styles
├── templates/
│   └── index.html        # Main application template
├── uploads/              # Temporary upload storage
└── output/              # Processed video segments
```

## Technical Details

- Built with Flask web framework
- Uses FFmpeg for video processing
- Implements secure file handling
- Supports multiple video formats
- Client-side validation and preview
- AJAX-based clear functionality
- Progress tracking during processing

## Security Features

- Secure file handling with unique filenames
- Input validation for all parameters
- Protected against directory traversal
- Maximum file size limit
- Automatic cleanup of temporary files

## Limitations

- Maximum file size: 200MB
- Supported formats: Common video formats (MP4, AVI, MOV, etc.)
- Processing time depends on video size and system capabilities

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Created by Srajan Soni on 2025-05-25

## Acknowledgments

- FFmpeg for video processing capabilities
- Flask framework for web implementation
- Contributors and testers

---
Last updated: 2025-05-25 18:24:38 UTC