from flask import Blueprint
from flask import jsonify
from flask import request

api = Blueprint(
    "api",
    __name__
)


@api.post("/ask-ai")
def ask_ai():

    question = request.json.get("question")

    answer = "AI is not connected yet."

    return jsonify({

        "answer": answer

    })