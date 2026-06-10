/**
 * MailPulse Front-End Behavior Scripts
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // --- Mobile Sidebar Toggle ---
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebarClose = document.getElementById('sidebar-close');
    
    // Create overlay element dynamically
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.add('show');
            overlay.classList.add('show');
        });
    }

    function hideSidebar() {
        if (sidebar) {
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
        }
    }

    if (sidebarClose) {
        sidebarClose.addEventListener('click', hideSidebar);
    }
    overlay.addEventListener('click', hideSidebar);


    // --- Automatic Alert Dismissal ---
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.6s ease';
                setTimeout(() => alert.remove(), 600);
            }
        }, 5000); // Fade out after 5 seconds
    });


    // Note: Quill editor is now initialized directly in compose.html template.

});
