# StoreReady Agent

StoreReady Agent is an end-to-end pre-opening readiness workspace for physical-store owners. It turns a messy opening brief into a dependency-aware launch plan, deterministic risk calculations, an independent AI review, explicit human approvals, and an auditable readiness report.

Built for the **Professional Agents** track of the AWS Agents for Humans Hackathon with the Strands Agents SDK and Amazon Bedrock.

> **DEMO ONLY:** Use fictional data. This is not a production service and does not submit permits, send messages, make purchases, sign contracts, or approve decisions on a user's behalf.

[Open the bilingual judge demo](https://predictions-windsor-hope-sophisticated.trycloudflare.com/) · [English interface](https://predictions-windsor-hope-sophisticated.trycloudflare.com/en) · [Judge testing guide](docs/JUDGING_GUIDE.md) · [Architecture](docs/ARCHITECTURE.md)

![StoreReady Agent architecture](docs/architecture-diagram.svg)

## The problem

Opening a physical store requires owners to coordinate documents, contractors, equipment, staff training, budgets, and a hard opening date. These items depend on each other, but are often managed across notes and spreadsheets. The result is late surprises and unclear human decisions.

StoreReady Agent handles this **pre-opening readiness workflow end to end**:

1. Accept all eight parts of a fictional store brief.
2. Build a backward-scheduled task plan and dependency graph.
3. Calculate the complete critical path, document gaps, budget status, delay forecast, and readiness score with deterministic Python tools.
4. Ask a separate read-only Reviewer Agent to reconstruct the original input and recalculate independently.
5. Present agreement or disagreement, risks, and items requiring a human decision.
6. Let the human approve, reject, or defer through a one-shot confirmation flow.
7. Produce an auditable report and event log.

## Signature feature — Opening Rescue Simulator

Most opening assistants stop at a checklist. StoreReady calculates each task's earliest
completion, last safe completion date, and workday slack. An owner can then shock one
unfinished task with a delay and direct budget change, add real recovery capacity and a
quoted recovery cost, and compare exactly three deterministic strategies:

- protect the original opening date;
- protect the approved budget;
- minimize remaining schedule risk without exceeding that budget.

Every card shows the resulting opening date, recovered and residual workdays, known budget
total and blockers. Unknown budget or quote data stays unknown and disables unsafe choices.
The scenario is stored separately from the baseline with source, shock and result hashes.
Launch Manager explains the trade-offs; Readiness Reviewer independently recomputes the
same immutable scenario. A human radio selection plus confirmation records a choice but
never changes the plan, spends money or performs an external action.

The project intentionally focuses on the complete pre-opening workflow. Opening-day operations and post-opening business analytics are future roadmap items, not unimplemented claims in this submission.

## Two-Agent architecture

- **Launch Manager Agent:** interprets the brief, invokes planning, critical-path and gap tools, then calls the Reviewer as an Agent-as-Tool.
- **Readiness Reviewer Agent:** receives the immutable original project snapshot, independently reruns the deterministic checks, and cannot mutate project state.

Dates, workdays, dependencies, critical paths, latest safe dates, slack, delay days,
budget totals, rescue policies, missing documents, completion rate, and readiness score
are never left to model arithmetic. Decision operations are not exposed as model tools.

The verified Live path uses Strands Agents SDK 1.55.0 and Amazon Nova Lite in `ap-southeast-2`. The tracked, non-secret evidence shows two distinct Agent IDs and seven required successful tool calls. See [Live evidence summary](docs/LIVE_EVIDENCE.md).

## Run locally

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/run_demo.py
```

Open `http://127.0.0.1:8000`. The default public-safe mode never invokes Bedrock;
`/api/live-analyze` and `/api/live-rescue/{project_id}` return HTTP 503.

## Judge deployment

The repository includes `render.yaml` for a free public judge DEMO on Render. It binds the
existing Python server to Render's assigned port, keeps Live Bedrock execution disabled, uses
`/health`, and disables automatic redeployment. Render Free services may sleep after inactivity
and have an ephemeral filesystem, so fictional DEMO sessions can reset after a restart. No real
or durable data belongs in this deployment.

For an authorized local Live verification, use the standard AWS credential chain. Never place credentials in this repository:

```bash
AWS_PROFILE=launchpilot AWS_REGION=ap-southeast-2 \
  .venv/bin/python scripts/preflight_live.py
```

`STORE_READY_ENABLE_LIVE=1` must be explicitly set before the web Live endpoint can invoke Bedrock. Health and readiness endpoints never call the model.

## Quality and safety

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src scripts tests
.venv/bin/python -m compileall -q src scripts tests
```

The verified bilingual candidate passes 74 automated tests. The responsive interface passed
Browser QA at 1440×900, 768×1024, and 390×844 with no page-level horizontal overflow; the
English entry also passed complete workflow QA and Safari loading checks. Mutation endpoints
require a same-site Session and CSRF token;
decisions are one-shot; Sessions and fictional SQLite data expire after two hours; request and
storage limits fail closed.

## Submission assets

- [Architecture explanation](docs/ARCHITECTURE.md)
- [Architecture diagram](docs/architecture-diagram.svg)
- [Devpost draft](docs/DEVPOST_DRAFT.md)
- [English five-minute video script](docs/VIDEO_SCRIPT_EN.md)
- [Judge testing guide](docs/JUDGING_GUIDE.md)
- [Apache License 2.0](LICENSE)

## 中文說明

開店就緒助手（內部代號 LaunchPilot）是 AWS Agents for Humans Hackathon 的 Professional Agents 新專案。它把虛構實體店的開幕資料轉為倒排工作計畫、完整關鍵路徑、文件／預算／時程風險、準備度分數及待人工決定事項。

目前是隔離、noindex 的 DEMO，不是 Production，不使用正式店家或個人資料。

介面把完整八項開店輸入整理成三段式引導：店家條件使用下拉選單，文件逐項選擇狀態，工作直接勾選完成與否；預算明細只有取得估價後才需展開。使用者選擇店型後，畫面會帶入該類店家專用的八項文件、十項工作與四項預算分類，涵蓋用途與登記、場地設備、供應與營運、人員訓練及開幕演練。這十項工作會實際進入完成率、相依關係、關鍵路徑、截止日與救援模擬，不是只顯示在畫面上的樣品清單。

分析後顯示準備度、文件／預算／時程風險、任務相依與截止日，以及「開幕保命線」衝擊模擬。店主可比較守住日期、守住預算、預算內壓低時程風險三種方案，再自行確認；人工智慧不會自動套用。

## 架構與邊界

產品只有兩個 Strands 代理：

- 開店規劃代理：理解輸入、依序呼叫計畫／關鍵路徑／缺口工具，再呼叫準備度複核代理。
- 準備度複核代理：從原始不可變快照重新取得資料並獨立重算，全程唯讀。

日期、工作天、相依關係、完整關鍵路徑、預算、文件缺口、完成率與分數全部由可測試的 Python 工具計算。`record_decision` 不在模型工具清單；只有 HTTP 應用服務能記錄真人的核准、拒絕或延後。

預算明細是選填資料；未提供時會顯示「預算明細不足」，總額、超支與餘額保持未知，系統不會代填或推測。準備度會標示為「暫定分數」，排除未知的預算構面後重新正規化其餘已知構面，不會把未知預算暗算成 0%。無法對應到內建工作分解的「尚未完成事項」會列為「待辦尚未排程」風險，不會被靜默忽略。開幕日期限於 2000-01-01 至 2100-12-31，超出範圍會回傳受控錯誤。

## 安裝

需要 Python 3.11+。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

## 環境變數

- `AWS_PROFILE`：AWS CLI／SDK 設定檔名稱，不含值。
- `AWS_REGION`、`AWS_DEFAULT_REGION`：Bedrock 區域。
- `STORE_READY_MODEL_ID`：模型 ID，預設 `amazon.nova-lite-v1:0`。
- `STORE_READY_ENABLE_LIVE`：只有值為 `1` 才啟用會產生 AWS 用量的 Live API；公開 DEMO 必須保持未設定。
- `STORE_READY_HOST`、`STORE_READY_PORT`：本機伺服器位址與連接埠。

不得把 Password、Access Key、Cookie、Token、MFA 或其他 Secret 寫入 Repo、指令紀錄或報告。

## 真正 Bedrock 預檢

```bash
AWS_PROFILE=launchpilot AWS_REGION=ap-southeast-2 \
  .venv/bin/python scripts/preflight_live.py
```

2026-09-12 已用 Strands Agents SDK 1.55.0 與 Amazon Nova Lite 真正執行兩個不同 Agent 及七項必要工具呼叫。公開版的去識別化證據摘要見 [`docs/LIVE_EVIDENCE.md`](docs/LIVE_EVIDENCE.md)；內部原始證據不隨公開包發布。失敗、逾時或缺工具一律 fail-closed，不會改用離線結果冒充成功。

## 啟動 DEMO

公開／分享測試預設模式（Live API 關閉）：

```bash
.venv/bin/python scripts/run_demo.py
```

Repo 根目錄另附 `render.yaml`，可建立免費、固定 `onrender.com` 網址的評審 DEMO。免費服務閒置後可能休眠，重新啟動時 SQLite 虛構資料會清空；這符合無登入的比賽展示用途，但不是商用 Production。

只供受控本機 Live QA：

```bash
STORE_READY_ENABLE_LIVE=1 AWS_PROFILE=launchpilot AWS_REGION=ap-southeast-2 \
  .venv/bin/python scripts/run_demo.py
```

端點另含 `POST /api/rescue/{project_id}`、`POST /api/live-rescue/{project_id}` 與 `POST /api/rescue-decision/{simulation_id}`。分析、模擬及真人選擇必須帶 Session 與 CSRF，且只能操作同一 DEMO Session 建立的專案。公開 DEMO 的兩個 Live 端點都回傳 `503 LIVE_AGENT_DISABLED_FOR_PUBLIC_DEMO`，不會觸發 Bedrock。

## 測試

```bash
.venv/bin/pytest -q --junitxml=/tmp/store-ready-agent-pytest.xml
.venv/bin/python scripts/sanitize_junit.py /tmp/store-ready-agent-pytest.xml
.venv/bin/ruff check src scripts tests
.venv/bin/ruff format --check src scripts tests
.venv/bin/mypy src scripts tests
.venv/bin/python -m compileall -q src scripts tests
git diff --check
```

JUnit 去識別化步驟會移除 hostname 並正規化本機家目錄；提交前必須確認產物沒有任何作業系統的使用者家目錄、`.local` 或 `hostname=`。

完整部署與回復方式見 `docs/DEPLOYMENT_RUNBOOK.md`。已知限制：週末以外的各地國定假日尚未納入；自訂待辦會標示為未排程但不會自動推測工期或相依關係；DEMO 無正式登入與多租戶；公開測試版不提供付費 Live 呼叫。
