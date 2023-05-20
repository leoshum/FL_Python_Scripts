var isPlanPage = {{isPlanPage}}; // used for substitution from python side
if (isPlanPage) {
    $("input[type='checkbox']").each(function() { 
        $(this).prop('checked', true);
    });
}else {
    for (var i = 0; i < $("input[type='checkbox']").length; ++i) {
        $("input[type='checkbox']")[i].click();
    }
}