function generateZipCode() {
    const texasZipCodes = [
        '11111', '22222', '33333', '44444', '55555'
    ];
    return texasZipCodes[Math.floor(Math.random() * texasZipCodes.length)];
}

function fillZipCodeFields() {
    let filledCount = 0;
    const results = {
        filled: [],
        errors: []
    };

    // STRATEGY: find field-title with "ZIP:" text
    const allFieldTitles = document.querySelectorAll('.field-title');
    const zipKeywords = ['zip', 'postal', 'zipcode', 'zip code'];

    allFieldTitles.forEach((titleElement, index) => {
        const titleText = (titleElement.textContent || titleElement.innerText || '').trim().toLowerCase();
        const isZipTitle = zipKeywords.some(keyword => titleText.includes(keyword.toLocaleLowerCase()));

        if (isZipTitle) {
            let container = titleElement.parentElement;
            let input = null;

            // Look in current container and parent containers
            for (let i = 0; i < 5 && container; i++) {
                // Look for input in this container
                const inputs = container.querySelectorAll('input[type="text"], input:not([type]), input.k-input-inner');

                if (inputs.length > 0) {
                    for (let inputEl of inputs) {
                        if (!inputEl.disabled && inputEl.offsetParent && inputEl.style.display !== 'none') {
                            input = inputEl;
                            break;
                        }
                    }
                    if (input) break;
                }
                container = container.parentElement;
            }

            if (input) {
                try {
                    const zipCode = generateZipCode();
                    input.value = zipCode;
                    input.focus();

                    // Comprehensive event triggering
                    const events = ['input', 'change', 'blur', 'keyup', 'paste', 'focusout'];
                    events.forEach(eventType => {
                        try {
                            const event = new Event(eventType, { bubbles: true, cancelable: true });
                            input.dispatchEvent(event);
                        } catch (e) {
                        }
                    });

                    // Additional Kendo-specific events
                    if (input.className.includes('k-input') || input.className.includes('k-textbox')) {
                        input.dispatchEvent(new Event('keypress', { bubbles: true }));
                        input.dispatchEvent(new Event('valueChange', { bubbles: true }));
                    }

                    results.filled.push({
                        title: titleText,
                        input: input.id || 'no-id',
                        zipCode: zipCode,
                        className: input.className
                    });
                    filledCount++;

                } catch (error) {
                    results.errors.push({
                        title: titleText,
                        input: input.id || 'no-id',
                        error: error.message
                    });
                }
            } else {
                results.errors.push({
                    title: titleText,
                    error: 'no_input_found'
                });
            }
        }
    });

    return filledCount;
}

// Execute
return fillZipCodeFields(); 