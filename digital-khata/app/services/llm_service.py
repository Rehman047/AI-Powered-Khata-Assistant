import json
from datetime import datetime
from typing import Annotated, Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import InjectedState, ToolNode, tools_condition
from sqlalchemy.orm import Session
from typing_extensions import TypedDict

from app.config import settings
from app.services.analytics_service import get_shop_analytics
from app.services.customer_service import (
    add_customer,
    delete_customer,
    get_customer_info,
    get_self_view_link,
    list_all_customers,
)
from app.services.transaction_service import add_credit, list_due_today, list_overdue, record_payment


MODEL_NAME = "llama-3.3-70b-versatile"

SYSTEM_PROMPT_TEMPLATE = """
You are Digital Khata Assistant for a small retail shop in Pakistan.

Your job is to manage customer udhaar records from natural-language English commands.
Always use the provided tools for database reads/writes. Never guess, invent, or hallucinate
customer names, balances, transactions, or amounts.

If required info is missing (customer name, amount, due date when needed), ask a concise
clarifying question and do not call tools yet.
If ambiguity exists, ask for clarification first.

Response style:
- Keep confirmations and simple answers to 1-2 sentences.
- Use neat list format for multi-customer outputs.
- Format amounts as PKR X,XXX with commas.
- Show dates in human-readable form.
- For list_due_today and list_overdue results, return a readable numbered list with
    customer name and balance, and include total count.
- If list_due_today or list_overdue is empty, respond with a natural sentence such as
    "No payments are due today" instead of showing raw JSON.
- For get_shop_analytics results, present the six metrics as readable financial prose
    instead of echoing raw key names.

Today is: {today}

Important multi-step rule:
If a message implies both creating a new customer and adding credit in one request,
call add_customer first, then add_credit in the same turn.
""".strip()

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    db: Session


def _get_db_from_state(state: dict[str, Any]) -> Session:
    db = state.get("db")
    if db is None:
        raise ValueError("Database session missing from LangGraph state.")
    return db


