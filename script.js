document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const designForm = document.getElementById('design-form');
    const logoUpload = document.getElementById('logo-upload');
    const logoFilename = document.getElementById('logo-filename');
    const logoPreviewArea = document.getElementById('logo-preview-area');
    const logoPreview = document.getElementById('logo-preview');

    const promptInput = document.getElementById('prompt-input');
    const styleSelect = document.getElementById('style-select'); // Get the style dropdown
    const logoPosition = document.getElementById('logo-position');

    const generateBtn = document.getElementById('generate-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorMessage = document.getElementById('error-message');
    const resultArea = document.getElementById('result-area');
    const resultImage = document.getElementById('result-image'); // Target for final image

    let logoFile = null;

    // --- Event Listeners ---

    // Logo Upload Handling & Preview
    logoUpload.addEventListener('change', (event) => {
        logoFile = event.target.files[0];
        if (logoFile) {
            logoFilename.textContent = logoFile.name;
            // Generate preview
            const reader = new FileReader();
            reader.onload = (e) => {
                logoPreview.src = e.target.result;
                logoPreview.style.display = 'block';
            }
            reader.readAsDataURL(logoFile);
        } else {
            logoFilename.textContent = 'Логотип не выбран...';
            logoPreview.style.display = 'none';
            logoPreview.src = '#';
            logoFile = null;
        }
    });

    // Form Submission Handler
    designForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default form submission
        console.log("Form submitted");

        // 1. Reset UI States
        hideError();
        resultArea.classList.add('hidden');
        resultImage.src = "#"; // Clear previous result image

        // 2. Basic Client-Side Validation (Server will also validate)
        if (!logoFile) {
            showError('Пожалуйста, загрузите логотип компании.');
            return;
        }
        if (!promptInput.value.trim()) {
             showError('Пожалуйста, введите промпт.');
             return;
        }
         if (!styleSelect.value) {
             showError('Пожалуйста, выберите стиль.');
             return;
        }
         if (!logoPosition.value) {
             showError('Пожалуйста, выберите позицию логотипа.');
             return;
        }


        // 3. Show Loading Indicator
        showLoading(true);

        // 4. Prepare data using FormData
        const formData = new FormData();
        formData.append('logo', logoFile);
        formData.append('prompt', promptInput.value.trim());
        formData.append('style', styleSelect.value);
        formData.append('position', logoPosition.value);

        console.log("Sending data to backend...");

        // 5. Send data to Flask backend
        try {
            const response = await fetch('/generate-card', { // Endpoint defined in Flask
                method: 'POST',
                body: formData
                // No 'Content-Type' header needed for FormData, browser sets it correctly
            });

            if (response.ok) {
                 // Check content type to see if we got an image or JSON error
                 const contentType = response.headers.get("content-type");
                 if (contentType && contentType.startsWith("image/")) {
                     // Got the image successfully
                     const imageBlob = await response.blob();
                     const imageObjectURL = URL.createObjectURL(imageBlob);
                     resultImage.src = imageObjectURL; // Display the final composited image
                     resultArea.classList.remove('hidden');
                     resultArea.scrollIntoView({ behavior: 'smooth' });
                     console.log("Image received and displayed.");
                 } else {
                     // Probably got a JSON error from the backend
                     const errorData = await response.json();
                     showError(errorData.error || 'Неизвестная ошибка от сервера.');
                     console.error("Server returned JSON error:", errorData);
                 }

            } else {
                // Handle HTTP errors (4xx, 5xx)
                let errorMsg = `Ошибка сервера: ${response.status} ${response.statusText}`;
                try {
                     const errorData = await response.json(); // Try to parse JSON error body
                     errorMsg = errorData.error || errorMsg; // Use specific error if available
                     console.error("Server returned error JSON:", errorData);
                } catch (e) {
                    // If response wasn't JSON
                    console.error("Server returned non-JSON error response.");
                }
                showError(errorMsg);
            }

        } catch (error) {
            // Handle network errors or other fetch issues
            console.error('Fetch error:', error);
            showError('Сетевая ошибка или ошибка при отправке запроса.');
        } finally {
            // 6. Hide Loading Indicator regardless of outcome
            showLoading(false);
        }
    });

    // --- Helper Functions ---
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
         errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function hideError() {
        errorMessage.classList.add('hidden');
        errorMessage.textContent = '';
    }

    function showLoading(isLoading) {
        if (isLoading) {
            loadingIndicator.classList.remove('hidden');
            generateBtn.disabled = true;
            generateBtn.style.opacity = '0.7';
            generateBtn.style.cursor = 'wait';
        } else {
            loadingIndicator.classList.add('hidden');
            generateBtn.disabled = false;
            generateBtn.style.opacity = '1';
             generateBtn.style.cursor = 'pointer';
        }
    }

    // REMOVED applyLogoPosition function

}); // End DOMContentLoaded