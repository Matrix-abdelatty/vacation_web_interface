document.addEventListener('DOMContentLoaded', function () {
    // Initialize Flatpickr date picker
    flatpickr(".datepicker", {
        altInput: true, // Human-readable format in the input
        altFormat: "F j, Y", // Format visible to user
        dateFormat: "Y-m-d", // Format sent to server (matches WTForms format)
        minDate: "today" // Don't allow past dates (server-side validation is still primary)
    });

    // Add any other general JS here
    console.log("LeaveFlow JS Initialized");
});