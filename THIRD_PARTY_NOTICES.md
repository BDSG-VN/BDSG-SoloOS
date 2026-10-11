# References and dependencies

Solo-OS is a new implementation, released under MIT. No source code, environment
files, credentials, business records, or deployments were copied from the local
SoloCEO repository. That repository informed the application navigation, LLM
gateway pattern, and human approval workflow.

Runtime dependencies retain their own licenses. Notable dependencies: FastAPI
(MIT), MCP Python SDK (MIT), React (MIT), OpenUI React Lang (MIT), Zod (MIT),
Lucide (ISC), HTTPX (BSD-3-Clause), cryptography (Apache-2.0 / BSD-3-Clause).
See each installed package for its complete license text.

Architectural references:

- [OpenUI](https://github.com/thesysdev/openui): official streaming parser and React renderer.
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk): MCP transports and client lifecycle.
- [Javis OS](https://github.com/blogminhquy/javis-os): local Markdown memory and conversation persistence.
- [Hermes Agent](https://hermes-agent.nousresearch.com/): shared memory and channel-independent agents.
- [OpenClaw](https://github.com/openclaw/openclaw): workspace and plugin organization.

OpenUI's token reduction is an upstream benchmark, not a measured performance
guarantee for Solo-OS. No proprietary model or commercial service is bundled.
