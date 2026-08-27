console.log("FOCOST Loaded");

document.addEventListener("DOMContentLoaded", () => {

    // =========================================================
    // Transaction Filters
    // =========================================================

    initTransactionFilters();

    // =========================================================
    // Mobile Sidebar
    // =========================================================

    initSidebar();

    // =========================================================
    // Mobile Search
    // =========================================================

    initMobileSearch();

});


/* ============================================================
   Transaction Filters
============================================================ */

function initTransactionFilters() {

    const form =
        document.getElementById("transactionFilterForm") ||
        document.querySelector("form");

    if (!form) return;

    const filterIds = [
        "transactionType",
        "transactionCategory",
        "transactionPeriod"
    ];

    filterIds.forEach(id => {

        const field = document.getElementById(id);

        if (!field) return;

        field.addEventListener("change", () => form.submit());

    });

    const search = document.getElementById("transactionSearch");

    if (!search) return;

    let timer;

    search.addEventListener("input", () => {

        clearTimeout(timer);

        timer = setTimeout(() => {

            form.submit();

        }, 600);

    });

    search.addEventListener("keydown", e => {

        if (e.key === "Enter") {

            e.preventDefault();

            form.submit();

        }

    });

}


/* ============================================================
   Sidebar
============================================================ */

function initSidebar() {

    const sidebar = document.getElementById("sidebar");
    const toggle = document.getElementById("sidebarToggle");

    if (!sidebar || !toggle) return;

    const closeSidebar = () => {

        sidebar.classList.remove("show");

    };

    const openSidebar = () => {

        sidebar.classList.add("show");

    };

    const toggleSidebar = () => {

        sidebar.classList.toggle("show");

    };

    toggle.addEventListener("click", e => {

        e.stopPropagation();

        toggleSidebar();

    });

    document.addEventListener("click", e => {

        if (
            window.innerWidth < 992 &&
            !sidebar.contains(e.target) &&
            !toggle.contains(e.target)
        ) {

            closeSidebar();

        }

    });

    window.addEventListener("resize", () => {

        if (window.innerWidth >= 992) {

            closeSidebar();

        }

    });

    sidebar.querySelectorAll("a").forEach(link => {

        link.addEventListener("click", () => {

            if (window.innerWidth < 992) {

                closeSidebar();

            }

        });

    });

    sidebar.open = openSidebar;

}


/* ============================================================
   Mobile Search
============================================================ */

function initMobileSearch() {

    const button = document.getElementById("mobileSearchButton");
    const sidebar = document.getElementById("sidebar");

    if (!button || !sidebar) return;

    button.addEventListener("click", () => {

        if (!sidebar.classList.contains("show")) {

            sidebar.open?.();

        }

        setTimeout(() => {

            const searchInput = sidebar.querySelector(
                "input[type='search'], input[type='text']"
            );

            searchInput?.focus();

        }, 250);

    });

}