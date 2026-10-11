"""Provider identifiers; actual models are configured as aliases in the LLM gateway."""

PROVIDERS = [
    {"id": name, "label": label}
    for name, label in [
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic"),
        ("google", "Gemini"),
        ("deepseek", "DeepSeek"),
        ("ollama", "Ollama"),
        ("mistral", "Mistral"),
        ("groq", "Groq"),
        ("xai", "xAI"),
        ("openrouter", "OpenRouter"),
        ("together", "Together AI"),
        ("fireworks", "Fireworks AI"),
        ("azure", "Azure OpenAI"),
        ("bedrock", "Amazon Bedrock"),
    ]
]
