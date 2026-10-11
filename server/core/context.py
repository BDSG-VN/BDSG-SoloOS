"""Bound context sent to a model without deleting the source transcript."""


def bounded_history(messages, limit=48000):
    selected = []
    used = 0
    for message in reversed(messages):
        text = message["content"]
        if used + len(text) > limit:
            if not selected:
                text = "[Earlier part omitted to fit context]\n" + text[-max(0, limit - 50) :]
                selected.append({"role": message["role"], "content": text})
                used += len(text)
            break
        selected.append({"role": message["role"], "content": text})
        used += len(text)
    return {
        "messages": list(reversed(selected)),
        "characters": used,
        "omitted": len(messages) - len(selected),
    }


def chat_history(state, conversation):
    if getattr(state, "workspace", None) and hasattr(state.workspace, "chat_context"):
        return state.workspace.chat_context(conversation)["messages"]
    return bounded_history(state.brain.messages(conversation))["messages"]
