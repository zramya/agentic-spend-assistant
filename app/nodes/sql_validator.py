FORBIDDEN_SQL = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "merge",
    "grant",
    "revoke"
]


def validate_sql(sql: str) -> bool:

    sql = sql.lower().strip()

    # allow only read queries
    if not sql.startswith(("select", "with")):
        return False

    # block modification queries
    for keyword in FORBIDDEN_SQL:
        if keyword in sql:
            return False

    return True