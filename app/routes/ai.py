from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user

from app.services.ai_service import AIService
from app.services.ai_usage_service import AIUsageService
from app.subscriptions.decorators import subscription_required


ai_bp = Blueprint(
    "ai",
    __name__,
    url_prefix="/ai"
)


# ==========================================================
# AI COACH PAGE
# ==========================================================

@ai_bp.get("/")
@login_required
def coach():

    return render_template(
        "ai/index.html"
    )


# ==========================================================
# AI CHAT
# ==========================================================

@ai_bp.post("/chat")
@login_required
@subscription_required("ai_chat")
def chat():

    data = request.get_json(
        silent=True
    ) or {}

    message = str(
        data.get("message", "")
    ).strip()

    if not message:

        return jsonify({
            "success": False,
            "message": "Please enter a message."
        }), 400

    result = AIService.chat(
        current_user.id,
        message
    )

    if result.get("success"):

        status = 200

    elif result.get("code") == "AI_USAGE_LIMIT":

        status = 429

    else:

        status = 503

    return jsonify(result), status


# ==========================================================
# AI USAGE
# ==========================================================

@ai_bp.get("/usage")
@login_required
def usage():

    return jsonify({
        "success": True,
        "usage": AIUsageService.monthly(
            current_user.id
        )
    })


# ==========================================================
# AI FORECAST
# ==========================================================

@ai_bp.get("/forecast")
@login_required
def forecast():

    from app.services.dashboard_service import DashboardService

    return jsonify({
        "success": True,

        "forecast":
            DashboardService.advanced_forecast(
                current_user.id
            ),

        "category_forecasts":
            DashboardService.category_forecasts(
                current_user.id
            ),

        "anomalies":
            DashboardService.anomaly_analysis(
                current_user.id
            )
    })


# ==========================================================
# CLEAR CURRENT AI SESSION
# ==========================================================

@ai_bp.post("/clear")
@login_required
def clear_chat():

    AIService.clear_session_history()

    return jsonify({
        "success": True
    })


# ==========================================================
# CURRENT SESSION HISTORY
# ==========================================================

@ai_bp.get("/history")
@login_required
def history():
    messages = session.get(
        "ai_history",
        []
    )

    return jsonify({
        "first_name": current_user.first_name,
        "messages": [
            {
                "sender": (
                    "You"
                    if item.get("role") == "user"
                    else "FOCOST AI"
                ),
                "message": item.get(
                    "content",
                    ""
                ),
                "role": item.get(
                    "role"
                ),
            }
            for item in messages
            if isinstance(item, dict)
        ],
    })