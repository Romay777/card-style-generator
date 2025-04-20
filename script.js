document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const designForm = document.getElementById('design-form');

    // Logo upload elements
    const logoDropzone = document.getElementById('logo-dropzone');
    const logoUpload = document.getElementById('logo-upload');
    const logoPreviewArea = document.getElementById('logo-preview-area');
    const logoPreview = document.getElementById('logo-preview');
    const removeLogo = document.getElementById('remove-logo');

    // Background elements
    const bgOption = document.getElementById('bg-option');
    const optionTabs = document.querySelectorAll('.option-tab');
    const generateInputs = document.getElementById('generate-inputs');
    const uploadInputs = document.getElementById('upload-inputs');

    // Background upload elements
    const bgDropzone = document.getElementById('bg-dropzone');
    const bgUpload = document.getElementById('bg-upload');
    const bgPreviewArea = document.getElementById('bg-preview-area');
    const bgPreview = document.getElementById('bg-preview');
    const removeBg = document.getElementById('remove-bg');

    // Logo position elements
    const logoPositionRadios = document.querySelectorAll('input[name="logo-position"]');
    const logoPositionPreview = document.getElementById('logo-position-preview');

    // Navigation and results elements
    const nextButtons = document.querySelectorAll('.next-btn');
    const backButtons = document.querySelectorAll('.back-btn');
    const progressSteps = document.querySelectorAll('.progress-step');
    const progressLines = document.querySelectorAll('.progress-line');

    const loadingIndicator = document.getElementById('loading-indicator');
    const errorMessage = document.getElementById('error-message');
    const resultArea = document.getElementById('result-area');
    const resultImage = document.getElementById('result-image');
    const downloadBtn = document.getElementById('download-btn');
    const restartBtn = document.getElementById('restart-btn');

    // State variables
    let logoFile = null;
    let backgroundFile = null;
    let currentSection = 1;

    // --- Event Listeners ---

    // Form navigation
    nextButtons.forEach(button => {
        button.addEventListener('click', () => {
            const nextSectionId = button.getAttribute('data-next');
            const nextSection = document.getElementById(nextSectionId);

            // Basic validation per section
            if (currentSection === 1 && !logoFile) {
                showError('Пожалуйста, загрузите логотип компании.');
                return;
            }

            if (currentSection === 2) {
                const isGenerating = bgOption.value === 'generate';
                if (isGenerating) {
                    const promptInput = document.getElementById('prompt-input');
                    if (!promptInput.value.trim()) {
                        showError('Пожалуйста, опишите желаемый фон.');
                        return;
                    }
                } else {
                    if (!backgroundFile) {
                        showError('Пожалуйста, загрузите фон карты.');
                        return;
                    }
                }
            }

            // Update UI for section change
            document.querySelector(`.form-section.active`).classList.remove('active');
            nextSection.classList.add('active');

            // Update progress indicators
            progressSteps[currentSection-1].classList.add('completed');
            if (currentSection < 3) {
                progressLines[currentSection-1].classList.add('active');
                progressSteps[currentSection].classList.add('active');
            }

            currentSection = parseInt(nextSectionId.split('-')[1]);
            hideError();

            // If going to section 3, update logo position preview
            if (currentSection === 3 && logoFile) {
                updateLogoPositionPreview();
            }
        });
    });

    backButtons.forEach(button => {
        button.addEventListener('click', () => {
            const prevSectionId = button.getAttribute('data-back');
            const prevSection = document.getElementById(prevSectionId);

            document.querySelector(`.form-section.active`).classList.remove('active');
            prevSection.classList.add('active');

            // Update progress indicators
            if (currentSection <= 3) {
                progressSteps[currentSection-1].classList.remove('active');
                progressLines[currentSection-2].classList.remove('active');
            }

            currentSection = parseInt(prevSectionId.split('-')[1]);
            hideError();
        });
    });

    // Logo upload handling
    logoDropzone.addEventListener('click', () => {
        logoUpload.click();
    });

    logoDropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        logoDropzone.classList.add('drag-over');
    });

    logoDropzone.addEventListener('dragleave', () => {
        logoDropzone.classList.remove('drag-over');
    });

    logoDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        logoDropzone.classList.remove('drag-over');

        if (e.dataTransfer.files.length) {
            logoUpload.files = e.dataTransfer.files;
            handleLogoUpload(e.dataTransfer.files[0]);
        }
    });

    logoUpload.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleLogoUpload(e.target.files[0]);
        }
    });

    removeLogo.addEventListener('click', () => {
        logoFile = null;
        logoUpload.value = '';
        logoPreviewArea.style.display = 'none';
        logoDropzone.style.display = 'block';
        logoPositionPreview.style.backgroundImage = 'none';
    });

    function handleLogoUpload(file) {
        // Check file type
        const validTypes = ['image/jpeg', 'image/png', 'image/svg+xml'];
        if (!validTypes.includes(file.type)) {
            showError('Пожалуйста, загрузите изображение в формате PNG, JPG или SVG.');
            return;
        }

        // Check file size (5MB max)
        if (file.size > 5 * 1024 * 1024) {
            showError('Размер файла не должен превышать 5MB.');
            return;
        }

        logoFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            logoPreview.src = e.target.result;
            logoPreviewArea.style.display = 'block';
            logoDropzone.style.display = 'none';

            // Update logo in position preview if we're on that section
            if (currentSection === 3) {
                updateLogoPositionPreview();
            }
        };
        reader.readAsDataURL(file);
        hideError();
    }

    // Background option tabs
    optionTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Update active tab
            document.querySelector('.option-tab.active').classList.remove('active');
            tab.classList.add('active');

            // Show corresponding inputs
            const targetId = tab.getAttribute('data-target');
            document.querySelector('.tab-content.active').classList.remove('active');
            document.getElementById(targetId).classList.add('active');

            // Update hidden input value
            bgOption.value = targetId === 'generate-inputs' ? 'generate' : 'upload';
        });
    });

    // Background upload handling
    bgDropzone.addEventListener('click', () => {
        bgUpload.click();
    });

    bgDropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        bgDropzone.classList.add('drag-over');
    });

    bgDropzone.addEventListener('dragleave', () => {
        bgDropzone.classList.remove('drag-over');
    });

    bgDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        bgDropzone.classList.remove('drag-over');

        if (e.dataTransfer.files.length) {
            bgUpload.files = e.dataTransfer.files;
            handleBgUpload(e.dataTransfer.files[0]);
        }
    });

    bgUpload.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleBgUpload(e.target.files[0]);
        }
    });

    removeBg.addEventListener('click', () => {
        backgroundFile = null;
        bgUpload.value = '';
        bgPreviewArea.style.display = 'none';
        bgDropzone.style.display = 'block';
    });

    function handleBgUpload(file) {
        // Check file type
        const validTypes = ['image/jpeg', 'image/png'];
        if (!validTypes.includes(file.type)) {
            showError('Пожалуйста, загрузите изображение в формате PNG или JPG.');
            return;
        }

        // Check file size (5MB max)
        if (file.size > 5 * 1024 * 1024) {
            showError('Размер файла не должен превышать 5MB.');
            return;
        }

        backgroundFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            bgPreview.src = e.target.result;
            bgPreviewArea.style.display = 'block';
            bgDropzone.style.display = 'none';
        };
        reader.readAsDataURL(file);
        hideError();
    }

    // Logo position handling
    logoPositionRadios.forEach(radio => {
        radio.addEventListener('change', updateLogoPositionPreview);
    });

    function updateLogoPositionPreview() {
        if (!logoFile) return;

        const selectedPosition = document.querySelector('input[name="logo-position"]:checked').value;

        // Первая настраиваем лого - делаем его видимым и устанавливаем фоновое изображение
        logoPositionPreview.style.display = 'block';
        logoPositionPreview.style.backgroundImage = `url(${logoPreview.src})`;
        logoPositionPreview.style.backgroundSize = 'contain';
        logoPositionPreview.style.backgroundRepeat = 'no-repeat';
        logoPositionPreview.style.width = '60px';
        logoPositionPreview.style.height = '60px';
        logoPositionPreview.style.position = 'absolute';

        // Позиционируем лого согласно выбранной позиции
        switch(selectedPosition) {
            case 'top-left':
                logoPositionPreview.style.top = '20px';
                logoPositionPreview.style.left = '20px';
                logoPositionPreview.style.right = 'auto';
                logoPositionPreview.style.bottom = 'auto';
                logoPositionPreview.style.transform = 'none';
                break;
            case 'top-right':
                logoPositionPreview.style.top = '20px';
                logoPositionPreview.style.right = '20px';
                logoPositionPreview.style.left = 'auto';
                logoPositionPreview.style.bottom = 'auto';
                logoPositionPreview.style.transform = 'none';
                break;
            case 'center':
                logoPositionPreview.style.top = '50%';
                logoPositionPreview.style.left = '50%';
                logoPositionPreview.style.right = 'auto';
                logoPositionPreview.style.bottom = 'auto';
                logoPositionPreview.style.transform = 'translate(-50%, -50%)';
                break;
            case 'bottom-left':
                logoPositionPreview.style.bottom = '20px';
                logoPositionPreview.style.left = '20px';
                logoPositionPreview.style.top = 'auto';
                logoPositionPreview.style.right = 'auto';
                logoPositionPreview.style.transform = 'none';
                break;
            case 'bottom-right':
                logoPositionPreview.style.bottom = '20px';
                logoPositionPreview.style.right = '20px';
                logoPositionPreview.style.top = 'auto';
                logoPositionPreview.style.left = 'auto';
                logoPositionPreview.style.transform = 'none';
                break;
        }
    }

    // Form submission
    designForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        // Reset UI states
        hideError();
        resultArea.classList.add('hidden');

        // Basic validation
        if (!logoFile) {
            showError('Пожалуйста, загрузите логотип компании.');
            return;
        }

        const logoPosition = document.querySelector('input[name="logo-position"]:checked').value;
        const isGenerating = bgOption.value === 'generate';

        const formData = new FormData();
        formData.append('logo', logoFile);
        formData.append('position', logoPosition);
        formData.append('mode', isGenerating ? 'generate' : 'upload');

        if (isGenerating) {
            const promptInput = document.getElementById('prompt-input');
            const styleValue = document.querySelector('input[name="style-select"]:checked').value;

            if (!promptInput.value.trim()) {
                showError('Пожалуйста, опишите желаемый фон.');
                return;
            }

            formData.append('prompt', promptInput.value.trim());
            formData.append('style', styleValue);
        } else {
            if (!backgroundFile) {
                showError('Пожалуйста, загрузите фон карты.');
                return;
            }
            formData.append('background', backgroundFile);
        }

        // Show loading indicator
        showLoading(true);

        // Send data to backend
        try {
            const response = await fetch('/generate-card', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.includes("image/")) {
                    const imageBlob = await response.blob();
                    const imageObjectURL = URL.createObjectURL(imageBlob);
                    resultImage.src = imageObjectURL;
                    resultArea.classList.remove('hidden');
                    resultArea.scrollIntoView({ behavior: 'smooth' });
                } else {
                    const errorData = await response.json();
                    showError(errorData.error || 'Неизвестная ошибка от сервера.');
                }
            } else {
                let errorMsg = `Ошибка сервера: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.error || errorMsg;
                } catch (e) {
                    console.error("Не удалось прочитать ответ сервера как JSON");
                }
                showError(errorMsg);
            }
        } catch (error) {
            console.error('Fetch error:', error);
            showError('Сетевая ошибка или ошибка при отправке запроса.');
        } finally {
            showLoading(false);
        }
    });

    // Download button functionality
    downloadBtn.addEventListener('click', () => {
        const link = document.createElement('a');
        link.href = resultImage.src;
        link.download = 'card-design.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    // Restart button functionality
    restartBtn.addEventListener('click', () => {
        // Reset form
        designForm.reset();

        // Reset file inputs
        logoFile = null;
        backgroundFile = null;
        logoUpload.value = '';
        bgUpload.value = '';

        // Reset previews
        logoPreviewArea.style.display = 'none';
        logoDropzone.style.display = 'block';
        bgPreviewArea.style.display = 'none';
        bgDropzone.style.display = 'block';

        // Reset sections
        document.querySelector('.form-section.active').classList.remove('active');
        document.getElementById('section-1').classList.add('active');

        // Reset progress indicators
        progressSteps.forEach((step, index) => {
            if (index === 0) {
                step.classList.add('active');
            } else {
                step.classList.remove('active');
                step.classList.remove('completed');
            }
        });

        progressLines.forEach(line => {
            line.classList.remove('active');
        });

        // Reset option tabs
        document.querySelector('.option-tab.active').classList.remove('active');
        document.querySelector('.option-tab[data-target="generate-inputs"]').classList.add('active');

        document.querySelector('.tab-content.active').classList.remove('active');
        generateInputs.classList.add('active');

        bgOption.value = 'generate';

        // Hide result
        resultArea.classList.add('hidden');

        // Reset current section
        currentSection = 1;

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // --- Helper Functions ---
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
        errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }

    function showLoading(isLoading) {
        if (isLoading) {
            loadingIndicator.classList.remove('hidden');
            document.getElementById('generate-btn').disabled = true;
        } else {
            loadingIndicator.classList.add('hidden');
            document.getElementById('generate-btn').disabled = false;
        }
    }

    // Initialize animation for progress bar
    const progressBarInner = document.querySelector('.progress-bar-inner');
    if (progressBarInner) {
        progressBarInner.style.width = '0%';
        let width = 0;
        const simulateProgress = () => {
            const interval = setInterval(() => {
                if (width >= 90) {
                    clearInterval(interval);
                } else {
                    width += 1;
                    progressBarInner.style.width = width + '%';
                }
            }, 50);
            return interval;
        };

        let progressInterval;
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class') {
                    const isHidden = loadingIndicator.classList.contains('hidden');
                    if (!isHidden) {
                        width = 0;
                        progressBarInner.style.width = '0%';
                        progressInterval = simulateProgress();
                    } else if (progressInterval) {
                        clearInterval(progressInterval);
                        width = 100;
                        progressBarInner.style.width = '100%';
                    }
                }
            });
        });

        observer.observe(loadingIndicator, { attributes: true });
    }
});