window.earlyDetection = {
    startTime: Date.now(),
    detected: false,
    detectionTime: null
};

const checkSuccess = () => {
    const successTexts = [
        'form has been updated successfully',
        'has been updated successfully', 
        'successfully updated',
        'saved successfully'
    ];
    
    const pageText = (document.documentElement.textContent ||
        document.documentElement.innerText || '').toLowerCase();
    
    if (!window.earlyDetection.detected && 
        successTexts.some(text => pageText.includes(text))) {
        window.earlyDetection.detected = true;
        window.earlyDetection.detectionTime = Date.now();
    }
};

window.earlyDetection.intervalId = setInterval(checkSuccess, 50);


