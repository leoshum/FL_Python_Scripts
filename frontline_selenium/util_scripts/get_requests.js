var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {};
var network = performance.getEntriesByType("resource").filter(function(item) {
    return item.initiatorType == "xmlhttprequest";
});
var requests = network.map(function (entry) {
    return {
        url: entry.name,
        status: entry.responseStatus ? entry.responseStatus : 0
    };
});
return requests;