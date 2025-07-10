$(".form input[data-role='datePicker']").each(function () {
    var datepicker = $(this).data("kendoDatePicker");
    
    var currentYear = new Date().getFullYear();
    
    // Create date range
    var startDate = new Date(currentYear - 2, 0, 1);
    var endDate = new Date(currentYear + 1, 11, 31);
    
    // Generate random date in range
    var randomDate = new Date(startDate.getTime() + Math.random() * (endDate.getTime() - startDate.getTime()));
    
    // Check if the generated date respects datepicker's min/max constraints
    var minDate = datepicker.options.min ? new Date(datepicker.options.min) : null;
    var maxDate = datepicker.options.max ? new Date(datepicker.options.max) : null;
    
    // Adjust if outside constraints
    if (minDate && randomDate < minDate) randomDate = minDate;
    if (maxDate && randomDate > maxDate) randomDate = maxDate;
    
    datepicker.value(randomDate);
    datepicker.trigger('change');
});