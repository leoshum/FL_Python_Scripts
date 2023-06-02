$(".form select[data-role='multiSelect']").each(function () {
    var values = [];
    $(this).find("option").each(function () {
        values.push($(this).val());
    });
    var randomIndex1 = Math.floor(Math.random() * values.length);
    var randomIndex2 = Math.floor(Math.random() * values.length);
    var iteration = 0;
    while (randomIndex2 === randomIndex1 && iteration <= 20) {
        randomIndex2 = Math.floor(Math.random() * values.length);
        iteration += 1;
    }

    if (randomIndex1 < values.length && randomIndex2 < values.length)
        $(this).data("kendoMultiSelect").value([values[randomIndex1], values[randomIndex2]]);
});