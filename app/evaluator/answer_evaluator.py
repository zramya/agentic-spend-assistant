from app.core.llm import _get_llm
from app.states.rag_state import AdvisorState


def answer_evaluator_node(state: AdvisorState):

    llm = _get_llm()

    route = state.get("route")

    if route == "DOCUMENT":

        prompt = f"""
You are evaluating a credit card assistant document-based answer.

Check whether the answer correctly satisfies the user's query.

User Query:
{state["query"]}

Retrieved Documents:
{state.get("retrieved_docs", [])}

Assistant Answer:
{state["response"].get("answer", "")}


PASS:
- Answer is supported by retrieved documents
- Answer directly answers the user question
- No unsupported information is added

FAIL:
- Answer is unrelated
- Answer contradicts retrieved documents
- Answer does not satisfy user intent

Return only:
PASS or FAIL
"""

    else:

        prompt = f"""
You are evaluating a credit card assistant SQL-based answer.

Check whether the answer correctly satisfies the user's query.

User Query:
{state["query"]}

Generated SQL:
{state.get("generated_sql", "")}

SQL Result:
{state.get("sql_result", "")}

Assistant Answer:
{state["response"].get("answer", "")}


PASS:
- SQL result satisfies the user question
- Answer is supported by SQL result

FAIL:
- SQL result is empty/wrong
- Answer is unsupported
- Query intent is not satisfied

Return only:
PASS or FAIL
"""


    result = llm.invoke(prompt).content.strip().upper()

    print("ANSWER EVALUATION:", result)


    retry_count = state.get("retry_count", 0)

    if result == "FAIL":
        retry_count += 1


    return {
        **state,
        "evaluation_result": result,
        "retry_count": retry_count
    }