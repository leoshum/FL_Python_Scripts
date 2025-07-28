/**
 * Monitors API requests detects errors and can wait for completion
 */
class NetworkMonitor {
    constructor(options = {}) {
        this.domain = options.domain || window.location.hostname.toLowerCase();
        this.apiPath = options.apiPath || '/api/';
        this.timeout = options.timeout || 10000; // 10 seconds default
        this.checkInterval = options.checkInterval || 200; // 200ms default
    }

    getApiErrors() {
        const errors = [];
        try {
            const entries = performance.getEntriesByType('resource');
            
            entries.forEach(entry => {
                const url = entry.name.toLowerCase();
                let entryDomain = '';
                
                try {
                    entryDomain = new URL(entry.name).hostname.toLowerCase();
                } catch(e) {
                    return; // Skip invalid URLs
                }
                
                const isOurDomain = entryDomain.includes(this.domain);
                const isXmlHttpRequest = entry.initiatorType === 'xmlhttprequest';
                const hasApiInUrl = url.includes(this.apiPath);
                
                if (isOurDomain && isXmlHttpRequest && hasApiInUrl) {
                    if (entry.responseStatus >= 500) {
                        errors.push({
                            url: entry.name,
                            status: entry.responseStatus,
                            type: 'http_error',
                            duration: entry.duration
                        });
                    }
                    else if (entry.responseStatus === 0 && entry.duration > 0) {
                        errors.push({
                            url: entry.name,
                            status: 0,
                            type: 'network_error',
                            duration: entry.duration
                        });
                    }
                }
            });
        } catch(e) {
            errors.push({
                url: 'Performance API',
                status: 0,
                type: 'performance_api_error',
                duration: 0,
                error: e.toString()
            });
        }
        return errors;
    }

    getPendingRequests() {
        try {
            const entries = performance.getEntriesByType('resource');
            let pending = 0;
            let total = 0;
            
            entries.forEach(entry => {
                const url = entry.name.toLowerCase();
                let entryDomain = '';
                
                try {
                    entryDomain = new URL(entry.name).hostname.toLowerCase();
                } catch(e) {
                    return;
                }
                
                const isOurDomain = entryDomain.includes(this.domain);
                const isXmlHttpRequest = entry.initiatorType === 'xmlhttprequest';
                const hasApiInUrl = url.includes(this.apiPath);
                
                if (isOurDomain && isXmlHttpRequest && hasApiInUrl) {
                    total++;
                    if (entry.responseEnd === 0) {
                        pending++;
                    }
                }
            });
            
            return { pending, total };
        } catch(e) {
            return { pending: 0, total: 0 };
        }
    }

    async waitForCompletion() {
        return new Promise((resolve) => {
            const startTime = Date.now();
            
            const checkComplete = () => {
                const { pending } = this.getPendingRequests();
                const elapsed = Date.now() - startTime;
                
                if (pending === 0) {
                    resolve({ success: true, elapsed, timedOut: false });
                } else if (elapsed > this.timeout) {
                    resolve({ success: false, elapsed, timedOut: true, pendingCount: pending });
                } else {
                    setTimeout(checkComplete, this.checkInterval);
                }
            };
            
            setTimeout(checkComplete, this.checkInterval);
        });
    }

    clear() {
        try {
            performance.clearResourceTimings();
        } catch(e) {
        }
    }

    getStatus() {
        const errors = this.getApiErrors();
        const { pending, total } = this.getPendingRequests();
        
        return {
            errors,
            pending,
            total,
            hasErrors: errors.length > 0,
            isComplete: pending === 0
        };
    }
}

// Export for use in Selenium (FIX with Chat GPT)
window.NetworkMonitor = NetworkMonitor;