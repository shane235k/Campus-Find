/**
 * Campus Lost & Found Hub — Global JavaScript
 * Phase 0 Technical Foundation
 */

document.addEventListener("DOMContentLoaded", function () {
  console.log("Campus Lost & Found Hub — Initialized (Phase 0 Foundation)");

  // Interactive handler for visual search bar placeholder
  const searchForm = document.getElementById("heroSearchForm");
  if (searchForm) {
    searchForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const queryInput = document.getElementById("heroSearchInput");
      const query = queryInput ? queryInput.value.trim() : "";
      
      const feedbackModal = document.getElementById("searchPlaceholderNotice");
      if (feedbackModal) {
        feedbackModal.classList.remove("d-none");
      } else {
        alert(
          query
            ? `Searching for "${query}" is scheduled for Phase 2 (Lost & Found Core)!`
            : "Search and filter functionality will be active in Phase 2."
        );
      }
    });
  }

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
