// START OF FULL AND CORRECTED script.js

document.addEventListener('DOMContentLoaded', function() {
    // === DOM Elements ===
    const themeToggle = document.getElementById('themeToggle');
    const logContainer = document.getElementById('logContainer');
    const notification = document.getElementById('notification');
    const coverDropArea = document.getElementById('coverDropArea');
    const coverFileInput = document.getElementById('coverFileInput');
    const payloadDropArea = document.getElementById('payloadDropArea');
    const payloadFileInput = document.getElementById('payloadFileInput');
    const payloadFileDisplay = document.getElementById('payloadFileDisplay');
    const payloadFilenameSpan = document.getElementById('payloadFilename');
    const clearPayloadFileBtn = document.getElementById('clearPayloadFile');
    const extractedFileContainer = document.getElementById('extractedFileContainer');
    const extractedFileInfo = document.getElementById('extractedFileInfo');
    const downloadExtractedFileBtn = document.getElementById('downloadExtractedFile');
    const stegoDropArea = document.getElementById('stegoDropArea');
    const stegoFileInput = document.getElementById('stegoFileInput');
    const coverFileDisplay = document.getElementById('coverFileDisplay');
    const coverFilenameSpan = document.getElementById('coverFilename');
    const stegoFileDisplay = document.getElementById('stegoFileDisplay');
    const stegoFilenameSpan = document.getElementById('stegoFilename');
    const coverPreview = document.getElementById('coverPreview');
    const outputPreview = document.getElementById('outputPreview');
    const hideProgress = document.getElementById('hideProgress');
    const hideProgressBar = document.getElementById('hideProgressBar');
    const hideProgressText = document.getElementById('hideProgressText');
    const extractProgress = document.getElementById('extractProgress');
    const extractProgressBar = document.getElementById('extractProgressBar');
    const extractProgressText = document.getElementById('extractProgressText');
    const messageInput = document.getElementById('message');
    const extractedText = document.getElementById('extractedText');
    const encryptedMessage = document.getElementById('encryptedMessage');
    const encryptedExtracted = document.getElementById('encryptedExtracted');
    const encryptedKey = document.getElementById('encryptedKey');
    const extractedKey = document.getElementById('extractedKey');
    const rawEncryptedKey = document.getElementById('rawEncryptedKey');
    const psnrValue = document.getElementById('psnrValue');
    const ssimValue = document.getElementById('ssimValue');
    const berValue = document.getElementById('berValue');
    const capacityValue = document.getElementById('capacityValue');
    const psnrBar = document.getElementById('psnrBar');
    const ssimBar = document.getElementById('ssimBar');
    const berBar = document.getElementById('berBar');
    const capacityBar = document.getElementById('capacityBar');
    const hideMessageBtn = document.getElementById('hideMessage');
    const extractMessageBtn = document.getElementById('extractMessage');
    const keyDisplayContainer = document.getElementById('keyDisplayContainer');
    const currentKey = document.getElementById('currentKey');
    const toggleKeyVisibility = document.getElementById('toggleKeyVisibility');
    const copyKey = document.getElementById('copyKey');
    const keyStatus = document.getElementById('keyStatus');
    const generateKeyBtn = document.getElementById('generateKey');
    const loadKeyBtn = document.getElementById('loadKey');
    const copyEncrypted = document.getElementById('copyEncrypted');
    const copyEncryptedExtracted = document.getElementById('copyEncryptedExtracted');
    const copyEncryptedKey = document.getElementById('copyEncryptedKey');
    const copyExtractedKey = document.getElementById('copyExtractedKey');
    const copyRawKey = document.getElementById('copyRawKey');
    const toggleEncryptedVisibility = document.getElementById('toggleEncryptedVisibility');
    const toggleEncryptedExtractedVisibility = document.getElementById('toggleEncryptedExtractedVisibility');
    const toggleEncryptedKeyVisibility = document.getElementById('toggleEncryptedKeyVisibility');
    const toggleExtractedKeyVisibility = document.getElementById('toggleExtractedKeyVisibility');
    const toggleRawKeyVisibility = document.getElementById('toggleRawKeyVisibility');
    const batchCoverDropArea = document.getElementById('batchCoverDropArea');
    const batchCoverInput = document.getElementById('batchCoverInput');
    const batchCoverFileList = document.getElementById('batchCoverFileList');
    const batchCoverFileCount = document.getElementById('batchCoverFileCount');
    const clearBatchCoverFilesBtn = document.getElementById('clearBatchCoverFiles');
    const batchMessageInput = document.getElementById('batchMessage');
    const batchPayloadDropArea = document.getElementById('batchPayloadDropArea');
    const batchPayloadFileInput = document.getElementById('batchPayloadFileInput');
    const batchPayloadFileDisplay = document.getElementById('batchPayloadFileDisplay');
    const batchPayloadFilenameSpan = document.getElementById('batchPayloadFilename');
    const clearBatchPayloadFileBtn = document.getElementById('clearBatchPayloadFile');
    const startBatchHideBtn = document.getElementById('startBatchHide');
    const batchHideProgress = document.getElementById('batchHideProgress');
    const batchHideProgressBar = document.getElementById('batchHideProgressBar');
    const batchHideProgressText = document.getElementById('batchHideProgressText');
    const batchHideResultsContainer = document.getElementById('batchHideResultsContainer');
    const batchHideResultsBody = document.getElementById('batchHideResultsBody');
    const batchStegoDropArea = document.getElementById('batchStegoDropArea');
    const batchStegoInput = document.getElementById('batchStegoInput');
    const batchStegoFileList = document.getElementById('batchStegoFileList');
    const batchStegoFileCount = document.getElementById('batchStegoFileCount');
    const clearBatchStegoFilesBtn = document.getElementById('clearBatchStegoFiles');
    const startBatchExtractBtn = document.getElementById('startBatchExtract');
    const batchExtractProgress = document.getElementById('batchExtractProgress');
    const batchExtractProgressBar = document.getElementById('batchExtractProgressBar');
    const batchExtractProgressText = document.getElementById('batchExtractProgressText');
    const batchExtractResultsContainer = document.getElementById('batchExtractResultsContainer');
    const batchExtractResultsBody = document.getElementById('batchExtractResultsBody');
    const batchGraphsCard = document.getElementById('batchGraphsCard');
    const batchGraphsContent = document.getElementById('batchGraphsContent');
    const graphSliderContainer = document.getElementById('graphSliderContainer');
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    const fullscreenGraphModal = document.getElementById('fullscreenGraphModal');
    const fullscreenGraphImage = document.getElementById('fullscreenGraphImage');
    const closeFullscreenGraphBtn = document.getElementById('closeFullscreenGraph');

    // === Global Variables ===
    let currentKeyValue = null;
    let coverImageFile = null;
    let stegoImageFile = null;
    let payloadFile = null;
    let batchPayloadFile = null;
    let lastExtractedFile = null;
    let batchCoverFiles = [];
    let batchStegoFiles = [];
    let originalCoverFilename = '';
    let lastBatchHideResults = [];
    let graphSliderWrapper = null;
    let graphSlides = [];
    let graphPaginationDots = [];
    let currentGraphIndex = 0;
    let totalGraphSlides = 0;
    let currentActiveTabId = 'hideTabContent';

    // === Initialization ===
    function initApp() {
        addLog('Application initialized.', 'info');
        setupEventListeners();
        
        // Hide UI elements related to output directory selection
        const outputPathGroup = document.getElementById('outputPathGroup');
        const batchOutputPathGroup = document.getElementById('batchOutputPathGroup');
        if (outputPathGroup) outputPathGroup.style.display = 'none';
        if (batchOutputPathGroup) batchOutputPathGroup.style.display = 'none';

        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') {
            document.body.classList.add('light-mode');
            updateThemeButton(true);
        } else {
            updateThemeButton(false);
        }
        batchGraphsCard.style.display = 'none';
        activateTab(tabButtons[0], tabButtons[0].dataset.tab);
        addLog('Ready.', 'info');
        setupFullscreenListeners();
    }

    // === Event Listeners Setup ===
    function setupEventListeners() {
        themeToggle.addEventListener('click', toggleTheme);
        tabButtons.forEach(button => {
            button.addEventListener('click', () => activateTab(button, button.dataset.tab));
        });
        setupDragDrop(coverDropArea, (files) => handleCoverImage(files[0]));
        coverFileInput.addEventListener('change', (e) => handleCoverImage(e.target.files[0]));
        coverDropArea.addEventListener('click', () => coverFileInput.click());
        setupDragDrop(payloadDropArea, (files) => handlePayloadFile(files[0]));
        payloadFileInput.addEventListener('change', (e) => handlePayloadFile(e.target.files[0]));
        payloadDropArea.addEventListener('click', () => payloadFileInput.click());
        clearPayloadFileBtn.addEventListener('click', (e) => { e.stopPropagation(); clearPayloadFile(); });
        setupDragDrop(batchPayloadDropArea, (files) => handleBatchPayloadFile(files[0]));
        batchPayloadFileInput.addEventListener('change', (e) => handleBatchPayloadFile(e.target.files[0]));
        batchPayloadDropArea.addEventListener('click', () => batchPayloadFileInput.click());
        clearBatchPayloadFileBtn.addEventListener('click', (e) => { e.stopPropagation(); clearBatchPayloadFile(); });
        downloadExtractedFileBtn.addEventListener('click', () => {
            if (lastExtractedFile) triggerDownload(lastExtractedFile.data, lastExtractedFile.filename);
        });
        setupDragDrop(stegoDropArea, (files) => handleStegoImage(files[0]));
        stegoFileInput.addEventListener('change', (e) => handleStegoImage(e.target.files[0]));
        stegoDropArea.addEventListener('click', () => stegoFileInput.click());
        generateKeyBtn.addEventListener('click', generateKey);
        loadKeyBtn.addEventListener('click', loadKey);
        toggleKeyVisibility.addEventListener('click', () => toggleInputVisibility(currentKey, toggleKeyVisibility));
        copyKey.addEventListener('click', () => copyToClipboard(currentKeyValue, 'Encryption key copied'));
        hideMessageBtn.addEventListener('click', hideMessageAction);
        extractMessageBtn.addEventListener('click', extractMessageAction);
        setupVisibilityToggle(toggleEncryptedVisibility, encryptedMessage);
        setupVisibilityToggle(toggleEncryptedExtractedVisibility, encryptedExtracted);
        setupVisibilityToggle(toggleEncryptedKeyVisibility, encryptedKey);
        setupVisibilityToggle(toggleExtractedKeyVisibility, extractedKey);
        setupVisibilityToggle(toggleRawKeyVisibility, rawEncryptedKey);
        setupCopyButton(copyEncrypted, encryptedMessage);
        setupCopyButton(copyEncryptedExtracted, encryptedExtracted);
        setupCopyButton(copyEncryptedKey, encryptedKey);
        setupCopyButton(copyExtractedKey, extractedKey);
        setupCopyButton(copyRawKey, rawEncryptedKey);
        setupDragDrop(batchCoverDropArea, handleBatchCoverFiles);
        batchCoverInput.addEventListener('change', (e) => handleBatchCoverFiles(e.target.files));
        batchCoverDropArea.addEventListener('click', () => batchCoverInput.click());
        clearBatchCoverFilesBtn.addEventListener('click', () => clearBatchFiles('cover'));
        setupDragDrop(batchStegoDropArea, handleBatchStegoFiles);
        batchStegoInput.addEventListener('change', (e) => handleBatchStegoFiles(e.target.files));
        batchStegoDropArea.addEventListener('click', () => batchStegoInput.click());
        clearBatchStegoFilesBtn.addEventListener('click', () => clearBatchFiles('stego'));
        startBatchHideBtn.addEventListener('click', startBatchHideAction);
        startBatchExtractBtn.addEventListener('click', startBatchExtractAction);
        graphSliderContainer.addEventListener('click', (e) => {
            if (e.target.closest('.slider-button.next')) nextGraphSlide();
            else if (e.target.closest('.slider-button.prev')) prevGraphSlide();
            else if (e.target.classList.contains('slider-dot')) goToGraphSlide(parseInt(e.target.dataset.index));
            if (e.target.classList.contains('performance-graph') && e.target.classList.contains('loaded')) openFullscreenGraph(e.target.src);
        });
    }

    function setupFullscreenListeners() {
        closeFullscreenGraphBtn.addEventListener('click', closeFullscreenGraph);
        fullscreenGraphModal.addEventListener('click', (e) => { if (e.target === fullscreenGraphModal) closeFullscreenGraph(); });
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeFullscreenGraph(); });
    }

    // === Helper: Trigger Download from Data URL or Blob ===
    function triggerDownload(data, filename) {
        const link = document.createElement('a');
        link.href = data;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        addLog(`Download prompted for: ${filename}`, 'info');
    }

    // === Steganography Actions (FIXED) ===
    function hideMessageAction() {
        if (!coverImageFile) return showNotification('Please select a cover image.', 'warning');
        if (!messageInput.value.trim() && !payloadFile) return showNotification('Please enter a message or select a file to hide.', 'warning');
        if (!currentKeyValue) return showNotification('A key is required. Please generate or load one.', 'warning');
        hideMessage();
    }

    function extractMessageAction() {
        if (!stegoImageFile) return showNotification('Please select a stego image to extract from.', 'warning');
        extractMessage();
    }

    function hideMessage() {
        addLog('Hiding message...', 'info');
        showProgress(hideProgress, hideProgressBar, hideProgressText, 10);
        resetMetrics();
        const timestamp = new Date().toISOString().replace(/[-:.]/g, '').replace('T', '_').slice(0, 15);
        const baseFilename = originalCoverFilename || 'stego_image';
        const outputFilename = `${baseFilename}_${timestamp}.png`;
        const keyFilename = `${baseFilename}_${timestamp}.key`;
        const formData = new FormData();
        formData.append('coverImage', coverImageFile);
        formData.append('message', messageInput.value);
        if (payloadFile) formData.append('payloadFile', payloadFile);
        formData.append('key', currentKeyValue);
        formData.append('useAES', document.getElementById('useAES').checked);
        formData.append('enhancedBit', document.getElementById('enhancedBit').checked);
        formData.append('adaptiveChannel', document.getElementById('adaptiveChannel').checked);
        formData.append('errorCorrection', document.getElementById('errorCorrection').checked);
        formData.append('embedKey', document.getElementById('embedKey').checked);
        fetch('/api/hide_message', { method: 'POST', body: formData })
            .then(response => {
                if (!response.ok) return response.json().then(err => { throw new Error(err.error || 'Server error'); });
                return response.json();
            })
            .then(d => {
                if (d.success) {
                    simulateProgress(hideProgressBar, hideProgressText, () => {
                        hideProgress.style.display = 'none';
                        outputPreview.src = d.outputImage;
                        encryptedMessage.value = d.encryptedData || '';
                        encryptedKey.value = d.encryptedKey || '';
                        updateMetrics(d.metrics || {});
                        if (d.isFilePayload) {
                            showNotification(`File "${d.payloadFilename}" hidden! Check your downloads.`, 'success');
                            addLog(`Hidden file payload: ${d.payloadFilename}`, 'success');
                        } else {
                            showNotification('Message hidden! Check your downloads.', 'success');
                        }
                        
                        // --- THIS IS THE MODIFIED PART ---
                        // Trigger image download
                        triggerDownload(d.outputImage, outputFilename);
                        // If key content exists, create a Blob and trigger its download
                        if (d.keyContent) {
                            const keyBlob = new Blob([d.keyContent], { type: 'text/plain' });
                            triggerDownload(URL.createObjectURL(keyBlob), keyFilename);
                        }
                        // ------------------------------------

                    });
                } else {
                    handleOperationError('Hiding failed', d.error, hideProgress);
                }
            })
            .catch(e => handleOperationError('Network error during hiding', e, hideProgress));
    }

    function extractMessage() {
        addLog('Extracting message...', 'info');
        showProgress(extractProgress, extractProgressBar, extractProgressText, 10);
        // Clear previous results
        extractedText.value = '';
        encryptedExtracted.value = '';
        extractedKey.value = '';
        rawEncryptedKey.value = '';

        const formData = new FormData();
        formData.append('stegoImage', stegoImageFile);
        formData.append('key', currentKeyValue || '');
        formData.append('useAES', document.getElementById('useAES').checked);
        formData.append('enhancedBit', document.getElementById('enhancedBit').checked);
        formData.append('adaptiveChannel', document.getElementById('adaptiveChannel').checked);
        formData.append('extractKey', document.getElementById('embedKey').checked);

        fetch('/api/extract_message', { method: 'POST', body: formData })
        .then(response => {
            if (!response.ok) return response.json().then(err => { throw new Error(err.error || 'Server returned an error'); });
            return response.json();
        })
        .then(d => {
            if (d.success) {
                simulateProgress(extractProgressBar, extractProgressText, () => {
                    extractProgress.style.display = 'none';
                    // Populate ALL fields with the response data
                    extractedText.value = d.message || 'No message was found or decrypted.';
                    encryptedExtracted.value = d.rawData || '';
                    extractedKey.value = d.extractedKey || '';
                    rawEncryptedKey.value = d.rawKeyData || '';

                    if (d.modeMismatchDetected) {
                        document.getElementById('enhancedBit').checked = d.actualEnhancedBit;
                        document.getElementById('adaptiveChannel').checked = d.actualAdaptiveChannel;
                        const modeLabel = d.actualEnhancedBit ? 'Enhanced Bit Distribution + Adaptive Channel ON' : 'Enhanced Bit Distribution + Adaptive Channel OFF';
                        addLog(`Your Enhanced/Adaptive settings didn't match this image - auto-detected and switched to: ${modeLabel}.`, 'warning');
                        showNotification(`Settings auto-corrected: this file was hidden with ${modeLabel}.`, 'warning');
                    }

                    if (d.isFile) {
                        lastExtractedFile = { data: d.fileData, filename: d.filename };
                        extractedFileInfo.textContent = `${d.filename} (${formatBytes(d.fileSize)})`;
                        extractedFileContainer.style.display = 'block';
                        addLog(`Extracted a hidden file: ${d.filename}`, 'success');
                    } else {
                        lastExtractedFile = null;
                        extractedFileContainer.style.display = 'none';
                    }

                    if (d.extractedKey && !currentKeyValue) {
                        currentKeyValue = d.extractedKey;
                        displayKey(currentKeyValue);
                        updateKeyStatus(true, 'Key was successfully extracted from image.');
                        addLog('Key extracted and loaded from image.', 'success');
                    } else if (d.extractedKey) {
                        addLog(`An embedded key was found: ${d.extractedKey.substring(0,8)}...`, 'info');
                    }
                    addLog('Extraction process completed.', 'success');
                    showNotification('Extraction successful!', 'success');
                });
            } else {
                // Also populate fields on failure, as there might be partial data
                extractedText.value = d.message || 'Extraction failed. See logs for details.';
                encryptedExtracted.value = d.rawData || '';
                extractedKey.value = d.extractedKey || '';
                rawEncryptedKey.value = d.rawKeyData || '';
                lastExtractedFile = null;
                extractedFileContainer.style.display = 'none';
                handleOperationError('Extraction failed', d.message, extractProgress);
            }
        })
        .catch(e => handleOperationError('Network error during extraction', e, extractProgress));
    }

    // === Batch Processing Actions (FIXED) ===
    function startBatchHideAction() {
        if (batchCoverFiles.length === 0) return showNotification('Please select images for the batch process.', 'warning');
        if (!batchMessageInput.value.trim() && !batchPayloadFile) return showNotification('Please enter a message or select a file for the batch process.', 'warning');
        if (!currentKeyValue) return showNotification('A key is required for the batch process.', 'warning');
        
        graphSliderContainer.innerHTML = `<div class="initial-loading-graphs"><i class="fas fa-spinner fa-spin"></i> Waiting for batch results...</div>`;
        lastBatchHideResults = [];
        batchGraphsCard.style.display = 'none';
        startBatchHide();
    }

    function startBatchExtractAction() {
        if (batchStegoFiles.length === 0) return showNotification('Please select stego images for batch extraction.', 'warning');
        startBatchExtract();
    }

    function startBatchHide() {
        addLog(`Starting Batch Hide for ${batchCoverFiles.length} images...`, 'info');
        startBatchHideBtn.disabled = true;
        startBatchHideBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        batchHideResultsContainer.style.display = 'none';
        batchHideResultsBody.innerHTML = '';
        showProgress(batchHideProgress, batchHideProgressBar, batchHideProgressText, 0);
        
        const formData = new FormData();
        formData.append('message', batchMessageInput.value);
        if (batchPayloadFile) formData.append('payloadFile', batchPayloadFile);
        formData.append('key', currentKeyValue);
        formData.append('useAES', document.getElementById('useAES').checked);
        formData.append('enhancedBit', document.getElementById('enhancedBit').checked);
        formData.append('adaptiveChannel', document.getElementById('adaptiveChannel').checked);
        formData.append('errorCorrection', document.getElementById('errorCorrection').checked);
        formData.append('embedKey', document.getElementById('embedKey').checked);
        batchCoverFiles.forEach(file => formData.append('coverImages', file, file.name));

        fetch('/api/batch_hide', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(d => handleBatchHideComplete(d))
        .catch(e => handleOperationError('Network error during Batch Hide', e, batchHideProgress))
        .finally(() => {
            startBatchHideBtn.disabled = false;
            startBatchHideBtn.innerHTML = '<i class="fas fa-cogs"></i> Start Batch Hide';
            batchHideProgressBar.style.width = '100%';
            batchHideProgressText.textContent = 'Complete';
            setTimeout(() => { batchHideProgress.style.display = 'none'; }, 1500);
        });
    }

    function startBatchExtract() {
        addLog(`Starting Batch Extract for ${batchStegoFiles.length} images...`, 'info');
        startBatchExtractBtn.disabled = true;
        startBatchExtractBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        batchExtractResultsContainer.style.display = 'none';
        batchExtractResultsBody.innerHTML = '';
        showProgress(batchExtractProgress, batchExtractProgressBar, batchExtractProgressText, 0);
        
        const formData = new FormData();
        formData.append('key', currentKeyValue || '');
        formData.append('useAES', document.getElementById('useAES').checked);
        formData.append('enhancedBit', document.getElementById('enhancedBit').checked);
        formData.append('adaptiveChannel', document.getElementById('adaptiveChannel').checked);
        formData.append('extractKey', document.getElementById('embedKey').checked);
        batchStegoFiles.forEach(file => formData.append('stegoImages', file, file.name));

        fetch('/api/batch_extract', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(d => handleBatchExtractComplete(d))
        .catch(e => handleOperationError('Network error during Batch Extract', e, batchExtractProgress))
        .finally(() => {
            startBatchExtractBtn.disabled = false;
            startBatchExtractBtn.innerHTML = '<i class="fas fa-cogs"></i> Start Batch Extract';
            batchExtractProgressBar.style.width = '100%';
            batchExtractProgressText.textContent = 'Complete';
            setTimeout(() => { batchExtractProgress.style.display = 'none'; }, 1500);
        });
    }

    function handleBatchHideComplete(data) {
        if (data.success) {
            displayBatchHideResults(data.results || []);
            
            // --- THIS IS THE MODIFIED PART ---
            if (data.zipFile && data.zipFilename) {
                triggerDownload(data.zipFile, data.zipFilename);
                showNotification('Batch complete! A ZIP file with results is downloading.', 'success');
            }
            // ------------------------------------

            if (lastBatchHideResults.length > 0) {
                triggerGraphGeneration(lastBatchHideResults);
            } else {
                addLog('Batch Hide finished, but no files were processed successfully.', 'warning');
                if (currentActiveTabId === 'batchTabContent') batchGraphsCard.style.display = 'none';
            }
        } else {
            handleOperationError('Batch Hide failed', data.error || 'An unknown backend error occurred.', batchHideProgress);
            displayBatchHideResults(data.results || [], data.error);
            batchGraphsCard.style.display = 'none';
        }
    }

    function handleBatchExtractComplete(data) {
         if (data.success) {
             displayBatchExtractResults(data.results || []);

             const mismatchCount = (data.results || []).filter(r => r.modeMismatchDetected).length;
             if (mismatchCount > 0) {
                 addLog(`${mismatchCount} image(s) were hidden with different Enhanced Bit Distribution / Adaptive Channel settings than yours - auto-detected and corrected (see the ✨ marker in the results table).`, 'warning');
             }

             if (data.resultsText && data.resultsFilename) {
                const resultsBlob = new Blob([data.resultsText], { type: 'text/plain;charset=utf-8' });
                triggerDownload(URL.createObjectURL(resultsBlob), data.resultsFilename);
                showNotification('Batch extraction complete! A text file with results is downloading.', 'success');
             }
         } else {
             handleOperationError('Batch Extract failed', data.error || 'An unknown backend error occurred.', batchExtractProgress);
             displayBatchExtractResults(data.results || [], data.error);
         }
         batchGraphsCard.style.display = 'none';
     }

    // === Unchanged Helper Functions (logging, UI, etc.) ===
    // (The rest of the helper functions from your original file can be pasted here without modification)

    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }
    function addLog(message, type = 'info') { const now = new Date(); const time = now.toTimeString().split(' ')[0]; const logEntry = document.createElement('div'); logEntry.className = 'log-entry'; const safeMessage = String(message).replace(/</g, "&lt;").replace(/>/g, "&gt;"); logEntry.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-${type}">${safeMessage}</span>`; logContainer.appendChild(logEntry); logContainer.scrollTop = logContainer.scrollHeight; }
    function showNotification(message, type = 'info') { notification.textContent = ''; let iconClass = 'fa-info-circle'; if (type === 'success') iconClass = 'fa-check-circle'; else if (type === 'error') iconClass = 'fa-exclamation-circle'; else if (type === 'warning') iconClass = 'fa-exclamation-triangle'; notification.className = `notification ${type}`; notification.innerHTML = `<i class="fas ${iconClass}"></i> ${message}`; notification.classList.add('show'); setTimeout(() => { notification.classList.remove('show'); }, 4000); }
    function isImageFile(file) { return !!(file && file.type && file.type.startsWith('image/')); }
    function formatBytes(bytes, decimals = 2) { if (!+bytes) return '0 Bytes'; const k = 1024; const dm = decimals < 0 ? 0 : decimals; const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']; const i = Math.floor(Math.log(bytes) / Math.log(k)); return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`; }
    function toggleInputVisibility(element, toggleButton) { const icon = toggleButton.querySelector('i'); if (element.type === 'password') { element.type = 'text'; icon.classList.replace('fa-eye', 'fa-eye-slash'); } else { element.type = 'password'; icon.classList.replace('fa-eye-slash', 'fa-eye'); } }
    function copyToClipboard(text, successMessage) { if (!text) { showNotification('Nothing to copy', 'warning'); return; } navigator.clipboard.writeText(text).then(() => { showNotification(successMessage, 'success'); addLog(`${successMessage} copied.`, 'info'); }).catch(err => { showNotification('Failed to copy: ' + err, 'error'); addLog(`Failed to copy ${successMessage}: ${err}`, 'error'); }); }
    function setupVisibilityToggle(button, element) { button.addEventListener('click', () => toggleInputVisibility(element, button)); }
    function setupCopyButton(button, element) { button.addEventListener('click', () => copyToClipboard(element.value, `${element.id} copied`)); }
    function toggleTheme() { const isLight = document.body.classList.toggle('light-mode'); updateThemeButton(isLight); localStorage.setItem('theme', isLight ? 'light' : 'dark'); addLog(`Theme changed to ${isLight ? 'Light' : 'Dark'} Mode`, 'info'); }
    function updateThemeButton(isLight) { const icon = themeToggle.querySelector('i'); const text = themeToggle.querySelector('span'); if (isLight) { icon.className = 'fas fa-sun'; text.textContent = 'Light Mode'; } else { icon.className = 'fas fa-moon'; text.textContent = 'Dark Mode'; } }
    function activateTab(selectedButton, tabId) { tabButtons.forEach(button => button.classList.remove('active')); tabContents.forEach(content => content.classList.remove('active')); selectedButton.classList.add('active'); document.getElementById(tabId).classList.add('active'); currentActiveTabId = tabId; if (tabId === 'batchTabContent' && lastBatchHideResults.length > 0) { batchGraphsCard.style.display = 'block'; } else { batchGraphsCard.style.display = 'none'; } }
    function setupDragDrop(area, callback) { ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => { area.addEventListener(eventName, preventDefaults, false); document.body.addEventListener(eventName, preventDefaults, false); }); ['dragenter', 'dragover'].forEach(eventName => area.addEventListener(eventName, () => area.classList.add('active'), false)); ['dragleave', 'drop'].forEach(eventName => area.addEventListener(eventName, () => area.classList.remove('active'), false)); area.addEventListener('drop', (e) => { const files = e.dataTransfer.files; if (files.length) { callback(files); } }, false); }
    function handleCoverImage(file) { if (!file || !isImageFile(file)) { showNotification('Invalid cover image type. Please upload an image file.', 'error'); return; } originalCoverFilename = file.name.split('.').slice(0, -1).join('.') || 'image'; coverFilenameSpan.textContent = `${file.name} (${formatBytes(file.size)})`; coverFileDisplay.style.display = 'flex'; coverImageFile = file; coverPreview.src = URL.createObjectURL(file); addLog(`Cover image loaded: ${file.name}`, 'success'); resetMetrics(); }
    function handleStegoImage(file) { if (!file || !isImageFile(file)) { showNotification('Invalid stego image type. Please upload an image file.', 'error'); return; } stegoFilenameSpan.textContent = `${file.name} (${formatBytes(file.size)})`; stegoFileDisplay.style.display = 'flex'; stegoImageFile = file; outputPreview.src = URL.createObjectURL(file); addLog(`Stego image loaded: ${file.name}`, 'success'); extractedText.value = ''; encryptedExtracted.value = ''; extractedKey.value = ''; rawEncryptedKey.value = ''; lastExtractedFile = null; extractedFileContainer.style.display = 'none'; }
    function handlePayloadFile(file) {
        if (!file) return;
        payloadFile = file;
        payloadFilenameSpan.textContent = `${file.name} (${formatBytes(file.size)})`;
        payloadFileDisplay.style.display = 'flex';
        addLog(`File to hide loaded: ${file.name} - this will replace the text message.`, 'success');
    }
    function clearPayloadFile() {
        payloadFile = null;
        payloadFileInput.value = '';
        payloadFileDisplay.style.display = 'none';
        addLog('Cleared file payload - text message will be used instead.', 'info');
    }
    function handleBatchPayloadFile(file) {
        if (!file) return;
        batchPayloadFile = file;
        batchPayloadFilenameSpan.textContent = `${file.name} (${formatBytes(file.size)})`;
        batchPayloadFileDisplay.style.display = 'flex';
        addLog(`Batch file to hide loaded: ${file.name} - this will replace the text message for every image.`, 'success');
    }
    function clearBatchPayloadFile() {
        batchPayloadFile = null;
        batchPayloadFileInput.value = '';
        batchPayloadFileDisplay.style.display = 'none';
        addLog('Cleared batch file payload - text message will be used instead.', 'info');
    }
    function handleBatchCoverFiles(files) { handleBatchFiles(files, 'cover'); }
    function handleBatchStegoFiles(files) { handleBatchFiles(files, 'stego'); }
    function handleBatchFiles(files, type) { const fileListEl = type === 'cover' ? batchCoverFileList : batchStegoFileList; const fileArray = type === 'cover' ? batchCoverFiles : batchStegoFiles; const maxFiles = 50; for (const file of files) { if (fileArray.length >= maxFiles) { showNotification(`Maximum batch size (${maxFiles}) reached.`, 'warning'); break; } if (isImageFile(file) && !fileArray.some(f => f.name === file.name && f.size === file.size)) { fileArray.push(file); } else if (!isImageFile(file)) { showNotification(`Skipping invalid file type: ${file.name}`, 'warning'); } } renderBatchFileList(type); }
    function renderBatchFileList(type) { const fileListEl = type === 'cover' ? batchCoverFileList : batchStegoFileList; const fileArray = type === 'cover' ? batchCoverFiles : batchStegoFiles; const countSpan = type === 'cover' ? batchCoverFileCount : batchStegoFileCount; fileListEl.innerHTML = ''; countSpan.textContent = fileArray.length; fileArray.forEach((file, index) => { const li = document.createElement('li'); li.innerHTML = `<span>${file.name} (${formatBytes(file.size)})</span><button class="remove-file" title="Remove file">&times;</button>`; li.querySelector('button').onclick = (e) => { e.stopPropagation(); removeBatchFile(index, type); }; fileListEl.appendChild(li); }); }
    function removeBatchFile(index, type) { if (type === 'cover') batchCoverFiles.splice(index, 1); else batchStegoFiles.splice(index, 1); renderBatchFileList(type); }
    function clearBatchFiles(type) { if (type === 'cover') batchCoverFiles = []; else batchStegoFiles = []; renderBatchFileList(type); }
    function generateKey() { addLog('Generating new key...', 'info'); fetch('/api/generate_key', { method: 'POST' }).then(r=>r.json()).then(d => { if(d.key) { currentKeyValue=d.key; displayKey(currentKeyValue); updateKeyStatus(true, 'New key generated.'); addLog('New AES-256 key generated.', 'success'); showNotification('New key generated', 'success'); } else handleKeyError('Error generating key', d.error); }).catch(e=>handleKeyError('Network error generating key', e)); }
    function loadKey() { const input = document.createElement('input'); input.type='file'; input.accept='.key,.txt'; input.onchange = function() { if(this.files.length) { const file = this.files[0]; const reader = new FileReader(); reader.onload = (e) => { const keyContent = e.target.result.trim(); if(/^[0-9a-fA-F]{64}$/.test(keyContent)) { currentKeyValue = keyContent.toLowerCase(); displayKey(currentKeyValue); updateKeyStatus(true, `Key loaded from ${file.name}.`); showNotification('Key loaded', 'success'); } else { handleKeyError(`Invalid key format in ${file.name}.`, 'Must be 64 hex characters.'); } }; reader.readAsText(file); } }; input.click(); }
    function displayKey(key) { keyDisplayContainer.style.display = 'block'; currentKey.value = key; currentKey.type = 'password'; toggleKeyVisibility.querySelector('i').classList.replace('fa-eye-slash', 'fa-eye'); }
    function updateKeyStatus(hasKey, message = '') { keyStatus.innerHTML = hasKey ? `<i class="fas fa-check-circle" style="color: var(--success);"></i> <span>${message || 'Key is ready.'}</span>` : `<i class="fas fa-times-circle" style="color: var(--error);"></i> <span>${message || 'No valid key.'}</span>`; keyStatus.style.color = hasKey ? 'var(--success)' : 'var(--error)'; keyStatus.style.display = 'block'; }
    function handleKeyError(logMessage, errorDetails) { const details = errorDetails instanceof Error ? errorDetails.message : String(errorDetails); addLog(`${logMessage}: ${details}`, 'error'); showNotification(logMessage, 'error'); updateKeyStatus(false, logMessage); currentKeyValue = null; }
    function handleOperationError(logPrefix, errorDetails, progressElement) { const details = errorDetails instanceof Error ? errorDetails.message : String(errorDetails); addLog(`${logPrefix}: ${details}`, 'error'); showNotification(logPrefix, 'error'); if (progressElement) progressElement.style.display = 'none'; }
    

    // In script.js, find and replace this entire function

function displayBatchHideResults(results, overallError = null) {
    batchHideResultsBody.innerHTML = ''; // Clear previous results
    batchHideResultsContainer.style.display = 'none';
    lastBatchHideResults = [];

    if (overallError) {
        const row = batchHideResultsBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 11; // Corresponds to the 11 columns in the header
        cell.innerHTML = `<span class="status-error">Overall Batch Error: ${overallError}</span>`;
        addLog(`Batch Hide Failed (Overall): ${overallError}`, 'error');
    }

    let successCount = 0;

    if (results && results.length > 0) {
        results.forEach(result => {
            const row = batchHideResultsBody.insertRow();

            // --- THIS IS THE KEY FIX ---
            // Create a cell for each column and populate it with the correct data
            
            // 1. Filename
            row.insertCell().textContent = result.filename || 'N/A';
            
            // 2. Status
            const statusCell = row.insertCell();
            statusCell.innerHTML = result.success ? '<span class="status-success">Success</span>' : `<span class="status-error">Error</span>`;

            // 3. Output Path (shows filename in zip) or Error Message
            const pathCell = row.insertCell();
            pathCell.textContent = result.success ? result.outputPath : (result.error || 'N/A');
            if (!result.success) pathCell.classList.add('status-error');

            // 4. PSNR
            row.insertCell().textContent = result.success ? (result.psnr || 0).toFixed(2) : '--';
            
            // 5. SSIM
            row.insertCell().textContent = result.success ? (result.ssim || 0).toFixed(4) : '--';
            
            // 6. Capacity
            row.insertCell().textContent = result.success ? (result.capacity || 0).toFixed(4) : '--';
            
            // 7. BER
            const ber = result.ber;
            row.insertCell().textContent = result.success ? (ber < 0.0001 && ber !== 0 ? ber.toExponential(2) : (ber || 0).toFixed(4)) : '--';

            // Helper function to create preview spans for long text
            const createPreviewCell = (text) => {
                const cell = row.insertCell();
                if (text) {
                    const span = document.createElement('span');
                    span.className = 'message-preview';
                    span.textContent = `${String(text).substring(0, 15)}...`;
                    span.title = String(text); // Full text on hover
                    cell.appendChild(span);
                } else {
                    cell.textContent = '--';
                }
            };
            
            // 8. Msg (Original Message)
            createPreviewCell(result.message);

            // 9. Key
            createPreviewCell(result.key);
            
            // 10. EncMsg (Encrypted Message)
            createPreviewCell(result.encrypted_message);

            // 11. EncKey (Encrypted Key)
            createPreviewCell(result.encrypted_key);
            
            // ---------------------------------

            if (result.success) {
                successCount++;
                lastBatchHideResults.push(result);
            }
        });
        
        batchHideResultsContainer.style.display = 'block';
    } else if (!overallError) {
        const row = batchHideResultsBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 11;
        cell.textContent = 'No results to display.';
        addLog('Batch Hide: No files were processed or no results were returned.', 'warning');
    }

    addLog(`Batch Hide results processed. ${successCount} successful, ${(results?.length || 0) - successCount} failed.`, 'info');
}
    // In script.js, find and replace this entire function

function displayBatchExtractResults(results, overallError = null) {
    batchExtractResultsBody.innerHTML = ''; // Clear previous results
    batchExtractResultsContainer.style.display = 'none';

    if (overallError) {
        const row = batchExtractResultsBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 6; // Corresponds to the 6 columns in the header
        cell.innerHTML = `<span class="status-error">Overall Batch Error: ${overallError}</span>`;
    }

    if (results && results.length > 0) {
        // Helper function to create preview cells for potentially long text
        const createPreviewCell = (row, text) => {
            const cell = row.insertCell();
            if (text) {
                const span = document.createElement('span');
                span.className = 'message-preview';
                span.textContent = `${String(text).substring(0, 20)}...`; // Show more characters
                span.title = String(text); // Full text appears on hover
                cell.appendChild(span);
            } else {
                cell.textContent = '--';
            }
        };

        results.forEach(result => {
            const row = batchExtractResultsBody.insertRow();
            
            // --- THIS IS THE KEY FIX ---
            // Build the table row cell by cell to ensure correct structure and data
            
            // 1. Filename
            row.insertCell().textContent = result.filename || 'N/A';
            
            // 2. Status
            const statusCell = row.insertCell();
            if (result.success) {
                statusCell.innerHTML = '<span class="status-success">Success</span>';
                if (result.modeMismatchDetected) {
                    const badge = document.createElement('span');
                    badge.title = 'Enhanced Bit Distribution / Adaptive Channel settings did not match this image - the correct settings were auto-detected.';
                    badge.style.marginLeft = '6px';
                    badge.innerHTML = '<i class="fas fa-magic" style="color: var(--warning);"></i>';
                    statusCell.appendChild(badge);
                }
            } else {
                statusCell.innerHTML = `<span class="status-error" title="${result.error || 'Unknown Error'}">Error</span>`;
            }

            // 3. Extracted Msg (or a download button, if a file was hidden instead of text)
            const msgCell = row.insertCell();
            if (result.success && result.isFile) {
                const btn = document.createElement('button');
                btn.className = 'secondary small';
                btn.innerHTML = `<i class="fas fa-download"></i> ${result.extractedFilename}`;
                btn.title = `Download ${result.extractedFilename} (${formatBytes(result.fileSize)})`;
                btn.addEventListener('click', () => triggerDownload(result.fileData, result.extractedFilename));
                msgCell.appendChild(btn);
            } else {
                msgCell.textContent = result.success ? (result.message || '(empty)') : (result.error || 'N/A');
                msgCell.title = result.success ? result.message : result.error; // Show full content on hover
            }
            
            // 4. Extracted Key
            createPreviewCell(row, result.extractedKey);
            
            // 5. Raw Enc. Msg
            createPreviewCell(row, result.rawData);

            // 6. Raw Enc. Key
            createPreviewCell(row, result.rawKeyData);
            
            // ---------------------------------
        });
        
        batchExtractResultsContainer.style.display = 'block';
    } else if (!overallError) {
        const row = batchExtractResultsBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 6;
        cell.textContent = 'No results to display.';
    }
}
    function showProgress(container, bar, text, initialPercent) { container.style.display = 'block'; bar.style.width = `${initialPercent}%`; text.textContent = `${initialPercent}%`; }
    function simulateProgress(bar, textElement, callback) { let p = parseInt(bar.style.width) || 10; const i = setInterval(() => { p += Math.random() * 15 + 5; if (p >= 100) { p = 100; clearInterval(i); bar.style.width = '100%'; textElement.textContent = '100%'; setTimeout(callback, 300); } else { bar.style.width = `${p}%`; textElement.textContent = `${p}%`; } }, 200); }
    function updateMetrics(metrics) { const { psnr = 0, ssim = 0, ber = 1, capacity = 0 } = metrics; psnrValue.textContent = `${psnr.toFixed(2)} dB`; ssimValue.textContent = `${ssim.toFixed(4)}`; capacityValue.textContent = `${capacity.toFixed(4)} bpp`; berValue.textContent = `${ber < 1e-4 && ber > 0 ? ber.toExponential(2) : ber.toFixed(4)}`; psnrBar.style.width = `${Math.min(Math.max((psnr - 30) / 20 * 100, 0), 100)}%`; ssimBar.style.width = `${Math.min(Math.max((ssim - 0.9) / 0.1 * 100, 0), 100)}%`; capacityBar.style.width = `${Math.min(Math.max(capacity / 2 * 100, 0), 100)}%`; berBar.style.width = `${Math.min(Math.max((1 - ber / 0.01) * 100, 0), 100)}%`; }
    function resetMetrics() { psnrValue.textContent = '--'; ssimValue.textContent = '--'; berValue.textContent = '--'; capacityValue.textContent = '--'; psnrBar.style.width = '0%'; ssimBar.style.width = '0%'; berBar.style.width = '0%'; capacityBar.style.width = '0%'; }
    function triggerGraphGeneration(resultsData) { addLog('Requesting performance graph generation...', 'info'); if (currentActiveTabId === 'batchTabContent') { batchGraphsCard.style.display = 'block'; } graphSliderContainer.innerHTML = `<div class="initial-loading-graphs"><i class="fas fa-spinner fa-spin"></i> Generating Graphs...</div>`; const payload = resultsData.filter(r => r.success).map(r => ({ filename: r.filename, psnr: r.psnr ?? 0, ssim: r.ssim ?? 0, ber: r.ber ?? 1, capacity: r.capacity ?? 0, file_size: r.file_size ?? 0 })); fetch('/api/batch_performance_graphs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ results: payload }) }).then(r => r.json()).then(d => { if (d.success && d.graphs.length > 0) { buildAndDisplayGraphSlider(d.graphs); } else { throw new Error(d.error || 'No graphs were generated.'); } }).catch(e => { graphSliderContainer.innerHTML = `<div class="graph-error"><i class="fas fa-exclamation-triangle"></i> Error generating graphs: ${e.message}</div>`; }); }
    function buildAndDisplayGraphSlider(urls) { graphSliderContainer.innerHTML = ''; graphSliderWrapper = document.createElement('div'); graphSliderWrapper.className = 'graph-slider-wrapper'; const pagination = document.createElement('div'); pagination.className = 'slider-pagination'; graphSlides = []; graphPaginationDots = []; totalGraphSlides = urls.length; currentGraphIndex = 0; const titles = { 'scatter_plots.png': 'Performance Scatter Plots', 'multi_metric_line.png': 'Multi-Metric Comparison', 'radar_chart.png': 'Performance Radar Profile' }; urls.forEach((url, i) => { const filename = url.split('/').pop().split('?')[0]; const slide = document.createElement('div'); slide.className = 'graph-slider-slide'; slide.innerHTML = `<h4>${titles[filename] || `Performance Graph ${i + 1}`}</h4><div class="graph-image-wrapper"><div class="graph-loading"><i class="fas fa-spinner fa-spin"></i> Loading...</div><img class="performance-graph" alt="${titles[filename]}"></div>`; graphSliderWrapper.appendChild(slide); graphSlides.push(slide); const img = slide.querySelector('img'); const loader = slide.querySelector('.graph-loading'); const tempImg = new Image(); tempImg.onload = () => { img.src = tempImg.src; img.classList.add('loaded'); loader.style.display = 'none'; }; tempImg.onerror = () => { loader.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error loading graph'; }; tempImg.src = url; const dot = document.createElement('span'); dot.className = 'slider-dot'; dot.dataset.index = i; pagination.appendChild(dot); graphPaginationDots.push(dot); }); graphSliderContainer.appendChild(graphSliderWrapper); if (totalGraphSlides > 1) { graphSliderContainer.insertAdjacentHTML('beforeend', '<button class="slider-button prev" aria-label="Previous Graph"><i class="fas fa-chevron-left"></i></button><button class="slider-button next" aria-label="Next Graph"><i class="fas fa-chevron-right"></i></button>'); graphSliderContainer.appendChild(pagination); } updateGraphSlider(); }
    function updateGraphSlider() { if (!graphSliderWrapper) return; graphSliderWrapper.style.transform = `translateX(-${currentGraphIndex * 100}%)`; graphPaginationDots.forEach((dot, i) => dot.classList.toggle('active', i === currentGraphIndex)); const prev = graphSliderContainer.querySelector('.prev'); const next = graphSliderContainer.querySelector('.next'); if (prev) prev.disabled = currentGraphIndex === 0; if (next) next.disabled = currentGraphIndex >= totalGraphSlides - 1; }
    function nextGraphSlide() { if (currentGraphIndex < totalGraphSlides - 1) { currentGraphIndex++; updateGraphSlider(); } }
    function prevGraphSlide() { if (currentGraphIndex > 0) { currentGraphIndex--; updateGraphSlider(); } }
    function goToGraphSlide(index) { if (index >= 0 && index < totalGraphSlides) { currentGraphIndex = index; updateGraphSlider(); } }
    function openFullscreenGraph(src) { fullscreenGraphImage.src = src; fullscreenGraphModal.classList.add('show'); }
    function closeFullscreenGraph() { fullscreenGraphModal.classList.remove('show'); }
    
    // === Start Application ===
    initApp();
});

// END OF FULL AND CORRECTED script.js