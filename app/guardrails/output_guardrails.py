def output_guardrail(answer: str):

    if not answer:
        return answer

    blocked_patterns = [
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "DROP ",
        "ALTER ",
        "CREATE TABLE",
        "SYSTEM PROMPT",
        "INTERNAL PROMPT",
        "IMPLEMENTATION DETAILS",
    ]

    upper_answer = answer.upper()

    for pattern in blocked_patterns:
        if pattern in upper_answer:
            return (
                "I can help you with your credit card spending, "
                "transactions, rewards, fees, benefits, and card-related "
                "information, but I cannot provide internal technical details."
            )

    return answer