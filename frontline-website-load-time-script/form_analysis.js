class FormLoadingMonitor {
    constructor() {
        this.startTime = Date.now();
        this.events = [];
        this.networkRequests = new Map();
        this.consoleErrors = [];
        this.observer = null;
        this.maxEvents = 100;
    }

    addEvent(type, data) {
        if (this.events.length < this.maxEvents) {
            this.events.push({
                time: Date.now() - this.startTime,
                type,
                data
            });
        }
    }

    isLoadingRelated(element) {
        const className = element.className || '';
        const id = element.id || '';
        
        // Exclude permanent UI containers
        if (className.includes('sk-activity-indicator') || 
            (className.includes('block') && !className.includes('loading'))) {
            return false;
        }
        
        const text = (className + ' ' + id).toLowerCase();
        return /loading|spinner|progress|busy|wait|overlay|mask/.test(text);
    }

    startDOMTracking() {
        this.observer = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1 && this.isLoadingRelated(node)) {
                            this.addEvent('LOADING_ADDED', {
                                tag: node.tagName,
                                classes: node.className,
                                visible: node.offsetWidth > 0 && node.offsetHeight > 0
                            });
                        }
                    });
                    
                    mutation.removedNodes.forEach(node => {
                        if (node.nodeType === 1 && this.isLoadingRelated(node)) {
                            this.addEvent('LOADING_REMOVED', {
                                tag: node.tagName,
                                classes: node.className
                            });
                        }
                    });
                }
            });
        });

        this.observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    startNetworkMonitoring() {
        // Override XMLHttpRequest
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(method, url, ...args) {
            this._monitorData = {
                method,
                url,
                startTime: Date.now()
            };
            return originalOpen.apply(this, [method, url, ...args]);
        };

        XMLHttpRequest.prototype.send = function(...args) {
            const startTime = Date.now();
            
            this.addEventListener('loadend', () => {
                const duration = Date.now() - startTime;
                const url = this._monitorData?.url || 'unknown';
                const key = `${this._monitorData?.method || 'unknown'}_${url}`;
                
                // Only keep first occurrence of duplicate requests
                if (!window.formMonitor.networkRequests.has(key)) {
                    const data = {
                        method: this._monitorData?.method || 'unknown',
                        url: url,
                        status: this.status || 0,
                        duration,
                        responseSize: this.responseText?.length || 0
                    };
                    
                    // Only record successful requests or real errors (not status 0)
                    if (this.status > 0) {
                        window.formMonitor.networkRequests.set(key, data);
                        
                        if (this.status >= 400) {
                            window.formMonitor.addEvent('NETWORK_ERROR', data);
                        }
                    }
                }
            });
            
            return originalSend.apply(this, args);
        };

        // Override fetch
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const startTime = Date.now();
            const url = args[0];
            const key = `fetch_${url}`;
            
            return originalFetch.apply(this, args)
                .then(response => {
                    const duration = Date.now() - startTime;
                    
                    // Only keep first occurrence
                    if (!window.formMonitor.networkRequests.has(key) && response.status > 0) {
                        const data = {
                            method: 'fetch',
                            url,
                            status: response.status,
                            duration,
                            responseSize: 0 // Can't get size from fetch easily
                        };
                        
                        window.formMonitor.networkRequests.set(key, data);
                        
                        if (response.status >= 400) {
                            window.formMonitor.addEvent('NETWORK_ERROR', data);
                        }
                    }
                    
                    return response;
                })
                .catch(error => {
                    if (!window.formMonitor.networkRequests.has(key)) {
                        window.formMonitor.addEvent('NETWORK_ERROR', {
                            method: 'fetch',
                            url,
                            status: 0,
                            error: error.message
                        });
                    }
                    throw error;
                });
        };
    }

    startConsoleMonitoring() {
        const originalError = console.error;
        const originalWarn = console.warn;
        
        console.error = (...args) => {
            this.consoleErrors.push({
                time: Date.now() - this.startTime,
                type: 'error',
                message: args.join(' ').substring(0, 200)
            });
            return originalError.apply(console, args);
        };

        console.warn = (...args) => {
            this.consoleErrors.push({
                time: Date.now() - this.startTime,
                type: 'warn',
                message: args.join(' ').substring(0, 200)
            });
            return originalWarn.apply(console, args);
        };

        window.addEventListener('error', (event) => {
            this.consoleErrors.push({
                time: Date.now() - this.startTime,
                type: 'js_error',
                message: event.message,
                filename: event.filename,
                line: event.lineno
            });
        });
    }

    getCurrentLoaders() {
        const loaders = [];
        document.querySelectorAll('*').forEach(el => {
            if (this.isLoadingRelated(el) && el.offsetWidth > 0 && el.offsetHeight > 0) {
                loaders.push({
                    tag: el.tagName,
                    classes: el.className,
                    size: `${el.offsetWidth}x${el.offsetHeight}`
                });
            }
        });
        return loaders;
    }

    start() {
        this.startDOMTracking();
        this.startNetworkMonitoring();
        this.startConsoleMonitoring();
        
        const initialLoaders = this.getCurrentLoaders();
        if (initialLoaders.length > 0) {
            this.addEvent('INITIAL_LOADERS', initialLoaders);
        }
    }

    stop() {
        if (this.observer) {
            this.observer.disconnect();
        }
        
        // Get better performance metrics
        const navigation = performance.getEntriesByType('navigation')[0];
        let performanceData = null;
        
        if (navigation) {
            performanceData = {
                domInteractive: Math.round(navigation.domInteractive - navigation.navigationStart),
                domContentLoaded: Math.round(navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart),
                loadComplete: Math.round(navigation.loadEventEnd - navigation.loadEventStart),
                totalLoadTime: Math.round(navigation.loadEventEnd - navigation.navigationStart)
            };
        }
        
        // Convert Map to Array for JSON serialization
        const networkArray = Array.from(this.networkRequests.values());
        
        return {
            duration: Date.now() - this.startTime,
            events: this.events,
            networkRequests: networkArray,
            consoleErrors: this.consoleErrors,
            finalLoaders: this.getCurrentLoaders(),
            performance: performanceData,
            summary: {
                totalRequests: networkArray.length,
                failedRequests: networkArray.filter(r => r.status >= 400).length,
                totalErrors: this.consoleErrors.length,
                loadingEvents: this.events.filter(e => e.type.includes('LOADING')).length,
                avgRequestDuration: networkArray.length > 0 ? 
                    Math.round(networkArray.reduce((sum, r) => sum + r.duration, 0) / networkArray.length) : 0,
                totalResponseSize: Math.round(networkArray.reduce((sum, r) => sum + r.responseSize, 0) / 1024)
            }
        };
    }
}

// Auto-initialize
if (typeof window !== 'undefined') {
    window.FormLoadingMonitor = FormLoadingMonitor;
    window.formMonitor = new FormLoadingMonitor();
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.formMonitor.start();
        });
    } else {
        window.formMonitor.start();
    }
} 