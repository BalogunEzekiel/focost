import traceback

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify
)

from flask_login import (
    login_required,
    current_user
)

from app.services.ai_service import AIService
from flask import session

ai_bp = Blueprint(
    "ai",
    __name__,
    url_prefix="/ai"
)


@ai_bp.route("/")
@login_required
def coach():
    """
    Render the AI Financial Coach page.
    """
    return render_template("ai/index.html")


@ai_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    """
    Handle AI chat requests.
    """

    try:

        data = request.get_json(silent=True) or {}

        message = data.get("message", "").strip()

        if not message:

            return jsonify({

                "success": False,

                "message": "Please enter a message."

            }), 400

        result = AIService.chat(
            user_id=current_user.id,
            message=message
        )

        return jsonify(result)

    except Exception as e:

        traceback.print_exc()

        return jsonify({

            "success": False,

            "message": str(e)

        }), 500




@ai_bp.route("/clear", methods=["POST"])
@login_required
def clear_chat():

    session.pop("ai_history", None)

    return jsonify({

        "success": True

    })

@ai_bp.route("/history")
@login_required
def history():

    history = session.get("ai_history", [])

    messages = []

    for item in history:

        role = item.get("role", "assistant")
        content = item.get("content", "")

        messages.append({
            "sender": "You" if role == "user" else "FOCOST AI",
            "message": content,
            "role": role
        })

    return jsonify({

        "first_name": current_user.first_name,

        "messages": messages

    })