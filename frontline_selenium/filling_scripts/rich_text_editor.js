var isPlanPage = {{isPlanPage}}; // used for substitution from python side
if (isPlanPage) {
    $(".k-editor[data-role='text-editor']").each(function() { 
        var editor = $(this).data('kendoEditor');
        editor.value({{text}});
        editor.trigger('change');
    });
}else {

}