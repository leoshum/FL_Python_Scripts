function generateEmail() {
    const firstNames = ['alexselenium', 'jordanselenium', 'nikoselenium'];
    const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
    return `${firstName.toLowerCase()}.${lastName.toLowerCase()}@script.com`;
}

function fillEmailFields() {
    let totalFilled = 0;

    try {
        const allElements = document.querySelectorAll('*');
        const emailTitles = [];

        allElements.forEach(element => {
            const text = element.textContent || element.innerText || '';
            if (text.toLowerCase().includes('email') && text.length < 20) { // Short text likely to be a label
                emailTitles.push(element);
            }
        });

        emailTitles.forEach((titleElement, index) => {
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
                input.value = generateEmail();
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
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