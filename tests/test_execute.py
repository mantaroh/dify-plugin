from src.execute import execute


def test_execute_echo():
    out = execute({"text": "hello"}, {})
    assert out["type"] == "text"
    assert "hello" in out["text"]

