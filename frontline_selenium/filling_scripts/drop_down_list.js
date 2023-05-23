var isPlanPage = {{isPlanPage}}; // used for substitution from python side
if (isPlanPage) {
    $(".form select[data-role='dropDownList']").each(function() {
        var values = [];
        $(this).find("option").each(function() {
            values.push($(this).val());
        })

        var dropDownList = $(this).data("kendoDropDownList");
        dropDownList.value(values[Math.floor(Math.random() * (values.length - 1)) + 1]);
        dropDownList.trigger("change");
    })
}else {
    //var comboBoxes = $("accelify-form-details-content kendo-combobox");
    //var comboBox = $("accelify-form-details-content kendo-combobox")[0];
    //comboBox.value = "a7a29640-2eeb-44d0-a864-3c4a5a4e8aca";
    //comboBox.dispatchEvent(new Event('change'));
    //var values = []
    //comboBoxes.each(function (index, comboBox) {
    //    console.log($(comboBox));
    //    console.log(comboBox.getElementsByTagName("option"));
    //    //var values = $(comboBox).data("kendoComboBox").dataItems().map(function (item) {
    //    //    return item.text;
    //    //});
    //    //var randomIndex = Math.floor(Math.random() * values.length);
    //    //var randomValue = values[randomIndex];
    //    //$(comboBox).data("kendoComboBox").value(randomValue);
    //});
}