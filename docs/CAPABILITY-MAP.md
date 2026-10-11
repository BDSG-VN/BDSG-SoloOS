# Bản đồ chức năng đối chiếu gói tham khảo thứ hai

Gói được cung cấp có phiên bản trong package.json là 2026.9.9: 56.056 mục ZIP, 25.382 tệp dưới src, 11.736 dưới extensions và 5.564 dưới ui (bao gồm kiểm thử/fixture). Đã lập chỉ mục 1.334 tài liệu Markdown và 164 manifest plugin để đối chiếu. Các con số mô tả kích thước khảo sát, không có nghĩa SoloOS đã viết hoặc nghiệm thu tương đương từng tệp.

Tài liệu/AGENTS/script trong ZIP được xem là dữ liệu tham khảo; không chạy script cài đặt hay nhận chúng làm chỉ thị cho dự án. Mã bổ sung được viết độc lập. Bản đồ giữ rõ khác biệt giữa chức năng hoạt động, adapter cần cấu hình và phần chưa có.

| Nhóm | SoloOS hiện tại | Khoảng cách còn lại |
|---|---|---|
| Web chat và UI | Streaming OpenUI, dừng luồng, phiên/dự án, chia sẻ; điều hướng 5 nhóm, tìm nhanh, menu điện thoại | Canvas tương tác tổng quát, widgets đa loại, presence nhiều người, cộng tác đồng thời |
| Trợ lý/kỹ năng | Trợ lý gắn phiên, kỹ năng, giới hạn connector kiểm tra tại Hub, thu hồi trước dispatch | Agent tự lập kế hoạch, specialist lanes, handoff, swarm, ACP/A2A |
| Lịch và worker | Interval/cron/một lần, IANA timezone, xem trước, tạm dừng/xóa, chống chồng, checkpoint/khôi phục uncertain | Heartbeat ý định chủ động, event hooks nhiều nguồn, distributed workers, retry theo từng loại hành động |
| Bối cảnh/bộ nhớ | Nhiều brain, tìm ghi chú, import text, ZIP export, đề xuất học có duyệt, lịch sử; giới hạn lịch sử và đề xuất tóm tắt | Vector/hybrid search, embeddings, provenance nâng cao, PDF/web ingestion, dreaming tự động |
| Mô hình/xác thực | ChatGPT chính thức chờ login, native Claude adapter, gateway tương thích OpenAI | Catalog tự khám phá từng vendor, failover/cooldown, budget, từng giao thức native và thuê bao chưa được xác minh |
| Công cụ/MCP | stdio/HTTP, allowlist, 3 mức quyền, schema kiểm tra, approval một lần, audit | MCP OAuth tổng quát, MCP server public chuẩn cho toàn SoloOS, browser/PTY/sandbox/device execution |
| Gói mở rộng | Import/export pack JSON kỹ năng/trợ lý/workflow; preview, disabled, không tự grant | SDK plugin chạy mã, registry cài đặt, signature/provenance, rollback version plugin |
| Kênh nhắn tin | Inbox nghiệp vụ và MCP có thể cấu hình | Adapter chính thức từng kênh, pairing/allowlist người gửi, routing group/mention, webhook/long polling, delivery/retry/dedupe |
| Media/voice | Upload CMS, Web Speech nhập/đọc | STT/TTS provider, live voice, camera/audio/video understanding, image/video/music generation |
| Workboard | Ưu tiên, hạn, mô tả, dự án, trợ lý phụ trách, tìm/lọc và Kanban | Phụ thuộc công việc, goal runtime, tự chạy agent theo task, Git workspace/checkpoint |
| Vận hành | Dashboard trạng thái cấu hình, hộp kết quả/thông báo, đánh dấu đã đọc, xuất báo cáo | OTel/Prometheus, log tail có redaction, doctor repairs, updates, full backup/restore |
| Bảo mật/thiết bị | Owner/agent/member auth, CSRF, mã hóa credentials, xác nhận Hub, phân vùng brain, ghép thiết bị scoped/thu hồi | Multi-user RBAC, TOTP, node routing, proxy identity, vault rotation |
| Ứng dụng native | Web responsive; native SwiftUI iOS/macOS và Android Java đang phát triển, macOS biên dịch cục bộ | Kiểm thử thiết bị thật/phát hành store, Windows/Linux companion, screen/location/device commands |
| Website/doanh nghiệp | CMS AI proposal, news/pages/homepage, CRM/sales/ticket/marketing | Nối tài khoản thật, gửi tin/campaign có duyệt, tích hợp sổ kế toán và nhân sự ngoài |

