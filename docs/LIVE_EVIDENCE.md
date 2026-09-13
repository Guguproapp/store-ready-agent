# Verified Strands and Amazon Bedrock Evidence

Final product-source verification completed on 2026-09-12 with:

- Strands Agents SDK 1.55.0
- Amazon Nova Lite (`amazon.nova-lite-v1:0`)
- AWS Region `ap-southeast-2`
- Distinct Agent IDs for Launch Manager and Readiness Reviewer
- Manager completed `create_launch_plan`, `calculate_critical_path`, `detect_readiness_gaps`, and `readiness_reviewer`
- Reviewer independently completed `calculate_critical_path`, `detect_readiness_gaps`, and `generate_readiness_report`
- Reviewer input reconstructed from the immutable original fictional project snapshot
- `record_decision` absent from all model tool lists
- Manager capped at 6 model cycles; Reviewer capped at 5
- Model output capped at 1,024 tokens per cycle
- Overall invocation timeout of 120 seconds and one controlled tool retry

The stored internal test evidence records tool-use IDs, statuses, latency, output hashes, token totals, and stop reasons. It deliberately excludes prompts, complete model responses, AWS identity, credentials, cookies, and secrets.

## Opening Rescue verification

The final candidate also completed a separate real Bedrock run for the Opening Rescue Simulator on 2026-09-13 (Asia/Taipei):

- Launch Manager called `simulate_opening_rescue` and then invoked Readiness Reviewer as an Agent-as-Tool.
- Readiness Reviewer independently called `simulate_opening_rescue`, `verify_rescue_hashes`, and `generate_rescue_review` from server-bound immutable snapshots.
- Source, shock, and result hashes matched; the original project was not modified.
- The two rescue Agent IDs were distinct, neither Agent had a state-write, strategy-selection, or human-decision tool, and the rescue run enforced four Manager cycles and six Reviewer cycles.
- The evidence document records only safe metadata and explicitly reports `secrets_recorded: false`.

The public-source package includes the implementation and repeatable verification script but excludes internal machine-specific governance evidence. Authorized reviewers can reproduce the Live check using the standard AWS credential chain:

The recorded preflight digest maps to the verified agent-core revision. Later release work changed presentation, bilingual UI, tests, documentation, and packaging only; the Manager/Reviewer implementation, deterministic domain and service logic, storage boundary, credential guard, and `scripts/preflight_live.py` remain byte-identical to that verified agent-core revision. The broader aggregate digest also includes UI and test files, so it is not presented as a current release-package digest. Package integrity is reported separately through `PUBLIC_MANIFEST.txt` and the release ZIP hash.

```bash
AWS_PROFILE=your-authorized-profile AWS_REGION=ap-southeast-2 \
  .venv/bin/python scripts/preflight_live.py
```

The default web DEMO does not call Bedrock. Live web execution requires the explicit `STORE_READY_ENABLE_LIVE=1` environment flag.
