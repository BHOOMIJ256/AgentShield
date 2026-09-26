# Start with the uncomfortable part

The document you have is a good engineering design doc and a weak commercial one. It describes a category — "composable runtime security SDK for agents" — rather than a purchase. And the category it describes has, in the ~18 months since this kind of framing became popular, been almost entirely absorbed by incumbents.

Look at what actually happened to the companies doing exactly this:

- Robust Intelligence went to Cisco for roughly $400M and became Cisco AI Defense.
- Protect AI went to Palo Alto for an estimated $500–700M and now powers Prisma AIRS.
- Lakera went to Check Point for around $300M.
- SentinelOne bought Prompt Security ($180M) and Observo AI ($225M).
- F5 acquired CalypsoAI, Cato acquired Aim Security, Varonis acquired SlashNext.
- Check Point Software acquired additional players, and Tenable/Apex and CrowdStrike/Pangea are also in the space.

And the incumbents are explicit about why. Palo Alto's own position is that security for AI agents won't live in isolation — it becomes part of a broader security platform with identity, access, zero trust, and privilege as the foundational controls, and there may be room for only a small number of well-funded startups to carve out meaningful share.

So the strategic question is not "how do I build AgentShield better." It is: "what is the specific thing that a platform vendor cannot easily bolt on, that someone will pay for before the platform vendors get there?"

The good news: that thing exists, and parts of your document already gesture at it. But you have to cut about 70% of the scope to find it.

---

## What the market actually looks like right now

### Size and heat

- Agentic AI security is projected to grow from about $1.65B in 2026 to $13.5B by 2032 at ~42% CAGR.
- Around RSAC 2026 alone, over $392M in new agentic-AI-security funding was announced.
- This is a real budget line now, not a research topic.

### The demand gap is enormous and quantified

- Eighty percent of Fortune 500 companies now run active AI agents, yet only 14% have full security approval for them.
- That gap — production agents that security has not signed off on — is your actual market.
- Notice the buyer implied by that sentence: it is not the developer building the agent. It is the person who has to approve it.

### Standards crystallized while you were writing

- OWASP shipped the Top 10 for Agentic Applications in December 2025 — ASI01 through ASI10 — covering agent goal hijack, tool misuse, memory poisoning, and rogue agents.
- It aligns with the LLM Top 10, the Non-Human Identity Top 10, and the AI Vulnerability Scoring System.
- The Cloud Security Alliance launched a dedicated AI security foundation at RSAC 2026 whose stated 2026 mission is "securing the agentic control plane."
- This matters enormously for you: there is now a shared vocabulary that buyers use in RFPs. Every capability in your doc should be labeled with an ASI number or it will read as invented taxonomy.

### Regulatory clock

- The EU AI Act's high-risk obligations apply from 2 August 2026.
- Combined with ISO 42001 and NIST AI RMF, this creates demand for something your doc treats as an afterthought: exportable evidence that a control existed, fired, and was reviewed.

### The layer map

The most useful framing I found for positioning: the "guardrails" market is really four distinct layers — content, evaluation, sandbox, and action — each catching a different failure class, none replacing another, with most production agents needing two or three.

Your document spans all four, which sounds comprehensive and reads as unfocused. Concretely:

- Content layer — prompt injection, jailbreak, PII detection.

  - This is commodity.
  - Free open-weights models (Llama Guard, Prompt Guard, NemoGuard), free cloud services (Bedrock Guardrails, Azure Content Safety), and mature OSS (LLM Guard, Presidio, Guardrails AI).
  - Worse, a text classifier cannot stop an agent from making a tool call — the classifier inspects text, but the threat is the action.
  - Sections 5 and the MVP list in §20 are heavily weighted toward this commodity layer.
- Evaluation layer — red teaming, benchmarks, CI gates.

  - Crowded but healthy.
  - This is where the money currently flows.
- Sandbox layer — process/host isolation.

  - Not your doc at all.
  - It is a real gap.
- Action layer — pre-execution authorization of tool calls.

  - This is where your doc is strongest.
  - This is where the market is thinnest.
  - Sections 6, 12, 13, and 15 are the valuable ones.

