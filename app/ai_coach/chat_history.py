from collections import defaultdict

# ==========================================================
# CONFIGURATION
# ==========================================================

# Maximum number of messages to retain per user.
# (User + Assistant messages)
MAX_HISTORY = 6

# ==========================================================
# IN-MEMORY STORAGE
# ==========================================================

history = defaultdict(list)

intent_memory = {}

# ==========================================================
# CHAT HISTORY
# ==========================================================


def add(user_id, role, message):

    history[user_id].append({

        "role": role,

        "sender": "You" if role == "user" else "FOCOST AI",

        "message": message

    })

    if len(history[user_id]) > MAX_HISTORY:

        history[user_id] = history[user_id][-MAX_HISTORY:]


def get(user_id):
    """
    Return entire conversation.
    """

    return history[user_id]


def conversation(user_id):
    """
    Alias for get().
    """

    return history[user_id]


def has_history(user_id):
    """
    Returns True if conversation exists.
    """

    return len(history[user_id]) > 0


def last_message(user_id):
    """
    Return latest message.
    """

    items = history[user_id]

    if items:

        return items[-1]

    return None


def last_question(user_id):
    """
    Return latest user message.
    """

    items = history[user_id]

    for item in reversed(items):

        if item["role"] == "user":

            return item["message"]

    return ""


def last_answer(user_id):
    """
    Return latest assistant message.
    """

    items = history[user_id]

    for item in reversed(items):

        if item["role"] == "assistant":

            return item["message"]

    return ""

# ==========================================================
# CONVERSATION INTENT MEMORY
# ==========================================================


def save_intent(user_id, parsed):
    """
    Save parsed conversation context.
    """

    intent_memory[user_id] = {

        "intent": parsed.get("intent"),

        "category": parsed.get("category"),

        "merchant": parsed.get("merchant"),

        "period": parsed.get("period"),

        "normalized": parsed.get("normalized"),

        "question": parsed.get("question"),

        "follow_up": parsed.get("follow_up"),

        "amount": parsed.get("amount")

    }


def get_intent(user_id):
    """
    Retrieve latest parsed intent.
    """

    return intent_memory.get(user_id, {})


def last_intent(user_id):

    return intent_memory.get(user_id, {}).get("intent")


def last_category(user_id):

    return intent_memory.get(user_id, {}).get("category")


def last_period(user_id):

    return intent_memory.get(user_id, {}).get("period")


def last_merchant(user_id):

    return intent_memory.get(user_id, {}).get("merchant")


def clear_intent(user_id):
    """
    Clear parsed intent.
    """

    intent_memory.pop(user_id, None)

# ==========================================================
# SESSION MANAGEMENT
# ==========================================================


def clear(user_id):
    """
    Clear chat history only.
    """

    history[user_id].clear()


def clear_session(user_id):
    """
    Clear everything associated with the user.
    Call this during logout.
    """

    clear(user_id)

    clear_intent(user_id)