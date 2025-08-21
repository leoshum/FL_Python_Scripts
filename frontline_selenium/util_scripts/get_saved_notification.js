const successTexts = [
    'form has been updated successfully',
    'has been updated successfully',
    'successfully updated',
    'saved successfully'
];

const pageText = (document.documentElement.textContent ||
    document.documentElement.innerText || '').toLowerCase();

return successTexts.some(text => pageText.includes(text));