### The genuinely under-served niche

- Total disclosed MCP security funding is about $40M across four startups — Operant AI, Runlayer, Helmet, and Manufact — for a protocol with 17,000+ deployed servers.
- Platform vendors are shipping MCP security features before the standalone startups even reach Series A.
- In a typical 10,000-person organization, over 15% of employees run an average of two MCP servers each — roughly 3,000 deployments, each with its own credentials, no least-privilege authorization, and no way to govern them.

### The competitive bar for detection quality

- Lakera, pre-acquisition, published detection rates above 98%, sub-50ms latency, and false positives below 0.5%.
- If your semantic detector is an LLM call, you are structurally an order of magnitude off on latency and you have no published FP number.
- NeMo Guardrails typically adds 100–300ms and Guardrails AI 50–200ms.
- NeMo's weakness is instructive: Colang has a learning curve and a small community, and it requires real engineering investment to define and maintain policies.

That last point is the single most important market signal for your design.

---

## The fatal flaw in the current design (and its fix)

Your §7 is the philosophical heart of the doc: "we cannot hardcode every possible security rule; the developer provides the security objective."

That is technically correct and commercially close to suicidal.

You are shipping a blank slate. NVIDIA — with infinite distribution, GPUs, and marketing — shipped a blank slate with a DSL and got a small community because of the configuration burden. A two-person open-source project shipping a more general blank slate will get GitHub stars and zero production deployments. Nobody has time to author a threat model for their resume agent.

The fix, borrowed from how WAF, DLP, and CSPM all solved this exact cold-start problem:

1. Shadow mode is the default, not an option.

   - Install → observe → learn a behavioral baseline of what this agent actually does (which tools, which arguments, which data classes, which destinations).
   - Block nothing on day one.
   - This is also the only honest way to deploy something that can terminate a production agent.
2. Policy packs, not policy primitives.

   - Ship opinionated, versioned, ASI-mapped bundles: `agentshield/packs/coding-agent`, `packs/support-agent`, `packs/rag-readonly`, `packs/finops`.
   - The developer picks a pack and overrides 5%.
   - Your composability story stays intact underneath, but the first-run experience is one line and it already does something.
3. Policy synthesis from observation.

   - After a week of shadow mode, generate the proposed policy from observed behavior and let a human diff it.
   - This is the feature that converts free users to paid, because generating, versioning, reviewing, and approving policies across a fleet of agents is inherently a control-plane job.

Reframe §7 from "the developer defines the semantics" to "AgentShield learns the agent's normal behavior and proposes the policy; the developer edits it." That is a product. The current version is a toolkit.

---

## Reframing the whole thing: from SDK to control plane

Here is the architecture that makes this sellable, replacing §16.

```text
DATA PLANE  (open source, Apache 2.0, runs in customer infra)
├── in-process SDK        (LangGraph/CrewAI/PydanticAI adapters)
├── MCP gateway / proxy   ← highest-leverage form factor
└── OTel-compatible emitter

    ↓ signed decision + evidence events

CONTROL PLANE  (commercial: SaaS or self-hosted license)
├── agent & tool inventory (what agents exist, what they can reach)
├── policy authoring, versioning, approval, distribution
├── behavioral baselines + drift detection
├── evidence & audit packs (EU AI Act / ISO 42001 / SOC 2)
├── replay & CI regression (ASI01–ASI10 suites)
└── SSO/SCIM/RBAC, multi-tenant, retention, SLA
```

### Three deliberate changes from your document

1. The MCP gateway matters more than the SDK.

   - An in-process SDK requires the developer to modify agent code, which means adoption dies at the org boundary — security teams cannot mandate it and cannot verify coverage.
   - A gateway/proxy sitting in front of MCP servers and tool APIs is enforceable, discoverable, and works on agents whose code nobody controls (Claude Code, Cursor, Copilot, vendor SaaS agents).
   - Sysdig launched runtime security specifically for coding agents at RSAC 2026, citing that nearly 65% of developers are vibe-coding weekly.
   - Keep the SDK for deep semantics; lead with the gateway for coverage.
