// Phone Field Filler - Simple approach
// Find phone title, find nearby input, fill it

console.log("Starting phone field detection and filling...");

function generatePhoneNumber() {
    const areaCodes = ['111', '222', '333', '444', '555', '666', '777', '888', '999'];
    const areaCode = areaCodes[Math.floor(Math.random() * areaCodes.length)];
    const exchange = Math.floor(Math.random() * 900) + 100;
    const number = Math.floor(Math.random() * 9000) + 1000;

    return `(${areaCode}) ${exchange}-${number}`;
}

function isTextInput(input) {
    if (!input || input.tagName !== 'INPUT') return false;
    
    const type = (input.type || '').toLowerCase();
    
    // Exclude checkbox, radio, hidden, submit, button types
    const excludedTypes = ['checkbox', 'radio', 'hidden', 'submit', 'button', 'reset', 'file', 'image'];
    
    return !excludedTypes.includes(type) && !input.disabled;
}

function fillPhoneFields() {
    let totalFilled = 0;

    try {
        const allElements = document.querySelectorAll('*');
        const phoneTitles = [];

        allElements.forEach(element => {
            const text = element.textContent || element.innerText || '';
            const lowercaseText = text.toLowerCase();
            
            // Look for phone-related text
            if ((lowercaseText.includes('phone') || lowercaseText.includes('fax')) && text.length < 50) {
                phoneTitles.push(element);
            }
        });

        phoneTitles.forEach((titleElement, index) => {
            let input = null;

            // Strategy 1: Look in same container for text inputs only
            const container = titleElement.closest('div, section, form, td, tr');
            if (container) {
                const inputs = container.querySelectorAll('input:not([disabled]):not([type="hidden"])');
                for (let inp of inputs) {
                    if (isTextInput(inp)) {
                        input = inp;
                        break;
                    }
                }
            }

            // Strategy 2: Look in next siblings for text inputs only
            if (!input) {
                let sibling = titleElement.nextElementSibling;
                let attempts = 0;
                while (sibling && !input && attempts < 3) {
                    if (isTextInput(sibling)) {
                        input = sibling;
                    } else {
                        const inputs = sibling.querySelectorAll('input:not([disabled]):not([type="hidden"])');
                        for (let inp of inputs) {
                            if (isTextInput(inp)) {
                                input = inp;
                                break;
                            }
                        }
                    }
                    sibling = sibling.nextElementSibling;
                    attempts++;
                }
            }

            // Strategy 3: Look in parent's next siblings for text inputs only
            if (!input) {
                let parentSibling = titleElement.parentElement?.nextElementSibling;
                let attempts = 0;
                while (parentSibling && !input && attempts < 3) {
                    const inputs = parentSibling.querySelectorAll('input:not([disabled]):not([type="hidden"])');
                    for (let inp of inputs) {
                        if (isTextInput(inp)) {
                            input = inp;
                            break;
                        }
                    }
                    parentSibling = parentSibling.nextElementSibling;
                    attempts++;
                }
            }

            if (input) {
                input.value = generatePhoneNumber();
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                totalFilled++;
            }
        });
        
        return totalFilled;

    } catch (error) {
        console.error('PHONE SCRIPT Failed:', error);
        return 0;
    }
}

// Execute
return fillPhoneFields(); 