@tool
def add_customer_tool(
    name: str,
    phone: str | None = None,
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> str:
    """Adds a new customer to the digital ledger."""
    try:
        result = add_customer(_get_db_from_state(state or {}), name=name, phone=phone)
        return json.dumps(result)
    except Exception as exc:  # pragma: no cover
        return json.dumps({"error": f"Tool execution failed: {str(exc)}"})


@tool
def add_credit_tool(
    customer_name: str,
    amount: float,
    note: str | None = None,
    due_date: str | None = None,
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> str:
    """Records credit given (udhaar) to a customer."""
    try:
        result = add_credit(
            _get_db_from_state(state or {}),
            customer_name=customer_name,
            amount=amount,
            note=note,
            due_date=due_date,
        )
        return json.dumps(result)
    except Exception as exc:  # pragma: no cover
        return json.dumps({"error": f"Tool execution failed: {str(exc)}"})


@tool
def record_payment_tool(
    customer_name: str,
    amount: float,
    note: str | None = None,
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> str:
    """Records a payment received from a customer."""
    try:
        result = record_payment(
            _get_db_from_state(state or {}),
            customer_name=customer_name,
            amount=amount,
            note=note,
        )
        return json.dumps(result)
    except Exception as exc:  # pragma: no cover
        return json.dumps({"error": f"Tool execution failed: {str(exc)}"})


@tool
def get_customer_info_tool(
    customer_name: str,
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> str:
    """Gets a customer's balance, trust info, and recent transactions."""
    try:
        result = get_customer_info(_get_db_from_state(state or {}), customer_name=customer_name)
        return json.dumps(result)
    except Exception as exc:  # pragma: no cover
        return json.dumps({"error": f"Tool execution failed: {str(exc)}"})


@tool
def list_all_customers_tool(state: Annotated[dict[str, Any], InjectedState] = None) -> str:
    """Lists all customers with balances and trust scores."""
    try:
        result = list_all_customers(_get_db_from_state(state or {}))
        return json.dumps(result)
    except Exception as exc:  # pragma: no cover
        return json.dumps({"error": f"Tool execution failed: {str(exc)}"})


@tool
def delete_customer_tool(
    customer_name: str,
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> str:
    """Deletes a customer when their balance is zero."""
    try:
        result = delete_customer(_get_db_from_state(state or {}), customer_name=customer_name)
        return json.dumps(result)
    except Exception as exc:  # pragma: no cover
        return json.dumps({"error": f"Tool execution failed: {str(exc)}"})


@tool
def get_customer_self_view_link_tool(
    customer_name: str,
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> str:
    """Gets a shareable read-only self-view link for a customer."""
    try:
        result = get_self_view_link(_get_db_from_state(state or {}), customer_name=customer_name)
        return json.dumps(result)
    except Exception as exc:  # pragma: no cover
        return json.dumps({"error": f"Tool execution failed: {str(exc)}"})


@tool
def list_due_today_tool(state: Annotated[dict[str, Any], InjectedState] = None) -> str:
    """Use when asked who needs to pay today, what is due today, or who has payments due today."""
    try:
        result = list_due_today(_get_db_from_state(state or {}))
        return json.dumps(result)
    except Exception as exc:  # pragma: no cover
        return json.dumps({"error": f"Tool execution failed: {str(exc)}"})


@tool
def list_overdue_tool(state: Annotated[dict[str, Any], InjectedState] = None) -> str:
    """Use when asked who is late, who is overdue, or who has not paid past due obligations."""
    try:
        result = list_overdue(_get_db_from_state(state or {}))
        return json.dumps(result)
    except Exception as exc:  # pragma: no cover
        return json.dumps({"error": f"Tool execution failed: {str(exc)}"})


@tool
def get_shop_analytics_tool(state: Annotated[dict[str, Any], InjectedState] = None) -> str:
    """Use for overall shop summary such as outstanding amount, balances, average debt, and analytics overview."""
    try:
        result = get_shop_analytics(_get_db_from_state(state or {}))
        return json.dumps(result)
    except Exception as exc:  # pragma: no cover
        return json.dumps({"error": f"Tool execution failed: {str(exc)}"})


TOOLS = [
    add_customer_tool,
    add_credit_tool,
    record_payment_tool,
    get_customer_info_tool,
    list_all_customers_tool,
    delete_customer_tool,
    get_customer_self_view_link_tool,
    list_due_today_tool,
    list_overdue_tool,
    get_shop_analytics_tool,
]

_model: Any | None = None


def _get_model() -> Any:
    global _model
    if _model is None:
        _model = ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=MODEL_NAME,
        ).bind_tools(TOOLS)
    return _model


def _call_model(state: AgentState) -> dict[str, list[AnyMessage]]:
    today = datetime.now().strftime("%d %B %Y")
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(today=today)
    response = _get_model().invoke([SystemMessage(content=system_prompt), *state["messages"]])
    return {"messages": [response]}


_workflow = StateGraph(AgentState)
_workflow.add_node("agent", _call_model)
_workflow.add_node("tools", ToolNode(TOOLS))
_workflow.add_edge(START, "agent")
_workflow.add_conditional_edges("agent", tools_condition)
_workflow.add_edge("tools", "agent")
_graph = _workflow.compile()


def _to_langgraph_history(history: list[dict[str, str]]) -> list[AnyMessage]:
    converted: list[AnyMessage] = []
    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if role == "user":
            converted.append(HumanMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))
    return converted


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for chunk in content:
            if isinstance(chunk, dict) and "text" in chunk:
                parts.append(str(chunk["text"]))
            else:
                parts.append(str(chunk))
        return "\n".join(parts)
    return str(content)


def _to_response_history(messages: list[AnyMessage]) -> list[dict[str, str]]:
    parsed_history: list[dict[str, str]] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            parsed_history.append({"role": "user", "content": _content_to_text(msg.content)})
        elif isinstance(msg, AIMessage):
            text = _content_to_text(msg.content).strip()
            if text:
                parsed_history.append({"role": "assistant", "content": text})
    return parsed_history


def _extract_last_assistant(messages: list[AnyMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            text = _content_to_text(msg.content).strip()
            if text:
                return text
    return "I could not complete that request right now. Please try again."


async def run_khata_chat(message: str, history: list[dict[str, str]], db_session: Session) -> dict[str, Any]:
    inputs = {
        "messages": [*_to_langgraph_history(history), HumanMessage(content=message)],
        "db": db_session,
    }

    try:
        final_state = await _graph.ainvoke(inputs)
        messages: list[AnyMessage] = final_state["messages"]
    except Exception as exc:
        fallback = f"I could not complete that request right now. {str(exc)}"
        updated_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": fallback},
        ]
        return {"reply": fallback, "history": updated_history}

    return {
        "reply": _extract_last_assistant(messages),
        "history": _to_response_history(messages),
    }


def chat_with_tools(*, message: str, history: list[dict[str, str]], db: Session) -> tuple[str, list[dict[str, str]]]:
    inputs = {
        "messages": [*_to_langgraph_history(history), HumanMessage(content=message)],
        "db": db,
    }

    try:
        final_state = _graph.invoke(inputs)
        messages: list[AnyMessage] = final_state["messages"]
    except Exception as exc:
        fallback = f"I could not complete that request right now. {str(exc)}"
        updated_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": fallback},
        ]
        return fallback, updated_history

    final_reply = _extract_last_assistant(messages)
    return final_reply, _to_response_history(messages)