2. The policy kernel must be deterministic, signed, and versioned.

   - Your §9 already says this; make it a hard architectural law.
   - LLM judgments are advisory signals with confidence scores that feed a deterministic decision function.
   - Nobody will let a nondeterministic LLM be the thing that blocks a payment, and no auditor will accept "the model decided."
   - This also fixes your latency story: rules and parsers on the hot path, LLM checks cached, batched, or run out-of-band with retroactive quarantine.
3. Provenance/taint tracking is your actual IP.

   - §11 is the most defensible idea in the entire document and it's buried as a "future direction."
   - Everyone does prompt-injection classifiers.
   - Almost nobody does end-to-end label propagation — tracking that this specific string entered from a low-trust web page, flowed through the agent's reasoning, and is now an argument to `send_email`.
   - That is a dataflow problem, not an ML problem, and it's the one thing a classifier vendor genuinely cannot replicate by swapping in a better model.
   - It also directly produces the enforcement rule that matters most: untrusted-origin content may not become a control-flow instruction or an argument to a high-authority tool.

Promote provenance from §11 to the core of the product. Your one-line pitch should be about data-flow authorization, not about detection.

---

## What you can actually sell, and to whom

Four monetization paths, ordered by how fast a small team can reach revenue:

### A. Services + OSS (fastest, unglamorous, funds everything else)

Sell fixed-price "agent security assessments" against OWASP ASI01–ASI10 — a 2-week engagement producing a findings report, a threat model, and a set of AgentShield policies deployed in shadow mode.

- ₹5–25L per engagement in India
- $25–60K in the US/EU

This is real revenue in month two, it forces you to learn what buyers actually fear, and every engagement generates policy packs and attack cases that become product. The 80%-deployed/14%-approved gap is this offer's pitch.

### B. Open core

Open core is the most common monetization model for developer tools in 2026 — open core functionality, charge for the enterprise features companies need: audit logs, team management, compliance tooling, SLAs — and it only works if the open source version is genuinely useful on its own.

The open/paid boundary that works here:

| Free (Apache 2.0)              | Paid                                     |
| ------------------------------ | ---------------------------------------- |
| SDK, gateway, adapters         | Fleet inventory & coverage reporting     |
| All detectors & policy DSL     | Policy authoring, approval, distribution |
| Local audit log to stdout/OTel | Retained, tamper-evident audit store     |
| Community policy packs         | Curated/updated packs + threat feed      |
| Single-agent shadow mode       | Cross-agent baselines & drift alerts     |
| Manual replay CLI              | CI gates, regression suites, dashboards  |
| —                             | SSO/SCIM/RBAC, evidence exports, SLA     |

Cut on the buyer, not on capability: everything a single developer needs is free; everything a team or an auditor needs is paid. License the control plane BUSL or a commercial EULA so a cloud provider can't resell it.

### C. Compliance evidence layer

Enterprises will pay for hosted open source, long-term support, SBOMs, audit exports, and security fixes because those remove operational and legal stress; buyers increasingly want control, local hosting, auditability, and exit options, which turns open source into a board-level buying decision.

With EU AI Act high-risk obligations now live, "prove your agent had enforced controls and a reviewed audit trail" is a budgeted problem. This packages nicely as a paid module rather than a whole company.

### D. Sovereign / self-hosted neutrality

Every winner in this space is now owned by a US-headquartered platform vendor, and most guardrail services require sending prompts, tool arguments, and retrieved documents to a third-party API. A fully self-hosted, no-egress, framework-neutral, model-neutral enforcement layer is a genuine differentiator for regulated Indian, EU, and Middle East buyers — and it is a position the acquired vendors structurally cannot take. For a small independent team, this may be the single strongest wedge available.

### Pricing metric

Avoid per-token and per-decision as the headline (hostile to adopt, punishes the agent-heavy customers you want). Use per-protected-agent-per-month, tiered by decision volume, with the console seat-free.

Something like:

- free self-hosted single-agent
- $/agent/month for teams
- enterprise floor with self-hosting, evidence exports, and support

Buyer split you must design for: the developer adopts, the platform/AI-engineering lead deploys, the CISO or AI-governance owner pays, and compliance signs off. Your document currently speaks only to the first.

