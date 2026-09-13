# StoreReady Agent — English Demo Video Script

Target runtime: 4 minutes 35 seconds. Hard limit: 5 minutes.

## 0:00–0:25 — The problem

**Screen:** Title, then a small store owner surrounded by disconnected notes for permits, contractors, equipment, training, and budget.

**Narration:**

Opening a physical store is a dependency problem disguised as a checklist. Documents, equipment, contractors, staff training, and budget all compete against one hard opening date. Store owners often know what needs to happen, but not what blocks what, what is already late, or which decision still requires them.

## 0:25–0:50 — The product

**Screen:** Open StoreReady Agent and select the built-in example.

**Narration:**

StoreReady Agent is an end-to-end pre-opening readiness workspace built for small-business owners. It turns one store brief into a traceable launch plan, deterministic risk calculations, an independent AI review, and explicit human decisions. This demo uses fictional data and is not a production permit or purchasing service.

## 0:50–1:25 — Eight-part brief

**Screen:** Select “帶入示範資料” (Load example). Show the guided store, location, budget, and date dropdowns; document-status choices; task checklist; and optional budget detail.

**Narration:**

The owner provides the eight parts of the opening brief through guided choices instead of composing long text. For this fictional coffee shop, the lease is complete, two documents are missing, several tasks remain, and the detailed spend leaves a sixty-five-thousand New Taiwan dollar buffer. The system keeps missing information unknown instead of inventing values.

## 1:25–2:05 — Launch Manager and deterministic tools

**Screen:** Run the analysis and show the progress stages, task table, deadlines, and critical-path marker.

**Narration:**

The Launch Manager interprets the brief, creates a launch plan, and selects deterministic Python tools. Those tools—not the language model—own dates, workdays, dependencies, the full critical path, budget totals, document gaps, delay days, completion rate, and readiness score. The plan schedules backward from the opening date, so the deadline is a real constraint.

## 2:05–2:45 — Independent Reviewer Agent

**Screen:** Show the Manager and Reviewer cards and their agreement indicator. Briefly overlay the non-secret Live evidence summary.

**Narration:**

The Manager then calls a separate Readiness Reviewer as an Agent-as-Tool. The Reviewer does not receive the Manager's calculated answer. It reloads the immutable original brief, independently reruns the critical-path, gap, and report tools, and remains read-only. In our verified Amazon Bedrock run, the two distinct Strands Agents completed all seven required tool calls.

## 2:45–3:40 — Signature feature: Opening Rescue Simulator

**Screen:** Show task slack and last-safe dates. Open Opening Rescue Simulator, apply a four-workday fit-out delay and a fifty-thousand New Taiwan dollar shock, then compare the three strategy cards. Select “Protect budget” and show the confirmation dialog.

**Narration:**

The signature feature answers the question a checklist cannot: what should I do when the plan breaks? StoreReady calculates every task's last safe date and slack. A four-day delay on this critical fit-out task reaches opening day immediately. The simulator does not overwrite the plan. It creates an immutable shock scenario and computes exactly three choices: protect the date, protect the budget, or minimize combined risk. Each choice exposes its resulting opening date, recovery days, total budget, feasibility, and blockers. The Reviewer independently recomputes the source, shock, and result hashes before a human can choose.

## 3:40–4:10 — Human checkpoints

**Screen:** Confirm the rescue strategy and show that the original plan is unchanged. Then choose “Defer” on the approval request, submit it, and show disabled decision buttons plus the new Audit Log events.

**Narration:**

The Agents can request a decision, but they cannot make it. Approve, reject, and defer are protected by a one-shot human confirmation. The decision operation is not available as a model tool, and every important action is recorded in the Audit Log.

## 4:10–4:35 — Report, safety, and impact

**Screen:** Show the printable report, JSON download, architecture diagram, mobile layout, and final title card.

**Narration:**

The result is a readable readiness report that the owner can print or download. Sessions, request rates, and fictional SQLite data are bounded, and the public demo disables paid Live calls by default. StoreReady Agent makes owners dramatically better at the judgment-heavy work they already do: deciding what must happen next so opening day does not arrive before the store is ready.

## Recording checklist

- Keep the final export below 5:00.
- Record at 1440×900 or 1920×1080 and verify mobile separately.
- Use English narration, English subtitles, or both.
- Do not show AWS account identifiers, credentials, prompts, terminal history, personal browser data, or local filesystem paths.
- Demonstrate only functionality that is present in the submitted repository.
- End with the public repository URL and free judge-testing URL after the owner authorizes publication.
