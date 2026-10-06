# Glossary

| Term | Meaning |
|---|---|
| **Action** | What a decision says should happen: `ALLOW`, `WARN`, `REQUIRE_APPROVAL`, `BLOCK`, `TERMINATE` (in increasing severity). |
| **Adapter / hook** | The code that connects AgentShield to a real agent: turns its tool calls and results into `Event`s and applies decisions. MCP proxy or LangGraph adapter. |
| **AgentDojo** | A public benchmark of prompt-injection attacks on tool-using agents. We will measure against it from M1. |
| **ASI01–ASI10** | The OWASP Top 10 for Agentic Applications. Buyers use these IDs in security questionnaires. |
| **Audit log** | Our append-only, hash-chained record of every event and decision (`audit.py`). |
| **Checkpoint** | A signed `(seq, hash)` of the log's latest entry. Stored separately, it proves the log wasn't truncated or rebuilt. |
| **Combine** | The kernel's rule for merging policy votes: most severe wins. |
| **Contract** | `model.py` + `kernel.py`: the shared types and interfaces everyone builds against. Changes need all three reviews. |
| **Decision** | The kernel's output for one event: action, mode, reasons, policy id. |
| **DLP** | Data loss prevention: stopping sensitive data from leaving. Problem 4. |
| **Egress** | Anything leaving the system: emails, webhooks, outbound API calls. |
| **Enforced action** | What actually happens: the decision's action in enforce mode, always `ALLOW` in shadow mode. |
| **Event** | One thing the agent did or received, as seen at an interception point. |
| **Fail closed** | When something breaks, deny rather than allow. A crashing policy votes `BLOCK`. |
| **Flagship demo** | Resume → salaries → external email, paused for approval. Milestone M1. |
| **Hash chain** | Each log entry includes the hash of the previous one, so changing any entry breaks every link after it. |
| **Indirect prompt injection** | Instructions hidden in content the agent reads (a resume, web page, email) rather than typed by the user. Problem 2. |
| **Label** | A provenance tag on content: origin, trust, sensitivity. |
| **Labeler** | A plug-in that attaches labels to events as content enters. Vibhas's Problem 2 work. |
| **MCP** | Model Context Protocol: the standard way agents connect to tool servers. |
| **MCP proxy** | A form of adapter that sits between an agent and its MCP servers, so it works without changing the agent's code. |
| **Mode** | `SHADOW` (record only) or `ENFORCE`. Shadow is the default. |
| **Origin** | Where content came from, as a string: `tool:read_resume`, `db:salaries`, `mcp:server/tool`. |
| **Policy** | A plug-in that votes on an event: returns a `Decision` or `None`. |
| **Presidio** | Microsoft's open-source PII detector. Used for the pattern-matching half of Problem 4. |
| **Prompt Guard / LLM Guard** | Existing jailbreak and injection classifiers. Used for Problem 1. |
| **Provenance** | The record of where a piece of content came from. Our core idea. |
| **Replay** | Re-running a recorded session through current policies and comparing decisions. |
| **Sensitivity** | How confidential content is: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `SECRET`. |
| **Session** | One conversation. Holds the history of every event and decision so far. |
| **Shadow mode** | Policies run and decisions are recorded, but nothing is blocked. How every deployment starts. |
| **Shield** | The kernel object: `Shield.check(event)` runs labelers, policies, combine, session and audit. |
| **Taint** | Untrusted origin spreading to what it touches. Session-level taint: once untrusted content is in context, later outputs are treated as untrusted too. |
| **Trifecta / lethal trifecta** | Untrusted input + sensitive data + external action in one session. Any two are fine; all three is the attack. Problem 5. |
| **Trust** | How much authority content has, set by origin: `TRUSTED`, `USER`, `UNTRUSTED`. |
