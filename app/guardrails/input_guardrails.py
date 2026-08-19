BLOCKED_PATTERNS = [
    "delete my customer id",
    "delete customer",
    "remove customer",
    "drop table",
    "delete record",
    "update my details",
    "change my customer id",
    "insert record",
    "modify database",
    "show sql",
    "show query",
    "generated sql",
    "database query",
    "system prompt",
]


TOXIC_WORDS = [
    "stupid",
    "idiot",
    "dumb",
    "fool",
    "mad"
]


def input_guardrail(query: str):

    text = query.lower()

    # Internal / destructive requests
    for pattern in BLOCKED_PATTERNS:
        if pattern in text:
            return {
                "blocked": True,
                "response": (
                    "I’m sorry, I can’t help with requests involving "
                    "database operations, internal queries, or system details. "
                    "I can help you with your credit card spending, "
                    "transactions, rewards, fees, and card information."
                )
            }


    # Toxic language
    for word in TOXIC_WORDS:
        if word in text:
            return {
                "blocked": True,
                "response": (
                    "I’m here to help with your credit card questions. "
                    "Please keep the conversation respectful."
                )
            }


    return {
        "blocked": False
    }