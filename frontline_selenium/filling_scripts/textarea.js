var isPlanPage = {{isPlanPage}}; // used for substitution from python side
if (isPlanPage) {
    $('.form textarea').each(function () {
        var text = {{text}};
        if ($(this).attr('maxlength')) {
            text = text.slice(0, $(this).attr('maxlength') - 1);
        }
        $(this).val(text);
        $(this).trigger('change');
    });
} else {
    // For non-plan pages, handle textareas differently if needed
    console.log("Non-plan page detected, textarea handling skipped");
}