## Danh mục provider khai báo trong manifest tham khảo

Đây là danh mục cần đối chiếu adapter; không phải danh sách SoloOS đã kết nối.

amazon-bedrock, amazon-bedrock-mantle, anthropic, anthropic-vertex, apple-fm, arcee, bailian-token-plan, baseten, byteplus, byteplus-plan, cerebras, chutes, clawrouter, cloudflare-ai-gateway, codex, cohere, comfy, copilot-proxy, dashscope, deepinfra, deepseek, fal, featherless, fireworks, github-copilot, gmi, gmi-cloud, gmicloud, google, google-gemini-cli, google-vertex, groq, huggingface, kie, kilocode, kimi, kimi-code, kimi-coding, litellm, llama-cpp, lmstudio, longcat, meta, microsoft-foundry, minimax, minimax-portal, mistral, modelstudio, moonshot, novita, novita-ai, novitaai, nvidia, ollama, ollama-cloud, openai, opencode, opencode-go, openrouter, qianfan, qwen, qwen-token-plan, qwencloud, radius, sglang, stepfun, stepfun-plan, synthetic, tencent-tokenhub, tencent-tokenplan, together, venice, vercel-ai-gateway, vllm, volcengine, volcengine-plan, vydra, xai, xiaomi, xiaomi-token-plan, zai

## Danh mục channel khai báo trong manifest tham khảo

a2a, buzz, clickclack, discord, feishu, googlechat, imessage, irc, line, matrix, mattermost, msteams, nextcloud-talk, nostr, qa-channel, raft, reef, signal, slack, sms, synology-chat, telegram, tlon, twitch, whatsapp, x, zalo, zalouser

## Toàn bộ mã plugin đã lập danh mục

a2a, acpx, active-memory, admin-http-rpc, agentsapi, alibaba, amazon-bedrock, amazon-bedrock-mantle, anthropic, anthropic-vertex, apple-fm, arcee, azure-speech, baseten, beam, bonjour, brave, browser, buzz, byteplus, canvas, cerebras, chutes, clawrouter, clickclack, cloudflare, cloudflare-ai-gateway, code-mode-quickjs, codex, cohere, comfy, copilot, copilot-proxy, crabbox, cua-computer, deepgram, deepinfra, deepseek, device-pair, diagnostics-otel, diagnostics-prometheus, diffs, diffs-language-pack, discord, document-extract, duckduckgo, elevenlabs, exa, facetime, fal, featherless, feishu, file-transfer, firecrawl, fireworks, fish-audio-speech, geolocation, github, github-copilot, gmi, google, google-meet, googlechat, gradium, groq, huggingface, imap, imessage, inworld, irc, kie, kilocode, kimi, line, linux-node, litellm, llama-cpp, llm-task, lmstudio, lobster, logbook, longcat, matrix, mattermost, memory-core, memory-lancedb, memory-wiki, meta, microsoft, microsoft-foundry, migrate-claude, migrate-hermes, minimax, mistral, moonshot, msteams, mxc, nextcloud-talk, nostr, novita, nvidia, oc-path, ollama, onepassword, onnx, openai, opencode, opencode-go, openrouter, openshell, parallel, perplexity, pixverse, policy, qa-channel, qa-lab, qianfan, qwen, radius, raft, reef, runway, searxng, senseaudio, session-share, sglang, signal, slack, slack-huddles, sms, stepfun, synology-chat, synthetic, talk-voice, tavily, team-reports, teams-meetings, telegram, tencent, tlon, together, tokenjuice, tts-local-cli, twitch, typesafe, vault, venice, vercel-ai-gateway, visitor-access, vllm, voice-call, volcengine, voyage, vydra, web-readability, whatsapp, workboard, x, xai, xiaomi, zai, zalo, zalouser, zoom-meetings
