# Judge Testing Guide

StoreReady Agent is a Taiwan-first, end-to-end pre-opening readiness workspace for the Professional Agents track. Traditional Chinese and English are two interfaces for the same Taiwan opening workflow; English does not switch the product to another country's rules.

## Fast path — approximately two minutes

1. Open [the Traditional Chinese demo](https://store-ready-agent.onrender.com/) or [the English interface](https://store-ready-agent.onrender.com/en).
2. Confirm no login or personal data is requested.
3. Select **Load example** and review the guided dropdowns, document statuses, and task checklist.
4. Select **Create and analyze plan**.
5. Review the readiness score, task completion, budget state, delay forecast, risks, dependencies, deadlines, and complete critical path.
6. Open **Opening Rescue Simulator**. Keep the example shock—Fit-out delayed by four workdays, TWD 50,000 unexpected cost, four recoverable workdays, and TWD 5,000 recovery cost per day—and run the simulation.
7. Compare the three strategies. The exact deterministic outcomes are: protect date = October 30 / TWD 805,000 / four recovered days; protect budget = November 5 / TWD 785,000 / four delayed days; lowest risk = November 2 / TWD 800,000 / three recovered days.
8. Select a rescue strategy and confirm it. Verify that this records a one-shot human choice but does not modify the original launch plan.
9. Compare the Launch Manager and Readiness Reviewer panels. The public route displays reproducible rule results and never fabricates an AI Reviewer result; the verified Bedrock evidence is documented separately.
10. Select **Approve**, **Reject**, or **Defer**. Confirm the second-step dialog and verify that all decision controls become disabled after submission.
11. Check the Audit Log, print-ready report, and JSON report download.

No login or credentials are required. Use only the built-in fictional example or other fictional information.

## What to evaluate

- The workflow is complete from brief to plan, independent review, human checkpoint, report, and audit trail.
- Dates, workdays, dependencies, critical path, task slack, rescue-policy outcomes, budget totals, document gaps, delay days, completion rate, and score come from deterministic tools.
- The rescue simulation is a non-destructive branch: source, shock, and result snapshots are hash-bound, and a mismatch disables strategy selection.
- Launch Manager and Readiness Reviewer are distinct Strands Agent objects.
- Reviewer tools reconstruct the immutable original project snapshot and cannot write state.
- The human-decision operation is not available to either Agent.
- Missing budget detail stays unknown and produces a clearly labelled provisional score.
- The responsive interface works at desktop, tablet, and mobile sizes without page-level horizontal overflow.

## Live Agent evidence

The public demo disables the metered Live endpoint to prevent unbounded AWS use. The submitted source contains the complete Strands/Bedrock path and the safe verification script. The project team ran the final candidate with Strands Agents SDK 1.55.0 and Amazon Nova Lite in `ap-southeast-2`; two distinct Agents completed all seven required tool calls. See `docs/LIVE_EVIDENCE.md`.

## Local installation

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/run_demo.py
```

Open `http://127.0.0.1:8000`, select **Load example**, and run the deterministic analysis.

## Safety notes

- The current product scope is physical-store opening in Taiwan. It is not a universal regulatory engine.
- This is a hackathon DEMO, not legal, financial, permit, or government-submission advice.
- City and county selection does not mean every current local requirement is encoded; confirm requirements with the competent local authority and qualified professionals in Taiwan.
- It does not send messages, purchase services, sign contracts, submit permits, or approve decisions automatically.
- The public demo stores only fictional test data and expires DEMO records.
- Opening-day operations and post-opening analytics are roadmap ideas, not claimed submission features.
