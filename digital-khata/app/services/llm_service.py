def run_llm_tool_call(*, message: str, history: list[dict]) -> dict:
    return {
        "status": "placeholder",
        "message": "Groq integration will be implemented in Week 2.",
        "input_message": message,
        "history_count": len(history),
    }
