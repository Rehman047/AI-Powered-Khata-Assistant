import json
from datetime import datetime
from typing import Any

from groq import Groq
from sqlalchemy.orm import Session

from app.config import settings
from app.services.customer_service import (
    add_customer,
    delete_customer,
    get_customer_info,
    get_self_view_link,
    list_all_customers,
)
from app.services.transaction_service import add_credit, record_payment


MODEL_NAME = "llama-3.3-70b-versatile"
MAX_TOOL_ITERATIONS = 10

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

Today is: {today}

Important multi-step rule:
If a message implies both creating a new customer and adding credit in one request,
call add_customer first, then add_credit in the same turn.
""".strip()

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "add_customer",
            "description": "Register a new customer before giving them credit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer full name."},
                    "phone": {"type": "string", "description": "Customer phone number."},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_credit",
            "description": "Record credit given to an existing customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name."},
                    "amount": {
                        "type": "number",
                        "description": "Positive PKR amount that increases what customer owes.",
                    },
                    "note": {"type": "string", "description": "Optional credit description."},
                    "due_date": {
                        "type": "string",
                        "description": "Expected repayment date in YYYY-MM-DD.",
                    },
                },
                "required": ["customer_name", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_payment",
            "description": "Record payment received from a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name."},
                    "amount": {"type": "number", "description": "Positive payment amount in PKR."},
                    "note": {"type": "string", "description": "Optional payment note."},
                },
                "required": ["customer_name", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_info",
            "description": "Get a customer's balance, trust info, and recent transactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name."}
                },
                "required": ["customer_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_customers",
            "description": "List all customers with balances and trust scores.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_customer",
            "description": "Delete a customer permanently. Only works when balance is zero.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name."}
                },
                "required": ["customer_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_self_view_link",
            "description": "Get shareable read-only self-view balance link for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name."}
                },
                "required": ["customer_name"],
            },
        },
    },
]

groq_client = Groq(api_key=settings.GROQ_API_KEY)


def _execute_tool(tool_name: str, arguments: dict[str, Any], db: Session) -> dict:
    tool_map = {
        "add_customer": add_customer,
        "add_credit": add_credit,
        "record_payment": record_payment,
        "get_customer_info": get_customer_info,
        "list_all_customers": list_all_customers,
        "delete_customer": delete_customer,
        "get_customer_self_view_link": get_self_view_link,
    }

    tool_fn = tool_map.get(tool_name)
    if tool_fn is None:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        return tool_fn(db, **arguments)
    except Exception as exc:  # pragma: no cover
        return {"error": f"Tool execution failed: {str(exc)}"}


def chat_with_tools(*, message: str, history: list[dict[str, str]], db: Session) -> tuple[str, list[dict[str, str]]]:
    today = datetime.now().strftime("%d %B %Y")
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(today=today)

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    for _ in range(MAX_TOOL_ITERATIONS):
        response = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
        )

        choice = response.choices[0]
        finish_reason = choice.finish_reason

        if finish_reason == "stop":
            final_reply = choice.message.content or "I could not generate a response."
            updated_history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": final_reply},
            ]
            return final_reply, updated_history

        if finish_reason == "tool_calls":
            assistant_message = choice.message
            tool_calls = assistant_message.tool_calls or []

            assistant_payload: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in tool_calls
                ],
            }
            messages.append(assistant_payload)

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                raw_arguments = tool_call.function.arguments or "{}"

                try:
                    parsed_arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    parsed_arguments = {}

                result = _execute_tool(tool_name, parsed_arguments, db)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )
            continue

        break

    fallback = "I could not complete that request right now. Please try again."
    updated_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": fallback},
    ]
    return fallback, updated_history
