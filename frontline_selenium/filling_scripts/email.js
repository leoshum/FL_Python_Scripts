function generateEmail() {
    const firstNames = ['alexselenium', 'jordanselenium', 'nikoselenium'];
    const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
    return `${firstName.toLowerCase()}@script.com`;
}

function fillEmailFields() {
    let totalFilled = 0;

    try {
        const allElements = document.querySelectorAll('*');
        const emailLabels = Array.from(allElements).filter(el => {
            const text = (el.textContent || '').trim().toLowerCase();
            return text.includes('email') && text.length <= 10;
        });

        emailLabels.forEach(label => {
            let input = null;

            // Strategy 1: Look in same container
            let container = label.closest('div, form, section, td, tr');
            if (container) {
                input = container.querySelector('input[type="text"]:not([disabled])') ||
                       container.querySelector('input:not([type="hidden"]):not([disabled]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"])');
            }

            // Strategy 2: Look in sibling containers
            if (!input && container) {
                let sibling = container.nextElementSibling;
                let attempts = 0;
                while (sibling && !input && attempts < 3) {
                    input = sibling.querySelector('input[type="text"]:not([disabled])') ||
                           sibling.querySelector('input:not([type="hidden"]):not([disabled]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"])');
                    sibling = sibling.nextElementSibling;
                    attempts++;
                }
            }

            // Strategy 3: Look in parent's sibling containers
            if (!input && container && container.parentElement) {
                let parentSibling = container.parentElement.nextElementSibling;
                let attempts = 0;
                while (parentSibling && !input && attempts < 3) {
                    input = parentSibling.querySelector('input[type="text"]:not([disabled])') ||
                           parentSibling.querySelector('input:not([type="hidden"]):not([disabled]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"])');
                    parentSibling = parentSibling.nextElementSibling;
                    attempts++;
                }
            }

            if (input) {
                const emailValue = generateEmail();
                input.value = '';
                input.value = emailValue;
                
                ['input', 'change', 'keyup', 'blur'].forEach(eventType => {
                    input.dispatchEvent(new Event(eventType, { bubbles: true }));
                });
                
                totalFilled++;
            }
        });

        return totalFilled;

    } catch (error) {
        console.error('EMAIL SCRIPT Failed:', error);
        return 0;
    }
}

// Execute
return fillEmailFields(); 