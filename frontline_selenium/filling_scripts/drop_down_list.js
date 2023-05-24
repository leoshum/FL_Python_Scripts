$(".form select[data-role='dropDownList']").each(function () {
    var values = [];
    $(this).find("option").each(function () {
        values.push($(this).val());
    })

    var dropDownList = $(this).data("kendoDropDownList");
    dropDownList.value(values[Math.floor(Math.random() * (values.length - 1)) + 1]);
    dropDownList.trigger("change");
})