document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements Cache ---
    const elements = {
        form: document.getElementById('design-form'),
        logo: {
            dropzone: document.getElementById('logo-dropzone'),
            upload: document.getElementById('logo-upload'),
            previewArea: document.getElementById('logo-preview-area'),
            preview: document.getElementById('logo-preview'),
            remove: document.getElementById('remove-logo'),
            positionPreview: document.getElementById('logo-position-preview'),
            sizeSlider: document.getElementById('logo-size-slider'),
            sizeValue: document.getElementById('logo-size-value')
        },
        bg: {
            option: document.getElementById('bg-option'),
            tabs: document.querySelectorAll('.option-tab'),
            generateInputs: document.getElementById('generate-inputs'),
            uploadInputs: document.getElementById('upload-inputs'),
            dropzone: document.getElementById('bg-dropzone'),
            upload: document.getElementById('bg-upload'),
            previewArea: document.getElementById('bg-preview-area'),
            preview: document.getElementById('bg-preview'),
            remove: document.getElementById('remove-bg'),
        },
        interactivePreview: document.getElementById('interactive-card-preview'),
        navigation: {
            nextButtons: document.querySelectorAll('.next-btn'),
            backButtons: document.querySelectorAll('.back-btn'),
            progressSteps: document.querySelectorAll('.progress-step'),
            progressLines: document.querySelectorAll('.progress-line')
        },
        results: {
            loading: document.getElementById('loading-indicator'),
            error: document.getElementById('error-message'),
            area: document.getElementById('result-area'),
            image: document.getElementById('result-image'),
            download: document.getElementById('download-btn'),
            restart: document.getElementById('restart-btn')
        },
        prompt: {
            input: document.getElementById('prompt-input'),
            improve: document.getElementById('improve-prompt-btn')
        }
    };

    // --- State ---
    const state = {
        logoFile: null,
        backgroundFile: null,
        currentSection: 1,
        logoPosition: {
            x: 50, // Position percentage (0-100)
            y: 50, // Position percentage (0-100)
            scale: 0.5, // Scale (matches slider initial value / 100)
            baseWidth: 100, // Default width in px for scaling reference
            baseHeight: 0, // Will be calculated based on aspect ratio
        },
        dragInfo: {
            isDragging: false,
            mouseOffsetX: 0,
            mouseOffsetY: 0
        }
    };

    // --- Event Handlers ---
    function initEventListeners() {
        // Form navigation
        elements.navigation.nextButtons.forEach(btn => {
            btn.addEventListener('click', handleNavigation);
        });

        elements.navigation.backButtons.forEach(btn => {
            btn.addEventListener('click', handleBackNavigation);
        });

        // Logo upload handling
        initDropZone(elements.logo.dropzone, elements.logo.upload, handleLogoUpload);
        elements.logo.upload.addEventListener('change', (e) => {
            if (e.target.files.length) handleLogoUpload(e.target.files[0]);
        });
        elements.logo.remove.addEventListener('click', removeLogo);

        // Background option tabs
        elements.bg.tabs.forEach(tab => {
            tab.addEventListener('click', handleTabSwitch);
        });

        // Background upload handling
        initDropZone(elements.bg.dropzone, elements.bg.upload, handleBgUpload);
        elements.bg.upload.addEventListener('change', (e) => {
            if (e.target.files.length) handleBgUpload(e.target.files[0]);
        });
        elements.bg.remove.addEventListener('click', removeBg);

        // Logo positioning
        initLogoPositioning();

        // Logo resizing
        elements.logo.sizeSlider.addEventListener('input', handleLogoResize);

        // Form submission
        elements.form.addEventListener('submit', handleFormSubmit);

        // Results actions
        elements.results.download.addEventListener('click', downloadResult);
        elements.results.restart.addEventListener('click', restartProcess);

        // Prompt improvement
        if (elements.prompt.improve && elements.prompt.input) {
            elements.prompt.improve.addEventListener('click', improvePrompt);
        }

        // Initialize progress bar animation
        initProgressBarAnimation();
    }

    // --- Navigation Functions ---
    function handleNavigation(e) {
        const nextSectionId = e.currentTarget.getAttribute('data-next');
        const nextSection = document.getElementById(nextSectionId);

        // Validate current section
        if (!validateSection(state.currentSection)) return;

        // Update UI for section change
        updateSectionUI(nextSection);

        // Update progress indicators
        updateProgressIndicators(state.currentSection, true);

        state.currentSection = parseInt(nextSectionId.split('-')[1]);
        hideError();

        // Initialize logo positioning if entering section 3
        if (state.currentSection === 3 && state.logoFile) {
            initializeLogoPositionAndScale();
        }
    }

    function handleBackNavigation(e) {
        const prevSectionId = e.currentTarget.getAttribute('data-back');
        const prevSection = document.getElementById(prevSectionId);

        // Update UI
        updateSectionUI(prevSection);
        updateProgressIndicators(state.currentSection, false);

        state.currentSection = parseInt(prevSectionId.split('-')[1]);
        hideError();
    }

    function updateSectionUI(targetSection) {
        document.querySelector('.form-section.active').classList.remove('active');
        targetSection.classList.add('active');
    }

    function updateProgressIndicators(currentSection, isForward) {
        if (isForward) {
            elements.navigation.progressSteps[currentSection-1].classList.add('completed');
            if (currentSection < 3) {
                elements.navigation.progressLines[currentSection-1].classList.add('active');
                elements.navigation.progressSteps[currentSection].classList.add('active');
            }
        } else {
            if (currentSection <= 3) {
                elements.navigation.progressSteps[currentSection-1].classList.remove('active');
                elements.navigation.progressLines[currentSection-2].classList.remove('active');
            }
        }
    }

    function validateSection(section) {
        if (section === 1 && !state.logoFile) {
            showError('Пожалуйста, загрузите логотип компании.');
            return false;
        }

        if (section === 2) {
            const isGenerating = elements.bg.option.value === 'generate';
            if (isGenerating) {
                if (!elements.prompt.input.value.trim()) {
                    showError('Пожалуйста, опишите желаемый фон.');
                    return false;
                }
            } else if (!state.backgroundFile) {
                showError('Пожалуйста, загрузите фон карты.');
                return false;
            }
        }
        return true;
    }

    // --- File Upload Functions ---
    function initDropZone(dropzone, fileInput, handleFn) {
        dropzone.addEventListener('click', () => fileInput.click());

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('drag-over');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('drag-over');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('drag-over');

            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                handleFn(e.dataTransfer.files[0]);
            }
        });
    }

    function handleLogoUpload(file) {
        if (!validateFile(file, ['image/jpeg', 'image/png', 'image/svg+xml'], 'Пожалуйста, загрузите изображение в формате PNG, JPG или SVG.')) return;

        state.logoFile = file;
        const reader = new FileReader();

        reader.onload = (e) => {
            const imgSrc = e.target.result;
            elements.logo.preview.src = imgSrc;
            elements.logo.positionPreview.style.backgroundImage = `url(${imgSrc})`;
            elements.logo.positionPreview.style.display = 'block';

            // Calculate base dimensions for scaling
            calculateLogoBaseDimensions(imgSrc);

            elements.logo.previewArea.style.display = 'block';
            elements.logo.dropzone.style.display = 'none';
        };

        reader.readAsDataURL(file);
        hideError();
    }

    function handleBgUpload(file) {
        if (!validateFile(file, ['image/jpeg', 'image/png'], 'Пожалуйста, загрузите изображение в формате PNG или JPG.')) return;

        state.backgroundFile = file;
        const reader = new FileReader();

        reader.onload = (e) => {
            elements.bg.preview.src = e.target.result;
            elements.bg.previewArea.style.display = 'block';
            elements.bg.dropzone.style.display = 'none';
        };

        reader.readAsDataURL(file);
        hideError();
    }

    function validateFile(file, validTypes, errorMsg) {
        if (!validTypes.includes(file.type)) {
            showError(errorMsg);
            return false;
        }

        // Check file size (5MB max)
        if (file.size > 5 * 1024 * 1024) {
            showError('Размер файла не должен превышать 5MB.');
            return false;
        }

        return true;
    }

    function calculateLogoBaseDimensions(imgSrc) {
        const img = new Image();
        img.onload = () => {
            const previewContainerWidth = elements.interactivePreview.clientWidth;
            // Set base size relative to container, e.g., 25% width initially
            state.logoPosition.baseWidth = previewContainerWidth * 0.25;
            const aspectRatio = img.naturalHeight / img.naturalWidth;
            state.logoPosition.baseHeight = state.logoPosition.baseWidth * aspectRatio;

            elements.logo.positionPreview.style.width = `${state.logoPosition.baseWidth}px`;
            elements.logo.positionPreview.style.height = `${state.logoPosition.baseHeight}px`;

            // If we are already on section 3, initialize position
            if (state.currentSection === 3) {
                initializeLogoPositionAndScale();
            }
        };
        img.src = imgSrc;
    }

    function removeLogo() {
        state.logoFile = null;
        elements.logo.upload.value = '';
        elements.logo.previewArea.style.display = 'none';
        elements.logo.dropzone.style.display = 'block';
        elements.logo.positionPreview.style.backgroundImage = 'none';
        elements.logo.positionPreview.style.display = 'none';

        // Reset state
        state.logoPosition.x = 50;
        state.logoPosition.y = 50;
        state.logoPosition.scale = 0.5;
        elements.logo.sizeSlider.value = 50;
        elements.logo.sizeValue.textContent = '50%';
    }

    function removeBg() {
        state.backgroundFile = null;
        elements.bg.upload.value = '';
        elements.bg.previewArea.style.display = 'none';
        elements.bg.dropzone.style.display = 'block';
    }

    function handleTabSwitch() {
        // Update active tab
        document.querySelector('.option-tab.active').classList.remove('active');
        this.classList.add('active');

        // Show corresponding inputs
        const targetId = this.getAttribute('data-target');
        document.querySelector('.tab-content.active').classList.remove('active');
        document.getElementById(targetId).classList.add('active');

        // Update hidden input value
        elements.bg.option.value = targetId === 'generate-inputs' ? 'generate' : 'upload';
    }

    // --- Logo Positioning Functions ---
    function initLogoPositioning() {
        elements.logo.positionPreview.addEventListener('mousedown', startDrag);
        document.addEventListener('mousemove', dragLogo);
        document.addEventListener('mouseup', endDrag);
    }

    function startDrag(e) {
        if (!state.logoFile || state.dragInfo.isDragging) return;
        e.preventDefault(); // Prevent text selection/image dragging

        const containerWidth = elements.interactivePreview.clientWidth;
        const containerHeight = elements.interactivePreview.clientHeight;
        const currentScale = state.logoPosition.scale;
        const currentWidth = state.logoPosition.baseWidth * currentScale;
        const currentHeight = state.logoPosition.baseHeight * currentScale;

        // Calculate top-left pixel position FROM the CENTER percentage state
        const currentLeftPx = (state.logoPosition.x / 100 * containerWidth) - (currentWidth / 2);
        const currentTopPx = (state.logoPosition.y / 100 * containerHeight) - (currentHeight / 2);

        // Calculate the offset of the mouse relative to the container
        const containerRect = elements.interactivePreview.getBoundingClientRect();
        const mouseXInContainer = e.clientX - containerRect.left;
        const mouseYInContainer = e.clientY - containerRect.top;

        state.dragInfo.mouseOffsetX = mouseXInContainer - currentLeftPx;
        state.dragInfo.mouseOffsetY = mouseYInContainer - currentTopPx;
        state.dragInfo.isDragging = true;
        elements.logo.positionPreview.classList.add('dragging');
    }

    function dragLogo(e) {
        if (!state.dragInfo.isDragging) return;
        e.preventDefault();

        // Calculate the new target position
        const containerRect = elements.interactivePreview.getBoundingClientRect();
        const mouseXInContainer = e.clientX - containerRect.left;
        const mouseYInContainer = e.clientY - containerRect.top;

        let newTargetLeftPx = mouseXInContainer - state.dragInfo.mouseOffsetX;
        let newTargetTopPx = mouseYInContainer - state.dragInfo.mouseOffsetY;

        // Get container dimensions
        const containerWidth = elements.interactivePreview.clientWidth;
        const containerHeight = elements.interactivePreview.clientHeight;

        // Calculate actual rendered dimensions
        const currentScale = state.logoPosition.scale;
        const currentWidth = state.logoPosition.baseWidth * currentScale;
        const currentHeight = state.logoPosition.baseHeight * currentScale;

        // Boundary checks
        if (newTargetLeftPx < 0) newTargetLeftPx = 0;
        if (containerWidth > 0 && newTargetLeftPx + currentWidth > containerWidth) {
            newTargetLeftPx = containerWidth - currentWidth;
        }

        if (newTargetTopPx < 0) newTargetTopPx = 0;
        if (containerHeight > 0 && newTargetTopPx + currentHeight > containerHeight) {
            newTargetTopPx = containerHeight - currentHeight;
        }

        // Update state (center percentage)
        state.logoPosition.x = containerWidth > 0 ? (newTargetLeftPx + currentWidth / 2) / containerWidth * 100 : 50;
        state.logoPosition.y = containerHeight > 0 ? (newTargetTopPx + currentHeight / 2) / containerHeight * 100 : 50;

        // Update UI
        updateLogoTransform();
    }

    function endDrag() {
        if (state.dragInfo.isDragging) {
            state.dragInfo.isDragging = false;
            elements.logo.positionPreview.classList.remove('dragging');
        }
    }

    function handleLogoResize() {
        const sliderValue = parseInt(elements.logo.sizeSlider.value);
        state.logoPosition.scale = sliderValue / 100;
        elements.logo.sizeValue.textContent = `${sliderValue}%`;
        updateLogoTransform();

        // Re-check boundaries after scaling
        checkAndAdjustBounds();
    }

    function updateLogoTransform() {
        if (!state.logoFile) return;

        const containerWidth = elements.interactivePreview.clientWidth;
        const containerHeight = elements.interactivePreview.clientHeight;

        // Calculate dimensions based on base size and current scale
        const currentWidth = state.logoPosition.baseWidth * state.logoPosition.scale;
        const currentHeight = state.logoPosition.baseHeight * state.logoPosition.scale;

        // Calculate top-left position from center percentage
        const targetLeft = (state.logoPosition.x / 100 * containerWidth) - (currentWidth / 2);
        const targetTop = (state.logoPosition.y / 100 * containerHeight) - (currentHeight / 2);

        // Apply styles
        elements.logo.positionPreview.style.width = `${currentWidth}px`;
        elements.logo.positionPreview.style.height = `${currentHeight}px`;
        elements.logo.positionPreview.style.left = `${targetLeft}px`;
        elements.logo.positionPreview.style.top = `${targetTop}px`;
        elements.logo.positionPreview.style.transform = 'none';
        elements.logo.positionPreview.style.display = 'block';
    }

    function checkAndAdjustBounds() {
        if (!state.logoFile || !elements.interactivePreview) return;

        const containerRect = elements.interactivePreview.getBoundingClientRect();
        let currentLeft = elements.logo.positionPreview.offsetLeft;
        let currentTop = elements.logo.positionPreview.offsetTop;
        const currentWidth = state.logoPosition.baseWidth * state.logoPosition.scale;
        const currentHeight = state.logoPosition.baseHeight * state.logoPosition.scale;

        let changed = false;

        // Adjust X
        if (currentLeft < 0) { currentLeft = 0; changed = true; }
        if (currentLeft + currentWidth > containerRect.width) {
            currentLeft = containerRect.width - currentWidth; changed = true;
        }

        // Adjust Y
        if (currentTop < 0) { currentTop = 0; changed = true; }
        if (currentTop + currentHeight > containerRect.height) {
            currentTop = containerRect.height - currentHeight; changed = true;
        }

        if (changed) {
            // Update state variables (center percentage)
            state.logoPosition.x = (currentLeft + currentWidth / 2) / containerRect.width * 100;
            state.logoPosition.y = (currentTop + currentHeight / 2) / containerRect.height * 100;
            // Re-apply the transform
            updateLogoTransform();
        }
    }

    function initializeLogoPositionAndScale() {
        if (!state.logoFile) return;

        // Reset to default position and scale
        state.logoPosition.x = 50;
        state.logoPosition.y = 50;
        const initialSliderValue = 50;
        elements.logo.sizeSlider.value = initialSliderValue;
        state.logoPosition.scale = initialSliderValue / 100;
        elements.logo.sizeValue.textContent = `${initialSliderValue}%`;

        // Calculate base dimensions if needed
        if (state.logoPosition.baseWidth === 0 && elements.logo.positionPreview.style.backgroundImage !== 'none') {
            const img = new Image();
            img.onload = () => {
                const previewContainerWidth = elements.interactivePreview.clientWidth;
                state.logoPosition.baseWidth = previewContainerWidth * 0.25;
                const aspectRatio = img.naturalHeight / img.naturalWidth;
                state.logoPosition.baseHeight = state.logoPosition.baseWidth * aspectRatio;
                updateLogoTransform();
            };

            // Extract src from background-image style
            const urlMatch = elements.logo.positionPreview.style.backgroundImage.match(/url\("?(.+?)"?\)/);
            if (urlMatch && urlMatch[1]) {
                img.src = urlMatch[1];
            }
        } else {
            updateLogoTransform();
        }
    }

    // --- Prompt Improvement ---
    async function improvePrompt() {
        const currentPrompt = elements.prompt.input.value.trim();
        if (!currentPrompt) {
            showError('Пожалуйста, введите текст промпта для улучшения.');
            return;
        }

        // Visual loading state
        const buttonSpan = elements.prompt.improve.querySelector('span');
        const originalButtonText = buttonSpan.textContent;
        elements.prompt.improve.disabled = true;
        buttonSpan.textContent = 'Улучшаем...';
        hideError();

        try {
            const response = await fetch('/improve-prompt', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: currentPrompt }),
            });

            const data = await response.json();

            if (response.ok && data.improved_prompt) {
                elements.prompt.input.value = data.improved_prompt;

                // Highlight animation
                elements.prompt.input.classList.add('highlighted');
                setTimeout(() => {
                    elements.prompt.input.classList.remove('highlighted');
                }, 1000);
            } else {
                showError(data.error || `Ошибка ${response.status}: Не удалось улучшить промпт.`);
            }
        } catch (error) {
            console.error('Ошибка при улучшении промпта:', error);
            showError('Сетевая ошибка или не удалось связаться с сервисом улучшения промптов.');
        } finally {
            // Reset button state
            elements.prompt.improve.disabled = false;
            buttonSpan.textContent = originalButtonText;
        }
    }

    // --- Form Submission ---
    async function handleFormSubmit(event) {
        event.preventDefault();

        // Reset UI
        hideError();
        elements.results.area.classList.add('hidden');

        // Validate submission
        if (!state.logoFile) {
            showError('Пожалуйста, загрузите логотип компании.');
            return;
        }

        const isGenerating = elements.bg.option.value === 'generate';
        const formData = new FormData();

        // Append logo and position data
        formData.append('logo', state.logoFile);
        formData.append('logoX', (state.logoPosition.x / 100).toFixed(4));
        formData.append('logoY', (state.logoPosition.y / 100).toFixed(4));
        formData.append('logoScale', state.logoPosition.scale.toFixed(4));
        formData.append('mode', isGenerating ? 'generate' : 'upload');

        // Add mode-specific data
        if (isGenerating) {
            if (!elements.prompt.input.value.trim()) {
                showError('Пожалуйста, опишите желаемый фон.');
                return;
            }
            formData.append('prompt', elements.prompt.input.value.trim());
            formData.append('style', document.querySelector('input[name="style-select"]:checked').value);
        } else {
            if (!state.backgroundFile) {
                showError('Пожалуйста, загрузите фон карты.');
                return;
            }
            formData.append('background', state.backgroundFile);
        }

        // Show loading
        showLoading(true);

        try {
            const response = await fetch('/generate-card', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.includes("image/")) {
                    const imageBlob = await response.blob();
                    elements.results.image.src = URL.createObjectURL(imageBlob);
                    elements.results.area.classList.remove('hidden');
                    elements.results.area.scrollIntoView({ behavior: 'smooth' });
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
    }

    // --- UI Helper Functions ---
    function showError(message) {
        elements.results.error.textContent = message;
        elements.results.error.classList.remove('hidden');
        elements.results.error.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function hideError() {
        elements.results.error.classList.add('hidden');
    }

    function showLoading(isLoading) {
        if (isLoading) {
            elements.results.loading.classList.remove('hidden');
            document.getElementById('generate-btn').disabled = true;
        } else {
            elements.results.loading.classList.add('hidden');
            document.getElementById('generate-btn').disabled = false;
        }
    }

    // --- Results Functions ---
    function downloadResult() {
        const link = document.createElement('a');
        link.href = elements.results.image.src;
        link.download = 'card-design.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function restartProcess() {
        // Reset form and state
        elements.form.reset();

        // Reset logo position and scale
        state.logoPosition = {
            x: 50,
            y: 50,
            scale: 0.5,
            baseWidth: 100,
            baseHeight: 0
        };

        elements.logo.sizeSlider.value = 50;
        elements.logo.sizeValue.textContent = '50%';
        elements.logo.positionPreview.style.backgroundImage = 'none';
        elements.logo.positionPreview.style.display = 'none';
        elements.logo.positionPreview.style.transform = 'translate(-50%, -50%) scale(0.5)';
        elements.logo.positionPreview.style.left = '50%';
        elements.logo.positionPreview.style.top = '50%';

        // Reset files
        state.logoFile = null;
        state.backgroundFile = null;
        elements.logo.upload.value = '';
        elements.bg.upload.value = '';

        // Reset UI elements
        elements.logo.previewArea.style.display = 'none';
        elements.logo.dropzone.style.display = 'block';
        elements.bg.previewArea.style.display = 'none';
        elements.bg.dropzone.style.display = 'block';

        // Reset navigation
        document.querySelector('.form-section.active').classList.remove('active');
        document.getElementById('section-1').classList.add('active');

        // Reset progress indicators
        elements.navigation.progressSteps.forEach((step, index) => {
            if (index === 0) {
                step.classList.add('active');
            } else {
                step.classList.remove('active');
                step.classList.remove('completed');
            }
        });

        elements.navigation.progressLines.forEach(line => {
            line.classList.remove('active');
        });

        // Reset background option tabs
        document.querySelector('.option-tab.active').classList.remove('active');
        document.querySelector('.option-tab[data-target="generate-inputs"]').classList.add('active');

        document.querySelector('.tab-content.active').classList.remove('active');
        elements.bg.generateInputs.classList.add('active');

        elements.bg.option.value = 'generate';

        // Hide result
        elements.results.area.classList.add('hidden');

        // Reset current section
        state.currentSection = 1;

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // --- Progress Bar Animation ---
    function initProgressBarAnimation() {
        const progressBarInner = document.querySelector('.progress-bar-inner');
        if (!progressBarInner) return;

        progressBarInner.style.width = '0%';
        let width = 0;
        let progressInterval;

        const simulateProgress = () => {
            return setInterval(() => {
                if (width >= 90) {
                    clearInterval(progressInterval);
                } else {
                    width += 1;
                    progressBarInner.style.width = width + '%';
                }
            }, 50);
        };

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class') {
                    const isHidden = elements.results.loading.classList.contains('hidden');
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

        observer.observe(elements.results.loading, { attributes: true });
    }

    // Initialize all event listeners
    initEventListeners();
});