# Devpost Draft — StoreReady Agent

Track: **Professional Agents**

## One-line summary

StoreReady Agent turns a physical store's Taiwan opening brief into a traceable launch plan with deterministic risk calculations and an independent readiness review.

## Inspiration and problem

Physical-store owners coordinate permits, contractors, equipment, staff training, budgets, and a hard opening date. These are dependent activities, but the information is usually scattered across messages, notes, and spreadsheets. A normal chatbot can suggest a checklist, but it does not reliably calculate the schedule, prove the critical path, or protect the owner's final decision.

StoreReady Agent treats pre-opening readiness as one complete professional workflow rather than an open-ended conversation. It is Taiwan-first: Traditional Chinese and English are two interfaces for the same Taiwan opening workflow, not two country rule sets.

## What it does

The demo accepts all eight brief fields: fictional store type, one of Taiwan's twenty-two cities or counties, area type, budget, opening date, acquired and missing documents, completed and pending work. Launch Manager organizes the brief and requests a Readiness Reviewer check. Deterministic Python tools calculate workdays, dependencies, critical path, document gaps, budget risk, training gaps and readiness score. The responsive workspace then exposes risks, Agent differences, human approvals, an Audit Log, and downloadable or print-ready reports.

Its signature feature is the **Opening Rescue Simulator**. When a task slips or an unexpected cost appears, the owner can model that shock without changing the approved baseline. The system computes the task's last safe date and available slack, then returns exactly three comparable strategies—protect the opening date, protect the budget, or minimize combined risk. Each card shows the resulting date, delay, recovery work, budget outcome, feasibility, and blockers. The two Agents independently verify immutable source, shock, and result hashes before a human can record one strategy.

The end-to-end result is:

`brief → backward launch plan → deterministic checks → independent Agent review → human decision → report and audit trail`

Opening-day operations and post-opening analytics are intentionally outside this submission. The demonstrated workflow is complete within the specific problem it claims to solve.

## Why two agents

The Manager is optimized for orchestration and explanation. The Reviewer is read-only and re-checks the original data independently, so the system can show agreement or disagreement instead of blindly repeating one model's summary.

The Reviewer receives the immutable original project snapshot, not the Manager's calculations. This separation makes the second Agent a genuine review boundary rather than a second narration of the same answer.

## How it was built

- Python 3.11+
- Strands Agents SDK 1.55.0
- Amazon Bedrock with Amazon Nova Lite
- Deterministic Python planning, readiness, and opening-rescue tools
- SQLite persistence
- Standard-library HTTP server
- Responsive HTML, CSS, and JavaScript interface

The Launch Manager uses deterministic planning tools and invokes Readiness Reviewer as an Agent-as-Tool. The Reviewer independently invokes critical-path, gap, report, and rescue-verification tools. Model-cycle, output-token, timeout, retry, input-size, Session, request-rate, hash-integrity, and SQLite-retention limits all fail closed.

## Human control

The product only creates approval requests. A human must explicitly approve, reject or defer. No agent can call the human-decision operation.

The UI requires a second confirmation and accepts only one decision for each request. The report and Audit Log then reflect that human action.

## What makes the implementation trustworthy

- Deterministic tools own dates, workdays, dependencies, critical path, slack, delay, recovery capacity, rescue budgets, missing documents, completion rate, and score.
- Unknown budget details remain unknown. The UI clearly labels the reweighted score provisional instead of treating missing data as zero.
- The Reviewer reconstructs and recalculates from the original brief and has no write tools.
- Untrusted content is rendered as text, mutation endpoints require Session and CSRF protection, and public Live execution defaults off.
- Health and readiness checks never invoke the model.

## Current evidence boundary

On 2026-09-12, the real integration ran with Strands Agents SDK 1.55.0 and Amazon Nova Lite in `ap-southeast-2`. Launch Manager completed four required tool calls, including Readiness Reviewer as an Agent-as-Tool. Reviewer independently completed three deterministic checks from the original immutable input snapshot. The evidence records IDs, hashes, latency, cycles, tokens and stop reasons without prompts, credentials or AWS identity.

The bilingual judge surface is a public-safe DEMO. Its public Live endpoint is disabled by default to prevent unmetered AWS use; the saved Live evidence and local integration test demonstrate the Bedrock path without exposing credentials or an unlimited paid endpoint.

The verified bilingual submission package passed 78 automated tests, Ruff, formatting, Mypy, Python compilation, JavaScript syntax, wheel packaging, dependency checks, and secret scans. The responsive UI passed exact Browser QA at 1440×900, 768×1024, and 390×844 without page-level horizontal overflow; the English workflow and Safari loading checks also passed.

## Challenges

The hardest part was separating model judgment from facts that must be reproducible. We moved every date, dependency, budget, document, delay, and scoring result into deterministic tools. We also had to make the Reviewer independently reconstruct source data while keeping the Manager-to-Reviewer interaction inside the Strands Agent workflow and within strict cycle and timeout limits.

Another challenge was keeping the public demo useful without exposing an unmetered Bedrock endpoint. The public-safe mode demonstrates the deterministic product flow and truthfully marks Live AI as not run, while the repository includes the complete Live path and verification script.

## Accomplishments

- Two genuinely distinct Strands Agents with isolated responsibilities
- Seven verified real tool calls through Amazon Bedrock
- Backward scheduling and a complete deterministic critical path
- Opening Rescue Simulator with last-safe dates, task slack, and three deterministic response strategies
- Immutable source, shock, and result hashes independently checked by the Reviewer
- Independent immutable-source Reviewer recomputation
- Human-only approve, reject, and defer boundary
- Responsive product UI, downloadable report, and Audit Log
- Reproducible public-source export with secret and local-path checks

## What we learned

Reliable professional Agents need more than prompts. They need deterministic sources of truth, bounded execution, explicit write permissions, honest missing-data states, independent review, and a human checkpoint where business authority matters.

## What's next

After the hackathon, the same safety architecture could support verified Taiwan local-requirement updates, holiday calendars, richer project templates, and—only as separately tested modules—other-country rule packs, opening-day operations, and post-opening improvement tracking. The current submission is not a universal regulatory engine and does not claim those future features.

## New work and disclosure

The project was created during the 2026 submission period. Work in this package includes the deterministic planner, SQLite schema, two-agent orchestration, human-decision boundary, web DEMO, tests and evidence. Standard open-source dependencies include Python, Strands Agents SDK, boto3/botocore and development test tools. OpenAI Codex assisted with implementation, test generation, debugging, copy editing, and read-only review under the entrant's product direction. The entrant retained all product, safety, publication, and submission decisions. No pre-existing commercial product, customer code, customer data, or private third-party source was incorporated.

## Submission timing

Official Devpost deadline: September 14, 2026 at 5:00 PM PDT, equivalent to September 15, 2026 at 08:00 Asia/Taipei. Source: `https://agentsforhumans.devpost.com/rules` (verified 2026-09-12). Target submission buffer remains September 14 at 20:00 Asia/Taipei, subject to the owner's final approval.

## Scope exclusions

No payment, contract, permit submission, external messaging, automatic purchasing, automatic booking, real customer data, OCR, RAG, vector database, real-time maps or unnecessary account system.
