alerts = []

for budget in budgets:

    if budget.percentage_used >= 100:

        alerts.append({
            "level": "danger",
            "message": f"{budget.category} budget exceeded."
        })

    elif budget.percentage_used >= 90:

        alerts.append({
            "level": "warning",
            "message": f"{budget.category} budget is almost exhausted."
        })

    elif budget.percentage_used >= 75:

        alerts.append({
            "level": "info",
            "message": f"{budget.category} budget has reached 75%."
        })