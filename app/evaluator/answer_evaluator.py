from app.core.llm import _get_llm
from app.states.rag_state import AdvisorState


def answer_evaluator_node(state: AdvisorState):

    llm = _get_llm()

    prompt = f"""
You are evaluating a credit card assistant response.

Check whether the answer correctly satisfies the user query.

User query:
{state["query"]}

Generated SQL:
{state.get("generated_sql", "")}

SQL Result:
{state.get("sql_result", "")}

Assistant Answer:
{state["response"].get("answer", "")}


Decide:

PASS:
- Answer is supported by SQL result
- SQL result satisfies the user question

FAIL:
- Answer is unsupported
- SQL result is empty/wrong
- Query does not satisfy user intent

Return only:
PASS or FAIL
"""

    result = llm.invoke(prompt).content.strip().upper()

    print("ANSWER EVALUATION:", result)

    return {
        **state,
        "evaluation_result": result
    }