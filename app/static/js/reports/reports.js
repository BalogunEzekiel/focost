document.addEventListener("DOMContentLoaded", () => {

    // =====================================================
    // Get JSON data from hidden div
    // =====================================================

    const reportData = document.getElementById("report-data");

    if (!reportData) {
        return;
    }

    // =====================================================
    // Income Category Chart
    // =====================================================

    const incomeLabels = JSON.parse(
        reportData.dataset.incomeLabels || "[]"
    );

    const incomeValues = JSON.parse(
        reportData.dataset.incomeValues || "[]"
    );

    const incomeCanvas = document.getElementById(
        "incomeCategoryChart"
    );

    if (incomeCanvas && incomeLabels.length > 0) {

        new Chart(incomeCanvas, {

            type: "doughnut",

            data: {

                labels: incomeLabels,

                datasets: [

                    {

                        label: "Income",

                        data: incomeValues,

                        borderWidth: 1

                    }

                ]

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

    // =====================================================
    // Expense Category Chart
    // =====================================================

    const expenseLabels = JSON.parse(
        reportData.dataset.expenseLabels || "[]"
    );

    const expenseValues = JSON.parse(
        reportData.dataset.expenseValues || "[]"
    );

    const expenseCanvas = document.getElementById(
        "expenseCategoryChart"
    );

    if (expenseCanvas && expenseLabels.length > 0) {

        new Chart(expenseCanvas, {

            type: "doughnut",

            data: {

                labels: expenseLabels,

                datasets: [

                    {

                        label: "Expenses",

                        data: expenseValues,

                        borderWidth: 1

                    }

                ]

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

    // =====================================================
    // Monthly Trend Chart
    // =====================================================

    const months = JSON.parse(
        reportData.dataset.months || "[]"
    );

    const monthlyIncome = JSON.parse(
        reportData.dataset.monthlyIncome || "[]"
    );

    const monthlyExpenses = JSON.parse(
        reportData.dataset.monthlyExpenses || "[]"
    );

    const trendCanvas = document.getElementById(
        "monthlyTrendChart"
    );

    if (trendCanvas && months.length > 0) {

        new Chart(trendCanvas, {

            type: "line",

            data: {

                labels: months,

                datasets: [

                    {

                        label: "Income",

                        data: monthlyIncome,

                        tension: 0.35,

                        fill: false

                    },

                    {

                        label: "Expenses",

                        data: monthlyExpenses,

                        tension: 0.35,

                        fill: false

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

                        position: "top"

                    }

                }

            }

        });

    }

});