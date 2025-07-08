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

function fillPhoneFields() {
    let totalFilled = 0;

    try {
        const allElements = document.querySelectorAll('*');
        const phoneTitles = [];

        allElements.forEach(element => {
            const text = element.textContent || element.innerText || '';
            if ((text.toLowerCase().includes('phone') || text.toLowerCase().includes('fax')) && text.length < 20) {
                phoneTitles.push(element);
            }
        });

        phoneTitles.forEach((titleElement, index) => {
            let input = null;

            // Strategy 1: Look in same container
            const container = titleElement.closest('div, section, form, td, tr');
            if (container) {
                input = container.querySelector('input:not([disabled]):not([type="hidden"])');
            }

            // Strategy 2: Look in next siblings
            if (!input) {
                let sibling = titleElement.nextElementSibling;
                let attempts = 0;
                while (sibling && !input && attempts < 3) {
                    if (sibling.tagName === 'INPUT' && !sibling.disabled) {
                        input = sibling;
                    } else {
                        input = sibling.querySelector('input:not([disabled]):not([type="hidden"])');
                    }
                    sibling = sibling.nextElementSibling;
                    attempts++;
                }
            }

            // Strategy 3: Look in parent's next siblings
            if (!input) {
                let parentSibling = titleElement.parentElement?.nextElementSibling;
                let attempts = 0;
                while (parentSibling && !input && attempts < 3) {
                    input = parentSibling.querySelector('input:not([disabled]):not([type="hidden"])');
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