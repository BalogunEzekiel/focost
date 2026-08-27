from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.ai_coach.services import AICoachService
from app.ai_coach.chat_history import get

ai_coach_bp = Blueprint(
    "ai_coach",
    __name__,
    url_prefix="/ai-coach"
)


@ai_coach_bp.route("/")
@login_required
def index():
    """
    Optional standalone AI Coach page.
    The floating widget works on every page.
    """
    return render_template("ai_coach/index.html")


@ai_coach_bp.route("/chat", methods=["POST"])
@login_required
def chat():

    data = request.get_json() or {}

    question = data.get("message", "").strip()

    if not question:
        return jsonify({
            "reply": "Please enter a message."
        }), 400

    reply = AICoachService.get_response(
        user=current_user,
        question=question
    )

    return jsonify({
        "reply": reply
    })


@ai_coach_bp.route("/history")
@login_required
def history():

    messages = get(current_user.id)

    return jsonify({

        "first_name": current_user.first_name,

        "messages": messages

    })