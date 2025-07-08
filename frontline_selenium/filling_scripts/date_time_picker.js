$(".form input[data-role='datePicker']").each(function () {
    var datepicker = $(this).data("kendoDatePicker");
    
    // Generate realistic date: current_year-5 to current_year+1
    var currentYear = new Date().getFullYear();
    var startYear = currentYear - 5;
    var endYear = currentYear + 1;
    
    // Create date range
    var startDate = new Date(startYear, 0, 1); // January 1st of start year
    var endDate = new Date(endYear, 11, 31);   // December 31st of end year
    
    // Generate random date in range
    var timeBetween = endDate.getTime() - startDate.getTime();
    var randomTime = Math.random() * timeBetween;
    var randomDate = new Date(startDate.getTime() + randomTime);
    
    // Check if the generated date respects datepicker's min/max constraints
    var minDate = datepicker.options.min ? new Date(datepicker.options.min) : null;
    var maxDate = datepicker.options.max ? new Date(datepicker.options.max) : null;
    
    // Adjust if outside constraints
    if (minDate && randomDate < minDate) {
        randomDate = minDate;
    }
    if (maxDate && randomDate > maxDate) {
        randomDate = maxDate;
    }
    
    datepicker.value(randomDate);
    datepicker.trigger('change');
});