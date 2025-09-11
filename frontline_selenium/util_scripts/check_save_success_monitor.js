if (window.earlyDetection && window.earlyDetection.detected) {
    const elapsed = (window.earlyDetection.detectionTime - window.earlyDetection.startTime) / 1000;
    return { detected: true, elapsed: elapsed };
}
return { detected: false };


