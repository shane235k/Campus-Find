/**
 * Campus Lost & Found Hub — Global JavaScript
 * Pure Green & White Theme
 */

document.addEventListener("DOMContentLoaded", function () {
  // Auto-dismiss alerts after 5 seconds
  const autoAlerts = document.querySelectorAll(".alert-dismissible");
  autoAlerts.forEach(function (alertEl) {
    setTimeout(function () {
      try {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
        bsAlert.close();
      } catch (err) {
        // Bootstrap alert instance might not be available
      }
    }, 5000);
  });
});
