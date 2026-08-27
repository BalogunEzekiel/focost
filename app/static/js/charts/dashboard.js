document.addEventListener("DOMContentLoaded", () => {

    const dataEl = document.getElementById("dashboardChartData");

    if (!dataEl || typeof Chart === "undefined") {
        console.warn("Dashboard chart data or Chart.js not found.");
        return;
    }

    // -----------------------------
    // Read data from HTML
    // -----------------------------

    const income = Number(dataEl.dataset.income || 0);
    const expenses = Number(dataEl.dataset.expenses || 0);

    const expenseLabels = JSON.parse(dataEl.dataset.expenseLabels || "[]");
    const expenseValues = JSON.parse(dataEl.dataset.expenseValues || "[]");

    const cashLabels = JSON.parse(dataEl.dataset.cashflowLabels || "[]");
    const cashIncome = JSON.parse(dataEl.dataset.cashflowIncome || "[]");
    const cashExpenses = JSON.parse(dataEl.dataset.cashflowExpenses || "[]");

    // =============================
    // Income vs Expense
    // =============================

    const incomeCanvas = document.getElementById("incomeExpenseChart");

    if (incomeCanvas) {

        new Chart(incomeCanvas, {

            type: "bar",

            data: {

                labels: ["Income", "Expenses"],

                datasets: [{

                    label: "Amount (₦)",

                    data: [income, expenses],

                    backgroundColor: [
                        "#198754",
                        "#dc3545"
                    ],

                    borderRadius: 8

                }]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                plugins: {

                    legend: {
                        display: false
                    }

                }

            }

        });

    }

    // =============================
    // Expense Breakdown
    // =============================

    const expenseCanvas = document.getElementById("expenseChart");

    if (expenseCanvas) {

        new Chart(expenseCanvas, {

            type: "doughnut",

            data: {

                labels: expenseLabels,

                datasets: [{

                    data: expenseValues,

                    backgroundColor: [

                        "#0d6efd",
                        "#dc3545",
                        "#ffc107",
                        "#198754",
                        "#6f42c1",
                        "#fd7e14",
                        "#20c997",
                        "#6610f2"

                    ]

                }]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                plugins: {

                    legend: {

                        position: "bottom"

                    }

                }

            }

        });

    }

    // =============================
    // Cash Flow Trend
    // =============================

    const cashCanvas = document.getElementById("cashFlowChart");

    if (cashCanvas) {

        new Chart(cashCanvas, {

            type: "line",

            data: {

                labels: cashLabels,

                datasets: [

                    {

                        label: "Income",

                        data: cashIncome,

                        borderColor: "#198754",

                        backgroundColor: "rgba(25,135,84,.15)",

                        fill: true,

                        tension: .35

                    },

                    {

                        label: "Expenses",

                        data: cashExpenses,

                        borderColor: "#dc3545",

                        backgroundColor: "rgba(220,53,69,.15)",

                        fill: true,

                        tension: .35

                    }

                ]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                interaction: {

                    mode: "index",

                    intersect: false

                },

                plugins: {

                    legend: {

                        position: "bottom"

                    }

                }

            }

        });

    }

});