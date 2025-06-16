// Enhanced network monitoring with pending requests detection
var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {};

// Get all network entries
var allEntries = performance.getEntriesByType ? performance.getEntriesByType("resource") : [];

// Filter for AJAX/API requests
var networkRequests = allEntries.filter(function(entry) {
    return entry.initiatorType === "xmlhttprequest" || 
           entry.initiatorType === "fetch" ||
           entry.name.includes('/api/');
});

// Map to structured format with pending detection (backward compatible)
var requests = networkRequests.map(function(entry) {
    var isPending = entry.responseEnd === 0 && entry.startTime > 0;
    
    return {
        url: entry.name,
        status: entry.responseStatus || (isPending ? 'pending' : 0),
        isPending: isPending,
        isApiRequest: entry.name.includes('/api/'),
        duration: isPending ? (Date.now() - entry.startTime) : (entry.responseEnd - entry.startTime),
        startTime: entry.startTime
    };
});

// Return the array for backward compatibility
return requests;