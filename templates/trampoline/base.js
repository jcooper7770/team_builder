// JavaScript code to handle notification count updates and displaying notifications
document.addEventListener("DOMContentLoaded", function () {
    // Function to handle displaying notifications dropdown
    function displayNotifications() {
        // Toggle dropdown visibility
        var dropdown = document.querySelector('.notifications-dropdown');
        if (dropdown.children.length > 0) {
            dropdown.classList.toggle('show');
        }
    }

    // Function to reset the notification count
    function resetNotificationCount() {
        // Reset the notification count to 0
        var notificationBadge = document.querySelector('.notification-badge');
        notificationBadge.innerText = '0';

        // Get the notifications dropdown
        var dropdown = document.querySelector('.notifications-dropdown');
        if (dropdown.children.length > 0) {
            // Remove all child elements
            dropdown.innerHTML = '';

            // Remove notifications for user
            $.ajax({
                type: 'POST',
                url: "/logger/notification/clear",
                contentType: 'application/json',
                success: function (data) {
                    console.log("removed notifications for user")
                }
            });

        }
    }

    {% if user %}
    // Event listener for clicking on the notification badge
    var notificationBadge = document.querySelector('.notification-badge');
    notificationBadge.addEventListener('click', function (event) {
        // Prevent the default behavior of the link
        event.preventDefault();
        // Call function to display notifications
        displayNotifications();

        // Get the notifications dropdown
        var dropdown = document.querySelector('.notifications-dropdown');
        if (!dropdown.classList.contains("show")) {
            // Call function to reset notification count
            resetNotificationCount();
        }

    });
    {% endif %}

    // Function to add a notification to the dropdown
    function addNotification(notificationText) {
        // Increment the notification count
        var count = parseInt(notificationBadge.innerText);
        notificationBadge.innerText = count + 1;

        // Get the notifications dropdown
        var dropdown = document.querySelector('.notifications-dropdown');

        // Create a new notification item
        var notificationItem = document.createElement('a');
        notificationItem.classList.add('dropdown-item');
        notificationItem.classList.add('notification');
        notificationItem.href = '#'; // You can add a link if needed
        notificationItem.textContent = notificationText;

        // Append the new notification item to the dropdown
        dropdown.appendChild(notificationItem);
    }

    function loadUserNotifications() {
        $.ajax({
            type: 'GET',
            url: "/logger/notifications",
            contentType: 'application/json',
            success: function (data) {
                for (var noti of data.notifications) {
                    addNotification(noti.message);
                }
                for (var request of data.requests) {
                    addNotification(`New coach request from ${request}`);
                }
                if (data.messages.length > 0) {
                    addNotification("New messages in your Settings");
                }
            }
        });

    }

    {% if user %}
    // Simulate receiving new notifications every 10 seconds (for demonstration purposes)
    /*
    setInterval(function () {
        loadUserNotifications();
    }, 10000);
    */
    // Just check for notifications on page load
    loadUserNotifications();
    {% endif %}
});