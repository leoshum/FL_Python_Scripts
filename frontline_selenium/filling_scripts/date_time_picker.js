var isPlanPage = {{isPlanPage}}; // used for substitution from python side
if (isPlanPage) {
    $(".form input[data-role='datePicker']").each(function() {
        var datepicker = $(this).data("kendoDatePicker");
        var minDate = new Date(datepicker.options.min).getTime();
        var maxDate = new Date(datepicker.options.max).getTime();
        var randomTimestamp = minDate + Math.random() * (maxDate - minDate);
        datepicker.value(new Date(randomTimestamp));
        datepicker.trigger('change');
    })
}else {

}