console.log("Notifications JS Started");

document.addEventListener("DOMContentLoaded", () => {

    const badge = document.getElementById("notificationBadge");
    const headerBadge = document.getElementById("notificationHeaderBadge");
    const notificationList = document.getElementById("notificationList");

    //----------------------------------------------------------
    // CSRF Token (optional if using Flask-WTF)
    //----------------------------------------------------------

    const csrfToken =
        document.querySelector('meta[name="csrf-token"]')?.content || "";

    //----------------------------------------------------------
    // Update Notification Count
    //----------------------------------------------------------

    function updateBadge(count) {

        if (badge) {

            if (count > 0) {

                badge.textContent = count;
                badge.classList.remove("d-none");

            } else {

                badge.classList.add("d-none");

            }

        }

        if (headerBadge) {

            if (count > 0) {

                headerBadge.textContent = count;
                headerBadge.classList.remove("d-none");

            } else {

                headerBadge.classList.add("d-none");

            }

        }

    }

    //----------------------------------------------------------
    // Generic POST Helper
    //----------------------------------------------------------

    async function post(url) {

        const response = await fetch(url, {

            method: "POST",

            headers: {

                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json",

                ...(csrfToken && {
                    "X-CSRFToken": csrfToken
                })

            }

        });

        return await response.json();

    }

    //----------------------------------------------------------
    // MARK ONE READ
    //----------------------------------------------------------

    document.addEventListener("click", async function (e) {

        const btn = e.target.closest(".mark-read");

        if (!btn) return;

        e.preventDefault();

        const id = btn.dataset.id;

        try {

            const data = await post(`/notifications/read/${id}`);

            if (!data.success) return;

            updateBadge(data.notification_count);

            const item = btn.closest(".notification-item");

            if (item) {

                item.classList.remove("bg-light");

                const newBadge = item.querySelector(".badge");

                if (newBadge)
                    newBadge.remove();

            }

            btn.remove();

        }

        catch (err) {

            console.error(err);

        }

    });

    //----------------------------------------------------------
    // MARK ALL READ
    //----------------------------------------------------------

    const markAllBtn = document.getElementById("markAllNotifications");

    if (markAllBtn) {

        markAllBtn.addEventListener("click", async function () {

            try {

                const data = await post("/notifications/mark-all-read");

                if (!data.success) return;

                updateBadge(0);

                document.querySelectorAll(".notification-item")
                    .forEach(item => {

                        item.classList.remove("bg-light");

                        const badge = item.querySelector(".badge");

                        if (badge)
                            badge.remove();

                    });

                document.querySelectorAll(".mark-read")
                    .forEach(btn => btn.remove());

            }

            catch (err) {

                console.error(err);

            }

        });

    }

    //----------------------------------------------------------
    // DELETE ONE
    //----------------------------------------------------------

    document.addEventListener("click", async function (e) {

        const btn = e.target.closest(".delete-notification");

        if (!btn) return;

        e.preventDefault();

        if (!confirm("Delete this notification?"))
            return;

        const id = btn.dataset.id;

        try {

            const data = await post(`/notifications/delete/${id}`);

            if (!data.success) return;

            updateBadge(data.notification_count);

            const item = btn.closest(".notification-item");

            if (item) {

                const divider = item.nextElementSibling;

                item.remove();

                if (
                    divider &&
                    divider.classList.contains("dropdown-divider")
                ) {
                    divider.remove();
                }

            }

            if (
                notificationList &&
                notificationList.children.length === 0
            ) {

                notificationList.innerHTML = `
                    <div class="text-center py-4 text-muted">
                        <i class="bi bi-bell-slash fs-1"></i>
                        <div class="mt-2">No notifications</div>
                    </div>
                `;

            }

        }

        catch (err) {

            console.error(err);

        }

    });

    //----------------------------------------------------------
    // DELETE ALL
    //----------------------------------------------------------

    const deleteAllBtn = document.getElementById("deleteAllNotifications");

    if (deleteAllBtn) {

        deleteAllBtn.addEventListener("click", async function () {

            if (!confirm("Delete ALL notifications?"))
                return;

            try {

                const data = await post("/notifications/delete-all");

                if (!data.success) return;

                updateBadge(0);

                if (notificationList) {

                    notificationList.innerHTML = `
                        <div class="text-center py-4 text-muted">
                            <i class="bi bi-bell-slash fs-1"></i>
                            <div class="fw-semibold mt-2">
                                No notifications
                            </div>
                            <small>
                                You're all caught up.
                            </small>
                        </div>
                    `;

                }

            }

            catch (err) {

                console.error(err);

            }

        });

    }

});