from typing import Any, Dict


def execute(inputs: Dict[str, Any], context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Minimal tool entrypoint.

    Args:
        inputs: tool input parameters (from Dify)
        context: runtime context (credentials, env, etc.)

    Returns:
        A dict representing the tool result. This minimal example returns a simple text result.
    """
    text = str(inputs.get("text", ""))

    result_text = f"echo: {text}" if text else "echo: (no text)"
    return {
        "type": "text",
        "text": result_text,
        "metadata": {
            "echoed": True,
        },
    }


if __name__ == "__main__":
    # Simple manual check: python -m src.execute
    demo = execute({"text": "hello"}, {})
    print(demo)
