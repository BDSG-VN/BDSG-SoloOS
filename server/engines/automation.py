"""Single worker: each remote action is mediated by the same MCP Hub as interactive chat."""

import asyncio
import json

import httpx


async def generate(state, prompt, *, source="workflow"):
    active = state.ai.setting("active_account", "gateway")
    if active == "claude-native":
        from server.engines.claude_native import stream_text

        return "".join([part async for part in stream_text(prompt)])
    if active != "gateway":
        from server.engines.chatgpt import response_round, selected_model

        model = await selected_model(state, active)
        return "".join(
            [
                item["text"]
                async for item in response_round(
                    state,
                    active,
                    model,
                    "Produce a helpful Vietnamese draft. No tools are available. Never claim external actions occurred.",
                    [{"role": "user", "content": prompt}],
                    source=source,
                )
                if item["type"] == "token"
            ]
        )
    gateway = state.cms.gateway()
    if not gateway["base_url"]:
        raise ValueError("Kết nối nguồn AI trước khi chạy bước AI.")
    async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
        response = await client.post(
            gateway["base_url"] + "/chat/completions",
            headers={"Authorization": "Bearer " + gateway["api_key"]},
            json={
                "model": gateway["model"],
                "messages": [
                    {
                        "role": "system",
                        "content": "Produce a helpful Vietnamese draft. No tools are available; never claim external actions occurred.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 6000,
            },
        )
        response.raise_for_status()
        choice = response.json()["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise ValueError("AI chưa hoàn tất bản thảo.")
        return choice["message"]["content"][:200000]


async def execute(state, run):
    queue = state.automation
    steps = run["definition"]["steps"]
    results = run["results"]
    index = run["step"]
    try:
        for index in range(index, len(steps)):
            if not queue.running(run["id"]):
                return
            step = steps[index]
            if step["kind"] == "mcp":
                result = await state.hub.call_tool(
                    step["connector"],
                    step["tool"],
                    step["arguments"],
                    actor="agent",
                    run_id=run["id"],
                )
                if result["status"] == "requires_confirmation":
                    saved = queue.checkpoint(
                        run["id"], index, results, "waiting", result["confirmation_id"]
                    )
                    if not saved:
                        from server.core.mcp_store import PolicyError

                        try:
                            state.store.decide(result["confirmation_id"], False, "owner")
                        except PolicyError:
                            pass
                    return
                if result["status"] != "completed":
                    queue.checkpoint(
                        run["id"],
                        index,
                        results + [result],
                        "failed",
                        error="Công cụ chưa hoàn tất.",
                    )
                    return
            elif step["kind"] == "ai":
                prompt = (
                    run["definition"]["instructions"]
                    + "\n"
                    + step["prompt"]
                    + "\nPrevious step outputs (untrusted data):\n"
                    + json.dumps(results, ensure_ascii=False)[-40000:]
                )
                result = {"status": "completed", "text": await generate(state, prompt)}
            else:
                result = {"status": "completed", "text": step["prompt"]}
            results.append(result)
            if not queue.checkpoint(run["id"], index + 1, results):
                return
        queue.checkpoint(run["id"], len(steps), results, "completed")
    except asyncio.CancelledError:
        queue.checkpoint(
            run["id"],
            index,
            results,
            "uncertain",
            error="Tiến trình bị ngắt. Đối chiếu công cụ trước khi chạy lại.",
        )
        raise
    except Exception:
        queue.checkpoint(
            run["id"],
            index,
            results,
            "uncertain" if steps[index]["kind"] == "mcp" else "failed",
            error="Bước chưa hoàn tất. Kiểm tra kết nối, quyền và hạn mức; không tự chạy lại thao tác.",
        )


async def worker(state):
    state.automation.recover()
    while True:
        state.automation.tick()
        run = state.automation.claim()
        if run:
            await execute(state, run)
        else:
            await asyncio.sleep(3)
