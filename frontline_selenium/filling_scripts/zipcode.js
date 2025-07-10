function generateZipCode() {
    const texasZipCodes = [
        '11111', '22222', '33333', '44444', '55555'
    ];
    return texasZipCodes[Math.floor(Math.random() * texasZipCodes.length)];
}

function fillZipCodeFields() {
    const zipKeywords = ['zip', 'postal', 'zipcode', 'zip code'];
    let filledCount = 0;

    // Find all text nodes and elements containing zip keywords
    const allElements = document.querySelectorAll('*');
    
    for (const element of allElements) {
        const text = (element.textContent || element.innerText || '').trim().toLowerCase();
        
        // Skip if no text or text is too long (avoid content areas)
        if (!text || text.length > 25) continue;
        
        // Check if element contains zip keyword
        const hasZipKeyword = zipKeywords.some(keyword => text.includes(keyword));
        if (!hasZipKeyword) continue;
        
        // Find nearest input field
        const input = findNearestInput(element);
        if (!input) continue;
        
        // Fill the input
        const zipCode = generateZipCode();
        input.value = zipCode;
        input.focus();
        
        // Trigger events
        const events = ['input', 'change', 'blur', 'keyup', 'paste', 'focusout'];
        events.forEach(eventType => {
            try {
                input.dispatchEvent(new Event(eventType, { bubbles: true, cancelable: true }));
            } catch (e) {}
        });
        
        // Kendo-specific events
        if (input.className.includes('k-')) {
            try {
                input.dispatchEvent(new Event('keypress', { bubbles: true }));
                input.dispatchEvent(new Event('valueChange', { bubbles: true }));
            } catch (e) {}
        }
        
        filledCount++;
    }
    
    return filledCount;
}

function findNearestInput(element) {
    const searchStrategies = [
        // 1. Look in next sibling (any depth)
        () => element.nextElementSibling ? findInputInElement(element.nextElementSibling) : null,
        // 2. Look in parent's next sibling (any depth)
        () => element.parentElement?.nextElementSibling ? findInputInElement(element.parentElement.nextElementSibling) : null,
        // 3. Look in same parent container (any depth)
        () => element.parentElement ? findInputInElement(element.parentElement) : null,
        // 4. Look in grandparent container (any depth)
        () => element.parentElement?.parentElement ? findInputInElement(element.parentElement.parentElement) : null
    ];
    
    for (const strategy of searchStrategies) {
        const input = strategy();
        if (input) return input;
    }
    
    return null;
}

function findInputInElement(container) {
    if (!container) 
        return null;

    const inputs = container.querySelectorAll('input');

    for (const input of inputs) {
        // Check if it's a text input
        const isTextInput = !input.type || input.type === 'text' || input.classList.contains('k-textbox');
        
        if (isTextInput && 
            !input.disabled && 
            input.offsetParent !== null && 
            input.style.display !== 'none' &&
            input.type !== 'hidden') {
            return input;
        }
    }
    
    return null;
}

// Execute
return fillZipCodeFields(); 