---

## Where the moat is (and isn't)

Be honest with yourself about this.

### Not a moat

- prompt-injection detection
- PII detection
- jailbreak classifiers
- LLM-as-judge semantics
- SQL parsing

All commodity, all free somewhere, all improving faster than you can maintain them.

### Plausible moats, in descending order

1. The provenance/taint engine

   - Hard to build.
   - Hard to copy.
   - Directly maps to the attack class everyone fears: indirect injection → autonomous harmful action.
   - Directly maps to ASI01.
2. The attack corpus and replay harness

   - Your §19 idea is better than you realize.
   - A benchmark operationalizing the OWASP Agentic Top 10 into executable tasks was recently merged into the UK AI Safety Institute's `inspect_evals` repository.
   - A growing library of real attack traces that can be replayed against a customer's policies after every change is a data asset that compounds.
3. Breadth and quality of framework/gateway adapters

   - Boring, unsexy, and the actual reason people pick one library over another.
4. Policy language + ecosystem

   - Only a moat if it becomes a de facto standard.
   - Long odds, but cheap to try.
   - Cheaper if you express policies as ASI-mapped and expose them as OTel semantic conventions rather than a bespoke DSL.

---

## Sequenced plan

### Months 0–3

Do not build the §20 MVP list; it is eleven things. Build:

- MCP gateway interception
- deterministic tool/argument policy
- provenance labels
- tamper-evident audit log
- one framework adapter

Ship shadow mode as the default. Publish latency (p50/p99) and false-positive rates against a public suite. Start the services offer in parallel.

### Months 3–6

Prove it on someone else's agent. Three design partners, ideally in one vertical (coding agents in CI, or finance-ops agents — pick one). Convert every incident into a replayable test case and a policy pack. Write the incident post-mortems publicly; in security, published research is the distribution channel.

### Months 6–9

Control plane alpha. Inventory, policy versioning, drift, evidence export. Price it. Charge someone, even if badly.

### Months 9–12

Decide honestly. Either you have paying design partners and a wedge worth funding, or you have a well-regarded OSS project whose realistic outcome is credibility, hiring leverage, and possibly an acquihire — which, given CB Insights assigning elevated acquisition likelihood across this space, is a legitimate outcome rather than a failure.

### Kill criteria

If after six months no design partner has moved a policy from shadow to enforce, the product is not the problem — the category is, and you should pivot to the services or compliance-evidence business.

---

## Risks that specifically kill this idea

- Platform absorption

  - The clouds and the AI labs ship "good enough" for free inside the runtime everyone already uses.
  - Mitigation: be the cross-runtime, self-hosted, evidence-producing layer they structurally won't build.
- False-positive fatigue

  - One wrongly blocked production action and you're uninstalled.
  - Mitigation: shadow-default, per-rule confidence, human-approval path, and a documented FP rate.
- Liability

  - Who is accountable when your policy blocks a legitimate $2M transaction — or fails to block a malicious one?
  - You need an answer for enterprise legal before your first paid deal.
- Framework churn

  - LangGraph-first is reasonable today, but adapter maintenance is a treadmill.
  - The gateway form factor hedges this.
- Scope as a symptom

  - A doc covering input, context, decisions, tools, outputs, memory, agent-to-agent, and external actions reads to an investor or buyer as "no wedge chosen."
  - Publish the long-term vision as a roadmap, not as the product.

---

## Sharper positioning

Your current one-liner (§22) describes a category. Replace it with something that names the buyer, the failure, and the artifact:

> AgentShield is a self-hosted authorization and provenance layer for AI agents. It tracks where every piece of context came from, blocks untrusted content from becoming a high-authority action, and produces the audit evidence your security team needs to approve the agent for production.

That version implies a buyer (security approver), a mechanism no classifier vendor owns (provenance), a deployment property incumbents can't match (self-hosted, neutral), and a deliverable someone signs off on (evidence).

The engineering thinking in your document is good — genuinely better than a lot of what's shipping. The commercial framing is the part that needs the rewrite: pick the action layer, lead with provenance, default to shadow mode, sell to the person who signs the approval, and fund it with services while the open-source core earns distribution.
