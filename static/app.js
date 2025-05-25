document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const videoInput = document.getElementById('videoInput');
    const splitButton = document.getElementById('splitButton');
    const clearButton = document.getElementById('clearButton');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const progressBar = document.getElementById('progressBar');
    
    // Detect mobile device
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    
    if (isMobile) {
        // Adjust file input for mobile
        videoInput.accept = "video/*;capture=camcorder";
        // Remove drag and drop for mobile
        document.getElementById('dropZone').classList.add('mobile');
    }

    // Handle file selection
    videoInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // Validate file size
            const maxSize = 200 * 1024 * 1024; // 200MB
            if (file.size > maxSize) {
                alert('File size must be less than 200MB');
                this.value = '';
                return;
            }
            
            // Enable split button
            splitButton.disabled = false;
            
            // Show file info
            document.getElementById('fileName').textContent = file.name;
            document.getElementById('fileSize').textContent = 
                (file.size / (1024 * 1024)).toFixed(2) + ' MB';
        }
    });

    // Handle form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Show loading state
        loadingIndicator.style.display = 'block';
        splitButton.disabled = true;
        
        // Submit form
        const formData = new FormData(this);
        
        fetch('/split', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(html => {
            // Replace page content with new HTML
            document.documentElement.innerHTML = html;
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error processing video. Please try again.');
        })
        .finally(() => {
            loadingIndicator.style.display = 'none';
            splitButton.disabled = false;
        });
    });

    // Handle clear button
    clearButton?.addEventListener('click', function(e) {
        e.preventDefault();
        
        fetch('/clear', {
            method: 'POST'
        })
        .then(response => {
            if (response.ok) {
                window.location.reload();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error clearing files');
        });
    });
});