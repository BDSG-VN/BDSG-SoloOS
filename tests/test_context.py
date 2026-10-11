from server.core.context import bounded_history


def test_context_preserves_recent_messages_without_mutating_transcript():
    messages = [
        {"role": "user", "content": "a" * 2000},
        {"role": "assistant", "content": "b" * 2000},
        {"role": "user", "content": "new"},
    ]
    result = bounded_history(messages, 3000)
    assert result["messages"] == messages[1:]
    assert result["omitted"] == 1
    assert messages[0]["content"] == "a" * 2000
    huge = bounded_history([{"role": "assistant", "content": "x" * 5000}], 1000)
    assert huge["characters"] <= 1000
    assert "omitted" in huge["messages"][0]["content"]
