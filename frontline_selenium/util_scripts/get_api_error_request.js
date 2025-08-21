const errors = [];
const processedUrls = new Set(); // Add deduplication
const currentDomain = window.location.hostname.toLowerCase();

try {
    const entries = performance.getEntriesByType('resource');

    for (const entry of entries) {
        let entryDomain = '';

        // Safe URL parsing
        try {
            entryDomain = new URL(entry.name).hostname.toLowerCase();
        } catch (e) {
            continue; // Skip malformed URLs
        }

        // Exact domain matching instead of includes()
        if (entryDomain !== currentDomain) continue;
        if (entry.initiatorType !== 'xmlhttprequest') continue;
        if (!entry.name.includes('/api/')) continue;

        // Create unique identifier for deduplication
        const errorKey = `${entry.name}:${entry.responseStatus}`;
        if (processedUrls.has(errorKey)) continue;

        const isError = entry.responseStatus >= 500 ||
            (entry.responseStatus === 0 && entry.responseEnd > 0);

        if (isError) {
            const isCancelled = entry.responseStart === 0 ||
                entry.duration < 1 ||
                entry.transferSize === 0;

            if (isCancelled) continue;

            processedUrls.add(errorKey);
            errors.push({
                url: entry.name,
                status: entry.responseStatus,
                type: entry.responseStatus >= 400 ? 'http_error' : 'network_error',
                duration: entry.duration || 0,
                transferSize: entry.transferSize || 0
            });
        }
    }
} catch (e) {
    console.error('Performance API error:', e);
    return { errors: [], error: e.message };
}

return errors;