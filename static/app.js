document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const videoInput = document.getElementById('videoInput');
    const uploadForm = document.getElementById('uploadForm');
    const clearForm = document.getElementById('clearForm');
    const previewContainer = document.getElementById('previewContainer');
    const videoPreview = document.getElementById('videoPreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const videoDuration = document.getElementById('videoDuration');
    const splitButton = document.getElementById('splitButton');
    const clearButton = document.getElementById('clearButton');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const downloadsSection = document.querySelector('.downloads');  // Add this line

    // Drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('highlight');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('highlight');
        });
    });

    dropZone.addEventListener('drop', handleDrop);
    videoInput.addEventListener('change', handleFileSelect);
    
    // Update clear form handling
    clearForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        try {
            const response = await fetch('/clear', {
                method: 'POST',
            });
            
            if (!response.ok) {
                throw new Error('Clear request failed');
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Clear the form and UI
                uploadForm.reset();
                if (videoPreview.src) {
                    URL.revokeObjectURL(videoPreview.src);
                    videoPreview.src = '';
                }
                previewContainer.classList.add('hidden');
                splitButton.disabled = true;
                progressContainer.classList.add('hidden');
                progressBar.style.width = '0%';
                progressText.textContent = 'Processing: 0%';
                
                // Remove downloads section if it exists
                if (downloadsSection) {
                    downloadsSection.remove();
                }
                
                // Show success message
                const message = document.createElement('div');
                message.className = 'success-message';
                message.textContent = 'Files cleared successfully';
                document.querySelector('.app-main').appendChild(message);
                
                // Remove success message after 3 seconds
                setTimeout(() => {
                    message.remove();
                }, 3000);
            } else {
                throw new Error('Failed to clear files');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to clear files');
        }
    });

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        handleFile(file);
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        handleFile(file);
    }

    function handleFile(file) {
        if (file && file.type.startsWith('video/')) {
            // Update file info
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);

            // Create video preview
            const videoURL = URL.createObjectURL(file);
            videoPreview.src = videoURL;
            previewContainer.classList.remove('hidden');

            // Enable split button
            splitButton.disabled = false;

            // Get video duration
            videoPreview.addEventListener('loadedmetadata', () => {
                videoDuration.textContent = formatDuration(videoPreview.duration);
            });
        }
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        seconds = Math.floor(seconds % 60);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }

    // Handle form submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(uploadForm);
        splitButton.disabled = true;
        progressContainer.classList.remove('hidden');

        try {
            const response = await fetch('/split', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const html = await response.text();
            
            // Replace the entire page content
            document.documentElement.innerHTML = html;
            
            // Reinitialize the JavaScript since we replaced the entire page
            location.reload();
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while processing the video');
            splitButton.disabled = false;
        }
    });
});