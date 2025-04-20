document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const designForm = document.getElementById('design-form');
    const logoUpload = document.getElementById('logo-upload');
    const logoFilename = document.getElementById('logo-filename');
    const logoPreviewArea = document.getElementById('logo-preview-area');
    const logoPreview = document.getElementById('logo-preview');

    // Background mode elements
    const bgOptionGenerate = document.getElementById('bg-option-generate');
    const bgOptionUpload = document.getElementById('bg-option-upload');
    const generateInputs = document.getElementById('generate-inputs');
    const uploadInputs = document.getElementById('upload-inputs');

    // Generation specific elements
    const promptInput = document.getElementById('prompt-input');
    const styleSelect = document.getElementById('style-select');

    // Upload specific elements
    const bgUpload = document.getElementById('bg-upload');
    const bgFilename = document.getElementById('bg-filename');
    const bgPreviewArea = document.getElementById('bg-preview-area');
    const bgPreview = document.getElementById('bg-preview');

    const logoPosition = document.getElementById('logo-position');
    const generateBtn = document.getElementById('generate-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorMessage = document.getElementById('error-message');
    const resultArea = document.getElementById('result-area');
    const resultImage = document.getElementById('result-image');

    let logoFile = null;
    let backgroundFile = null; // Variable to store uploaded background file

    // --- Event Listeners ---

    // Logo Upload Handling & Preview
    logoUpload.addEventListener('change', (event) => {
        logoFile = event.target.files[0];
        if (logoFile) {
            logoFilename.textContent = logoFile.name;
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

     // Background Upload Handling & Preview
     bgUpload.addEventListener('change', (event) => {
        backgroundFile = event.target.files[0];
        if (backgroundFile) {
            bgFilename.textContent = backgroundFile.name;
            const reader = new FileReader();
            reader.onload = (e) => {
                bgPreview.src = e.target.result;
                bgPreview.style.display = 'block';
            }
            reader.readAsDataURL(backgroundFile);
        } else {
            bgFilename.textContent = 'Фон не выбран...';
            bgPreview.style.display = 'none';
            bgPreview.src = '#';
            backgroundFile = null;
        }
    });

    // Radio Button Logic (Show/Hide relevant inputs & manage required attribute)
    function handleModeChange() {
        if (bgOptionGenerate.checked) {
            generateInputs.classList.remove('hidden');
            uploadInputs.classList.add('hidden');
            // Set required for generate mode
            promptInput.required = true;
            styleSelect.required = true;
            bgUpload.required = false; // Not required in generate mode
            // Clear upload fields if user switches back
            backgroundFile = null;
            bgUpload.value = ''; // Reset file input
            bgFilename.textContent = 'Фон не выбран...';
            bgPreview.style.display = 'none';
            bgPreview.src = '#';
        } else { // bgOptionUpload is checked
            generateInputs.classList.add('hidden');
            uploadInputs.classList.remove('hidden');
            // Set required for upload mode
            promptInput.required = false;
            styleSelect.required = false;
            bgUpload.required = true; // Required in upload mode
             // Clear generate fields if user switches
             // promptInput.value = ''; // Optional: clear prompt
             // styleSelect.value = ''; // Optional: reset style dropdown
        }
    }

    bgOptionGenerate.addEventListener('change', handleModeChange);
    bgOptionUpload.addEventListener('change', handleModeChange);


    // Form Submission Handler
    designForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        console.log("Form submitted");

        // 1. Reset UI States
        hideError();
        resultArea.classList.add('hidden');
        resultImage.src = "#";

        // 2. Basic Client-Side Validation
        if (!logoFile) {
            showError('Пожалуйста, загрузите логотип компании.');
            return;
        }
         if (!logoPosition.value) {
             showError('Пожалуйста, выберите позицию логотипа.');
             return;
        }

        const isGenerating = bgOptionGenerate.checked;
        const formData = new FormData();
        formData.append('logo', logoFile);
        formData.append('position', logoPosition.value);
        formData.append('mode', isGenerating ? 'generate' : 'upload');

        if (isGenerating) {
             if (!promptInput.value.trim()) {
                 showError('Пожалуйста, введите промпт для генерации.');
                 return;
             }
              if (!styleSelect.value) {
                 showError('Пожалуйста, выберите стиль генерации.');
                 return;
             }
             formData.append('prompt', promptInput.value.trim());
             formData.append('style', styleSelect.value);
        } else { // Uploading
             if (!backgroundFile) {
                showError('Пожалуйста, загрузите файл фона.');
                return;
             }
             formData.append('backgroundFile', backgroundFile); // Add background file
        }

        // 3. Show Loading Indicator
        showLoading(true);
        console.log("Sending data to backend...");

        // 4. Send data to Flask backend
        try {
            const response = await fetch('/generate-card', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                 const contentType = response.headers.get("content-type");
                 if (contentType && contentType.startsWith("image/")) {
                     const imageBlob = await response.blob();
                     const imageObjectURL = URL.createObjectURL(imageBlob);
                     resultImage.src = imageObjectURL;
                     resultArea.classList.remove('hidden');
                     resultArea.scrollIntoView({ behavior: 'smooth' });
                     console.log("Image received and displayed.");
                 } else {
                     const errorData = await response.json();
                     showError(errorData.error || 'Неизвестная ошибка от сервера.');
                     console.error("Server returned JSON error:", errorData);
                 }
            } else {
                let errorMsg = `Ошибка сервера: ${response.status} ${response.statusText}`;
                try {
                     const errorData = await response.json();
                     errorMsg = errorData.error || errorMsg;
                     console.error("Server returned error JSON:", errorData);
                } catch (e) { console.error("Server returned non-JSON error response."); }
                showError(errorMsg);
            }
        } catch (error) {
            console.error('Fetch error:', error);
            showError('Сетевая ошибка или ошибка при отправке запроса.');
        } finally {
            showLoading(false);
        }
    });

    // --- Helper Functions (showError, hideError, showLoading - remain the same) ---
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

    // Initial setup: Ensure correct fields are shown and required attributes are set
    handleModeChange();

}); // End DOMContentLoaded