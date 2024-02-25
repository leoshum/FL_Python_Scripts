$(".form input[data-role='datePicker']").each(function () {
    var datepicker = $(this).data("kendoDatePicker");
    var minDate = new Date(datepicker.options.min).getTime();
    var maxDate = new Date(datepicker.options.max).getTime();

    var currentDate = new Date().getTime();

    if (currentDate >= minDate && currentDate <= maxDate) {
        var randomOffset = Math.random() * (maxDate - currentDate);
        var randomTimestamp = currentDate + randomOffset;
    } else {
        var randomTimestamp = minDate + Math.random() * (maxDate - minDate);
    }
    datepicker.value(new Date(randomTimestamp));
    datepicker.trigger('change');
});