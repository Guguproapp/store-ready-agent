"use strict";

const $ = (id) => document.getElementById(id);
const runSteps = [...document.querySelectorAll("#run-steps li")];
const documentRows = [...document.querySelectorAll("[data-document-name]")];
const taskChoices = [...document.querySelectorAll("[data-task-name]")];
const budgetInputs = [...document.querySelectorAll("[data-budget-item]")];
const budgetLabels = [...document.querySelectorAll("[data-budget-label]")];
const actionIds = ["sample-fill", "submit-plan", "live-run"];
const decisionIds = ["approve", "reject", "defer"];
const decisionLabels = { approved: "核准計畫", rejected: "拒絕計畫", deferred: "延後決定" };
const categoryLabels = { document: "文件", documents: "文件", budget: "預算", budget_data: "預算資料", data: "缺少必要資料", training: "訓練", timeline: "日期", site: "場地與設備", operations: "供應與營運", people: "人員", readiness: "開幕檢查", general: "其他風險" };
const severityLabels = { high: "高風險", medium: "中風險", low: "低風險" };

const focusPresets = {
  retail: {
    summary: "一般零售門市：聚焦店面用途、陳列收銀、商品來源、盤點流程與開幕排班。",
    documents: [
      "店面租約與零售用途同意文件",
      "商業登記申請資料",
      "建物使用與營業場所證明",
      "消防安全設備檢查資料",
      "商品來源與責任保險資料",
      "商品標示與價格檢查表",
      "收銀與發票設定資料",
      "人員緊急聯絡與安全紀錄",
    ],
    tasks: [
      "確認租約與零售用途",
      "完成登記、場所與消防文件盤點",
      "確認用電、網路與保全條件",
      "完成店面動線、陳列與安全工程",
      "完成貨架、收銀與盤點設備測試",
      "完成供應商、商品規格與首批進貨",
      "完成定價、收銀與退換貨流程",
      "完成招募、排班與職責配置",
      "完成商品、服務與安全訓練",
      "完成盤點、試營運與開幕演練",
    ],
    budgets: ["店面水電與基本工程", "貨架、收銀與盤點設備", "登記、消防與保險", "招募、訓練與首批進貨"],
  },
  food: {
    summary: "餐飲與食品店：聚焦餐飲用途、給排水、排煙、食品衛生、冷藏製作設備與備料演練。",
    documents: [
      "店面租約與餐飲用途同意文件",
      "商業登記申請資料",
      "建物使用與營業場所證明",
      "消防安全設備檢查資料",
      "食品業者登錄相關資料",
      "排煙與油脂處理設備資料",
      "從業人員健康與衛生管理紀錄",
      "產品責任保險資料",
    ],
    tasks: [
      "確認租約與餐飲用途",
      "完成登記、場所與消防文件盤點",
      "確認用電、給排水與排煙容量",
      "完成廚房、吧台與顧客動線工程",
      "完成冷藏、製作與收銀設備測試",
      "完成供應商、食材規格與首批備料",
      "完成菜單、定價與食品保存流程",
      "完成招募、排班與職責配置",
      "完成食品安全與服務訓練",
      "完成清潔、試營運與開幕演練",
    ],
    budgets: ["店面水電與排煙工程", "製作、冷藏與收銀設備", "登記、消防與保險", "招募、訓練與開幕備料"],
  },
  personal: {
    summary: "美容與寵物服務：聚焦營業用途、給排水、通風、器具清潔、服務同意書、專業資格與衛生流程。",
    documents: [
      "店面租約與服務用途同意文件",
      "商業登記申請資料",
      "建物使用與營業場所證明",
      "消防安全設備檢查資料",
      "專業資格與技術人員資料",
      "器具清潔消毒與衛生紀錄",
      "服務內容、價格與客戶同意資料",
      "公共意外與責任保險資料",
    ],
    tasks: [
      "確認租約與服務用途",
      "完成登記、場所與消防文件盤點",
      "確認用電、給排水與通風安全",
      "完成接待、服務與清潔動線工程",
      "完成服務、消毒與收銀設備測試",
      "完成耗材供應商與安全庫存設定",
      "完成預約、定價與服務同意流程",
      "完成資格確認、招募與排班配置",
      "完成衛生、安全與客訴處理訓練",
      "完成清潔、試營運與開幕演練",
    ],
    budgets: ["店面水電與通風工程", "服務、消毒與收銀設備", "登記、消防與保險", "招募、訓練與開幕耗材"],
  },
  studio: {
    summary: "教室與運動工作室：聚焦可容納人數、逃生安全、器材檢查、預約課程、師資資格與緊急處理。",
    documents: [
      "場地租約與教學運動用途同意文件",
      "商業登記申請資料",
      "建物使用與可容納人數相關資料",
      "消防逃生與安全設備檢查資料",
      "師資或教練資格資料",
      "器材檢查與維護紀錄",
      "課程、收費與參與同意文件",
      "公共意外與責任保險資料",
    ],
    tasks: [
      "確認租約、用途與場所容量",
      "完成登記、場所與消防文件盤點",
      "確認用電、通風、照明與逃生條件",
      "完成教學、運動與接待動線工程",
      "完成器材、音響與收銀設備測試",
      "完成教材耗材與安全庫存設定",
      "完成預約、課程與收費流程",
      "完成師資資格、招募與排班配置",
      "完成器材安全與緊急應變訓練",
      "完成試課、疏散與開幕演練",
    ],
    budgets: ["場地安全與通風工程", "教學、運動與收銀設備", "登記、消防與保險", "師資、訓練與開幕教材"],
  },
};

const foodStoreTypes = ["街邊咖啡店", "飲料店", "餐廳／小吃店", "烘焙／甜點店", "食品零售店", "攤車／快閃店"];
const personalStoreTypes = ["美容／美髮／美甲工作室", "寵物服務店"];
const studioStoreTypes = ["健身／運動工作室", "教育／才藝教室", "生活服務門市"];
const errorLabels = {
  INVALID_OPENING_DATE: "開幕日期需介於 2000 年 1 月 1 日與 2100 年 12 月 31 日",
  INVALID_STORE_TYPE: "請選擇有效店型",
  INVALID_LOCATION: "請選擇有效地點",
  INVALID_BUDGET: "請輸入有效預算",
  INVALID_BUDGET_ITEMS: "預算明細格式不正確",
  CONTRADICTORY_DOCUMENT_STATUS: "文件狀態互相矛盾",
  CONTRADICTORY_TASK_STATUS: "工作狀態互相矛盾",
  RESCUE_STRATEGY_ALREADY_SELECTED: "這個情境已記錄過選擇",
  APPROVAL_ALREADY_DECIDED: "這項確認已經送出",
  INVALID_RESCUE_TASK: "請選擇可模擬延誤的工作",
  UNKNOWN_RESCUE_TASK: "找不到所選工作，請重新選擇",
  COMPLETED_TASK_CANNOT_BE_SHOCKED: "已完成的工作不能加入延誤情境",
  INVALID_DELAY_WORKDAYS: "請輸入 1 到 60 個延誤工作天",
  INVALID_BUDGET_SHOCK: "請輸入有效的新增費用",
  INVALID_RECOVERY_CAPACITY: "請輸入有效的可追回天數",
  INVALID_RECOVERY_COST: "請輸入有效的每日追回工期費用",
  MONEY_LIMIT_EXCEEDED: "金額超過可接受範圍，請重新輸入",
  CSRF_REQUIRED: "操作階段已失效，請重新整理頁面後再試",
  DEMO_SESSION_REQUIRED: "操作階段已失效，請重新整理頁面後再試",
  PROJECT_SESSION_MISMATCH: "目前無法開啟這份計畫，請重新建立",
  APPROVAL_SESSION_MISMATCH: "目前無法送出這項決定，請重新建立計畫",
  DEMO_ANALYSIS_LIMIT_REACHED: "操作次數已達上限，請稍後再試",
  LIVE_AGENT_DISABLED_FOR_PUBLIC_DEMO: "目前版本未開放雙代理即時分析",
  LIVE_AGENT_TIMEOUT: "雙代理分析逾時，尚未完成，請安全重試",
  RESCUE_STRATEGY_BLOCKED: "這個方案目前不能選擇，請先補齊必要資料",
  RESCUE_SIMULATION_NOT_FOUND: "找不到這次模擬，請重新計算",
  REPORT_NOT_FOUND: "找不到報告，請重新建立計畫",
  PROJECT_NOT_FOUND: "找不到計畫，請重新建立",
};
const auditEventLabels = {
  deterministic_analysis_completed: "系統計算完成",
  human_decision_recorded: "人工決定已記錄",
  rescue_simulation_completed: "開幕救援模擬完成",
  rescue_strategy_recorded: "救援選擇已記錄",
};
const auditDetailLabels = {
  "deterministic tools completed": "系統依固定計算方式完成檢查",
};
const strategyLabels = {
  "守住開幕日": "維持原定開幕日",
  "守住核准預算": "守住預算上限",
  "預算內壓低時程風險": "在預算內降低延誤",
};

const friendlyErrorMessage = (error) => {
  const message = String(error?.message || "").trim();
  return /[\u3400-\u9fff]/.test(message) && !/[A-Z_]{4,}/.test(message)
    ? message
    : "目前無法連線到服務，請稍後再試";
};

let csrfToken = "";
let liveAvailable = false;
let currentProjectId = null;
let approvalId = null;
let pendingDecision = null;
let lastOperation = null;
let currentData = null;
let rescueSimulationId = null;
let selectedStrategyId = null;
let selectedStrategyName = "";
let lastRescueOperation = null;

const demoPayload = {
  store_type: "街邊咖啡店",
  location_city: "台北市",
  location_area: "住宅商圈",
  location: "台北市／住宅商圈",
  budget: 800000,
  opening_date: "2026-10-30",
  acquired_documents: ["店面租約與餐飲用途同意文件", "商業登記申請資料"],
  missing_documents: [
    "建物使用與營業場所證明",
    "消防安全設備檢查資料",
    "食品業者登錄相關資料",
    "排煙與油脂處理設備資料",
  ],
  completed_items: ["確認租約與餐飲用途", "完成登記、場所與消防文件盤點"],
  pending_items: [
    "確認用電、給排水與排煙容量",
    "完成廚房、吧台與顧客動線工程",
    "完成冷藏、製作與收銀設備測試",
    "完成供應商、食材規格與首批備料",
    "完成菜單、定價與食品保存流程",
    "完成招募、排班與職責配置",
    "完成食品安全與服務訓練",
    "完成清潔、試營運與開幕演練",
  ],
  budget_items: [330000, 240000, 100000, 65000],
};

const formatCurrency = (value) => value == null ? "—" : `新臺幣 ${new Intl.NumberFormat("zh-TW", { maximumFractionDigits: 0 }).format(value)} 元`;
const formatDate = (value) => value ? new Intl.DateTimeFormat("zh-TW", { year: "numeric", month: "short", day: "numeric" }).format(new Date(`${value}T00:00:00`)) : "—";
const formatDateTime = (value) => value ? new Intl.DateTimeFormat("zh-TW", { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "—";
const clear = (node) => { while (node.firstChild) node.removeChild(node.firstChild); };
const text = (tag, value, className = "") => { const node = document.createElement(tag); node.textContent = value; if (className) node.className = className; return node; };

const requestJson = async (url, options = {}, timeoutMs = 120000) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    let data;
    try { data = await response.json(); } catch { data = { error: "INVALID_SERVER_RESPONSE" }; }
    if (!response.ok) {
      throw new Error(errorLabels[data.error] || "目前無法完成這項操作，請稍後重試");
    }
    return data;
  } finally { clearTimeout(timer); }
};

let sessionRequest = null;
const resetSession = () => {
  sessionRequest = null;
  csrfToken = "";
};
const ensureSession = () => {
  if (!sessionRequest) {
    sessionRequest = requestJson("/api/session", {}, 5000)
      .then((data) => { csrfToken = data.csrf_token; })
      .catch((error) => {
        resetSession();
        throw error;
      });
  }
  return sessionRequest;
};

const setStatus = (message, type = "") => {
  $("status").textContent = message;
  $("status").className = `status-message ${type}`.trim();
};

const setBusy = (busy) => {
  actionIds.forEach((id) => { $(id).disabled = busy || (id === "live-run" && !liveAvailable); });
  if (currentProjectId) setRescueBusy(busy);
};

const setDecisionDisabled = (disabled) => {
  decisionIds.forEach((id) => { $(id).disabled = disabled || !approvalId; });
};

const setRescueBusy = (busy) => {
  $("simulate-rescue").disabled = busy || !currentProjectId;
  $("live-rescue").disabled = busy || !currentProjectId || !liveAvailable;
  $("rescue-task").disabled = busy || !currentProjectId;
  if (busy) $("adopt-rescue").disabled = true;
};

const setRunProgress = (activeIndex, complete = false) => {
  runSteps.forEach((item, index) => {
    item.classList.toggle("done", complete || index < activeIndex);
    item.classList.toggle("active", !complete && index === activeIndex);
    const marker = item.firstElementChild;
    if (marker) marker.textContent = complete || index < activeIndex ? "✓" : String(index + 1);
  });
};

const setSelectValue = (select, value, fallback = "other") => {
  select.value = [...select.options].some((option) => option.value === String(value)) ? String(value) : fallback;
};

const resolveFocusPreset = (storeType) => {
  if (foodStoreTypes.includes(storeType)) return focusPresets.food;
  if (personalStoreTypes.includes(storeType)) return focusPresets.personal;
  if (studioStoreTypes.includes(storeType)) return focusPresets.studio;
  return focusPresets.retail;
};

const applyFocusPreset = (storeType, reset = true) => {
  const preset = resolveFocusPreset(storeType);
  $("focus-summary").textContent = storeType
    ? preset.summary
    : "選擇店型後，這裡會顯示該店型的八項重要文件與十項開幕工作。";
  documentRows.forEach((row, index) => {
    const name = preset.documents[index];
    row.dataset.documentName = name;
    row.querySelector("span").textContent = name;
    const select = row.querySelector("select");
    select.setAttribute("aria-label", `${name}狀態`);
    if (reset) select.value = "";
  });
  taskChoices.forEach((choice, index) => {
    const name = preset.tasks[index];
    choice.dataset.taskName = name;
    choice.querySelector("span").textContent = name;
    if (reset) choice.querySelector('input[type="checkbox"]').checked = false;
  });
  budgetLabels.forEach((label, index) => { label.textContent = preset.budgets[index]; });
};

const updateGuidedFields = () => {
  const form = $("project-form").elements;
  const customStoreType = form.store_type.value === "other";
  const customLocation = form.location_area.value === "other";
  const customBudget = form.budget_range.value === "custom";
  $("store-type-other-field").hidden = !customStoreType;
  $("location-other-field").hidden = !customLocation;
  $("budget-custom-field").hidden = !customBudget;
  form.store_type_other.required = customStoreType;
  form.location_other.required = customLocation;
  form.budget_custom.required = customBudget;
};

const formPayload = () => {
  const form = new FormData($("project-form"));
  const storeTypeChoice = String(form.get("store_type") || "");
  const customStoreType = String(form.get("store_type_other") || "").trim();
  if (storeTypeChoice === "other" && !customStoreType) throw new Error("請填寫其他店型");

  const cityChoice = String(form.get("location_city") || "");
  const areaChoice = String(form.get("location_area") || "");
  const customLocation = String(form.get("location_other") || "").trim();
  if (areaChoice === "other" && !customLocation) throw new Error("請填寫區域補充");
  const locationParts = [cityChoice];
  if (areaChoice === "other") {
    locationParts.push(customLocation);
  } else locationParts.push(areaChoice);

  const budgetChoice = String(form.get("budget_range") || "");
  const budget = Number(budgetChoice === "custom" ? form.get("budget_custom") : budgetChoice);
  if (!Number.isFinite(budget) || budget <= 0) throw new Error("請選擇或填寫有效的總預算");

  const acquiredDocuments = [];
  const missingDocuments = [];
  documentRows.forEach((row) => {
    const status = row.querySelector("select").value;
    if (status === "acquired") acquiredDocuments.push(row.dataset.documentName);
    if (status === "missing") missingDocuments.push(row.dataset.documentName);
  });

  const completedItems = [];
  const pendingItems = [];
  taskChoices.forEach((choice) => {
    const target = choice.querySelector('input[type="checkbox"]').checked ? completedItems : pendingItems;
    target.push(choice.dataset.taskName);
  });

  const rawBudgetItems = budgetInputs.map((input) => input.value.trim());
  if (rawBudgetItems.some(Boolean) && !rawBudgetItems.every(Boolean)) throw new Error("預算明細請四項都填完整，或全部留白");
  const budgetItems = rawBudgetItems.filter(Boolean).map(Number);
  if (budgetItems.some((item) => !Number.isFinite(item) || item < 0)) throw new Error("預算項目必須是 0 或大於 0 的有效金額");
  const payload = {
    store_type: storeTypeChoice === "other" ? customStoreType : storeTypeChoice,
    location: locationParts.filter(Boolean).join("／"),
    budget,
    opening_date: String(form.get("opening_date") || ""),
    acquired_documents: acquiredDocuments,
    missing_documents: missingDocuments,
    completed_items: completedItems,
    pending_items: pendingItems,
  };
  if (budgetItems.length) payload.budget_items = budgetItems;
  return payload;
};

const setFormPayload = (payload) => {
  const form = $("project-form").elements;
  setSelectValue(form.store_type, payload.store_type);
  form.store_type_other.value = form.store_type.value === "other" ? payload.store_type : "";
  setSelectValue(form.location_city, payload.location_city || "台北市");
  setSelectValue(form.location_area, payload.location_area || "住宅商圈");
  form.location_other.value = "";
  setSelectValue(form.budget_range, payload.budget, "custom");
  form.budget_custom.value = form.budget_range.value === "custom" ? payload.budget : "";
  form.opening_date.value = payload.opening_date;
  applyFocusPreset(payload.store_type, false);
  documentRows.forEach((row) => {
    row.querySelector("select").value = payload.acquired_documents.includes(row.dataset.documentName)
      ? "acquired"
      : payload.missing_documents.includes(row.dataset.documentName) ? "missing" : "na";
  });
  taskChoices.forEach((choice) => {
    choice.querySelector('input[type="checkbox"]').checked = payload.completed_items.includes(choice.dataset.taskName);
  });
  budgetInputs.forEach((input, index) => { input.value = payload.budget_items[index] ?? ""; });
  updateGuidedFields();
};

const renderRisks = (gaps) => {
  const grid = $("risk-grid");
  clear(grid);
  $("risk-count").textContent = `${gaps.length} 項`;
  if (!gaps.length) {
    grid.append(text("div", "目前沒有已知缺口，仍請完成最後確認。", "no-risk"));
    return;
  }
  gaps.forEach((risk) => {
    const item = document.createElement("article");
    item.className = `risk-item ${risk.severity}`;
    const head = document.createElement("div"); head.className = "risk-type";
    head.append(text("span", categoryLabels[risk.kind] || "其他風險"));
    head.append(text("b", severityLabels[risk.severity] || risk.severity, "severity"));
    item.append(head, text("h3", risk.title), text("p", risk.detail));
    grid.append(item);
  });
};

const renderSchedule = (schedule) => {
  const body = $("schedule-body"); clear(body);
  schedule.forEach((task) => {
    const row = document.createElement("tr");
    if (task.critical) row.className = "critical";
    const nameCell = document.createElement("td"); nameCell.append(text("span", task.name, "task-name"));
    const stateCell = document.createElement("td"); stateCell.append(text("span", task.completed ? "已完成" : "待完成", `status-chip ${task.completed ? "completed" : "pending"}`));
    const dependencyCell = text("td", task.depends_on_names.length ? task.depends_on_names.join("、") : "無", "dependency");
    row.append(
      nameCell,
      stateCell,
      dependencyCell,
      text("td", formatDate(task.start_date)),
      text("td", formatDate(task.earliest_completion)),
      text("td", formatDate(task.latest_safe_completion)),
      text("td", task.slack_workdays === 0 ? "0 天 · 關鍵工作" : `${task.slack_workdays} 天`),
      text("td", `${task.duration_days} 天`),
    );
    body.append(row);
  });
};

const populateRescueTasks = (schedule) => {
  const select = $("rescue-task");
  const previous = select.value;
  clear(select);
  schedule.filter((task) => !task.completed).forEach((task) => {
    const option = document.createElement("option");
    option.value = task.task_id;
    option.textContent = `${task.name}｜可延後 ${task.slack_workdays} 天`;
    select.append(option);
  });
  if ([...select.options].some((option) => option.value === previous)) select.value = previous;
  else if ([...select.options].some((option) => option.value === "fitout")) select.value = "fitout";
  select.disabled = !select.options.length;
};

const renderAgents = (data) => {
  clear($("manager-facts")); clear($("reviewer-facts"));
  const live = data.status === "LIVE_AGENT_COMPLETE";
  const localizedLiveSummary = `開店規劃代理已完成分析，共找出 ${data.gaps.length} 項風險與 ${data.missing_documents.length} 項文件缺口，再交由準備度複核代理從原始資料獨立核對。`;
  $("manager").textContent = live ? localizedLiveSummary : "任務、日期、風險與分數已由系統計算完成。";
  [
    `關鍵工作：${data.critical_path.length} 項`,
    `文件缺口：${data.missing_documents.length} 項`,
    `預算差額：${data.budget_data_status === "provided" ? formatCurrency(data.budget_overage) : "尚未提供預算明細"}`,
  ].forEach((item) => $("manager-facts").append(text("li", item)));

  if (live && data.reviewer_report) {
    $("reviewer").textContent = "準備度複核代理只讀取原始資料重新計算，沒有直接採用規劃代理的摘要。";
    [
      `獨立分數：${data.reviewer_report.score}/100`,
      "計算方式：只依原始資料獨立重算",
      `獨立預算差額：${data.reviewer_report.budget_total == null ? "尚未提供預算明細" : formatCurrency(data.reviewer_report.budget_overage)}`,
    ].forEach((item) => $("reviewer-facts").append(text("li", item)));
    const scoreDiff = data.reviewer_report.score - data.score;
    $("agreement-state").textContent = scoreDiff === 0 ? "結論一致" : "存在差異";
    $("agent-difference").textContent = scoreDiff === 0 ? "兩位代理使用相同原始資料，分別計算後得到相同分數。" : `複核代理與主結果相差 ${Math.abs(scoreDiff)} 分，請確認差異。`;
  } else {
    $("reviewer").textContent = "準備度複核代理已依原始資料完成可再次核對的計算。";
    $("reviewer-facts").append(text("li", "狀態：計算核對完成"), text("li", "系統計算：已完成"));
    $("agreement-state").textContent = "計算核對完成";
    $("agent-difference").textContent = "目前結果由系統計算產生；啟用雙代理後，會再提供另一份獨立判讀。";
  }
  $("agent-section-kicker").textContent = live ? "雙代理複核" : "系統計算與複核";
  $("agents-title").textContent = live ? "雙代理結論與差異" : "計算結果與核對";
};

const rescueBlockerLabels = {
  BUDGET_DETAILS_REQUIRED: "需要完整預算明細",
  RECOVERY_QUOTE_REQUIRED: "請先填寫每天追回工期的費用",
  RECOVERY_CAPACITY_INSUFFICIENT: "可追回天數不足以守住原開幕日",
  DIRECT_SHOCK_EXCEEDS_BUDGET: "新增費用已超過預算上限",
  NO_WITHIN_BUDGET_OPTION: "目前沒有足夠預算可縮短延誤",
};

const rescuePayload = () => {
  const form = new FormData($("rescue-form"));
  const quote = String(form.get("recovery_cost_per_day") || "").trim();
  return {
    task_id: String(form.get("task_id") || ""),
    delay_workdays: Number(form.get("delay_workdays")),
    direct_budget_shock: Number(form.get("direct_budget_shock")),
    max_recoverable_workdays: Number(form.get("max_recoverable_workdays")),
    recovery_cost_per_day: quote === "" ? null : Number(quote),
  };
};

const setRescueStatus = (message, type = "") => {
  $("rescue-status").textContent = message;
  $("rescue-status").className = `rescue-status ${type}`.trim();
};

const renderRescue = (data) => {
  rescueSimulationId = data.simulation_id;
  selectedStrategyId = null;
  selectedStrategyName = "";
  $("rescue-result").hidden = false;
  $("rescue-baseline-date").textContent = formatDate(currentData.project.opening_date);
  $("rescue-shock-date").textContent = formatDate(data.scenario_opening_date);
  $("rescue-delay-copy").textContent = data.projected_delay_workdays
    ? `若不處理，延後 ${data.projected_delay_workdays} 個工作天`
    : "目前延誤仍在可延後天數內";
  const taskNames = new Map(currentData.schedule.map((task) => [task.task_id, task.name]));
  const affectedNames = data.affected_task_ids.map((taskId) => taskNames.get(taskId) || "受影響工作");
  $("rescue-affected-count").textContent = `${affectedNames.length} 項`;
  $("rescue-affected-copy").textContent = affectedNames.length ? affectedNames.join("、") : "沒有後續工作被推移";

  const grid = $("strategy-grid");
  clear(grid);
  data.strategies.forEach((strategy) => {
    const card = document.createElement("label");
    card.className = `strategy-card ${strategy.selectable ? "" : "blocked"}`.trim();
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "rescue-strategy";
    radio.value = strategy.strategy_id;
    radio.disabled = !strategy.selectable;
    radio.addEventListener("change", () => {
      selectedStrategyId = strategy.strategy_id;
      selectedStrategyName = strategyLabels[strategy.name] || "救援方案";
      $("adopt-rescue").disabled = false;
      $("rescue-choice-state").textContent = `已選擇：${selectedStrategyName}；尚未確認記錄`;
    });
    const metrics = document.createElement("div");
    metrics.className = "strategy-metric";
    const values = [
      ["預計開幕", formatDate(strategy.resulting_opening_date)],
      ["追回天數／剩餘延誤", `${strategy.recovered_workdays}／${strategy.residual_delay_workdays} 天`],
      ["預算結果", strategy.budget_total == null ? "尚未提供預算明細" : formatCurrency(strategy.budget_total)],
      ["超出預算", strategy.budget_overage == null ? "目前無法計算" : formatCurrency(strategy.budget_overage)],
    ];
    values.forEach(([label, value]) => {
      const item = document.createElement("div");
      item.append(text("span", label), text("strong", value));
      metrics.append(item);
    });
    const blockers = strategy.blockers.map((item) => rescueBlockerLabels[item] || "目前缺少必要資料");
    const status = blockers.length
      ? `不可選：${blockers.join("；")}`
      : strategy.budget_status === "over"
        ? "需要你確認：結果會超出預算上限"
        : "資料完整，可供你比較";
    card.append(radio, text("h4", strategyLabels[strategy.name] || "救援方案"), metrics, text("p", status, "strategy-status"));
    grid.append(card);
  });

  const live = data.status === "LIVE_RESCUE_COMPLETE";
  if (live && data.reviewer_report && data.reviewer_report.hash_match === true) {
    $("rescue-review-badge").textContent = "雙代理計算一致";
    $("rescue-manager").textContent = "開店規劃代理已比較三種救援選擇，再交給複核代理。";
    $("rescue-reviewer").textContent = "準備度複核代理已依相同原始資料重新計算，兩份結果一致。";
  } else {
    $("rescue-review-badge").textContent = "計算核對完成";
    $("rescue-manager").textContent = "已依情境計算三種救援方案。";
    $("rescue-reviewer").textContent = "已依相同原始資料完成計算核對。";
  }
  $("adopt-rescue").disabled = true;
  $("rescue-choice-state").textContent = data.strategies.some((item) => item.selectable)
    ? "尚未選擇方案"
    : "資料不足或沒有可行方案；請調整情境後重新計算";
  const modeText = live ? "雙代理已分別計算並確認結果一致" : "系統計算與核對完成";
  setRescueStatus(`完成：${modeText}。原計畫保持不變。`, "success");
};

const executeRescue = async (mode) => {
  if (!currentProjectId) return;
  const payload = rescuePayload();
  const endpoint = mode === "live" ? `/api/live-rescue/${encodeURIComponent(currentProjectId)}` : `/api/rescue/${encodeURIComponent(currentProjectId)}`;
  lastRescueOperation = () => executeRescue(mode);
  rescueSimulationId = null;
  selectedStrategyId = null;
  selectedStrategyName = "";
  $("rescue-result").hidden = true;
  $("rescue-choice-state").textContent = "重新計算中；先前方案不可送出";
  setRescueBusy(true);
  $("rescue-retry").hidden = true;
  setRescueStatus(mode === "live" ? "開店規劃代理正在模擬，準備度複核代理將從原始情境獨立計算…" : "正在重新計算工作順序、可延後天數、開幕日與三種方案…");
  try {
    await ensureSession();
    const data = await requestJson(endpoint, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: JSON.stringify(payload) }, mode === "live" ? 120000 : 10000);
    renderRescue(data);
  } catch (error) {
    resetSession();
    const timedOut = error.name === "AbortError";
    setRescueStatus(timedOut ? "救援模擬逾時：沒有標示成功，輸入已保留，可安全重試。" : `救援模擬失敗：${friendlyErrorMessage(error)}`, "error");
    $("rescue-retry").hidden = false;
    $("rescue-task").focus();
  } finally { setRescueBusy(false); }
};

const renderReport = (data) => {
  $("report-project").textContent = `${data.project.store_type}｜${data.project.location}`;
  $("report-meta").textContent = `預定開幕 ${formatDate(data.project.opening_date)} · 預計總預算 ${formatCurrency(data.project.budget)}`;
  $("report-score").textContent = `${data.score}/100${data.score_status === "provisional" ? "（暫定）" : ""}`;
  $("report-critical").textContent = `${data.critical_path.length} 項`;
  $("report-risks").textContent = `${data.gaps.length} 項`;
  const conclusion = data.score >= 80 ? "目前準備度良好；請完成最後確認與現場檢查。" : data.score >= 60 ? "仍有關鍵缺口，建議依關鍵路徑逐項關閉後再確認開幕日。" : "目前存在顯著準備風險；請先處理高風險文件、預算與關鍵工作。";
  $("report-conclusion").textContent = data.score_status === "provisional" ? `此為排除未知預算構面後的暫定分數。${conclusion}` : conclusion;
  const link = $("report-link");
  link.hidden = !data.report_available;
  if (data.report_available) link.href = `/api/report/${encodeURIComponent(data.project_id)}`;
};

const render = (data) => {
  currentData = data;
  currentProjectId = data.project_id;
  approvalId = data.approval_request.id || null;
  $("empty-state").hidden = true;
  $("result").hidden = false;
  const score = Number(data.score);
  $("score").textContent = `${score}/100`;
  $("score-progress").value = score;
  $("score-progress").textContent = `${score}%`;
  $("score-ring").className = `score-ring ${score >= 80 ? "good" : score >= 60 ? "caution" : "risk"}`;
  const readinessText = score >= 80 ? "接近可開幕" : score >= 60 ? "需要補強" : "高風險待處理";
  $("readiness-label").textContent = data.score_status === "provisional" ? `暫定分數 · ${readinessText}` : readinessText;
  $("completion").textContent = `${data.task_completion_percent}%`;
  $("completion-note").textContent = `${data.schedule.filter((task) => task.completed).length}/${data.schedule.length} 項已完成`;
  if (data.budget_data_status === "provided") {
    $("budget-state").textContent = data.budget_overage > 0 ? `超支 ${formatCurrency(data.budget_overage)}` : `餘額 ${formatCurrency(data.budget_remaining)}`;
    $("budget-note").textContent = `使用者輸入明細合計 ${formatCurrency(data.budget_total)}`;
  } else {
    $("budget-state").textContent = "尚未提供預算明細";
    $("budget-note").textContent = "請填寫各項預估金額，系統不會代填";
  }
  $("delay-state").textContent = String(data.delayed_days);
  $("source").textContent = `來源：${data.status === "LIVE_AGENT_COMPLETE" ? "雙代理複核與系統計算" : "系統計算"}`;
  renderRisks(data.gaps);
  renderSchedule(data.schedule);
  populateRescueTasks(data.schedule);
  rescueSimulationId = null;
  selectedStrategyId = null;
  $("rescue-result").hidden = true;
  $("rescue-retry").hidden = true;
  setRescueStatus("原計畫已保留，不會因模擬而更改。你現在可以加入一個延誤情境。", "success");
  setRescueBusy(false);
  renderAgents(data);
  renderReport(data);
  setDecisionDisabled(false);
  $("decision-state").textContent = approvalId ? "等待你的決定" : "本次沒有待核准項目";
  loadAudit();
  $("dashboard").scrollIntoView({ behavior: "smooth", block: "start" });
};

const loadAudit = async () => {
  if (!currentProjectId) return;
  const list = $("audit-log");
  try {
    const data = await requestJson(`/api/project/${encodeURIComponent(currentProjectId)}/audit`, {}, 5000);
    clear(list);
    if (!data.events.length) { list.append(text("li", "尚無操作紀錄。")); return; }
    data.events.forEach((event) => {
      const item = document.createElement("li");
      const eventLabel = auditEventLabels[event.event_type] || "系統事件";
      const detailLabel = auditDetailLabels[event.detail] || "重要動作已完成並留下紀錄";
      item.append(text("time", formatDateTime(event.created_at)), text("span", `${eventLabel}｜${detailLabel}`));
      list.append(item);
    });
  } catch { clear(list); list.append(text("li", "操作紀錄暫時無法載入。")); }
};

const execute = async (mode) => {
  if (!$("project-form").checkValidity()) {
    $("project-form").reportValidity();
    return;
  }
  let payload;
  try { payload = formPayload(); } catch (error) { setStatus(error.message, "error"); return; }
  const endpoint = mode === "live" ? "/api/live-analyze" : "/api/analyze";
  lastOperation = () => execute(mode);
  setBusy(true); setDecisionDisabled(true); $("retry").hidden = true;
  $("run-mode").textContent = mode === "live" ? "雙代理分析" : "系統計算";
  setRunProgress(0); setStatus("正在驗證原始資料與安全邊界…");
  try {
    await ensureSession();
    setRunProgress(1); setStatus(mode === "live" ? "開店規劃代理正在分析，完成後由準備度複核代理依原始資料重新計算…" : "正在計算工作順序、完成期限、關鍵工作與風險…");
    const data = await requestJson(endpoint, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: JSON.stringify(payload) }, mode === "live" ? 120000 : 10000);
    setRunProgress(3); render(data); setRunProgress(4, true);
    setStatus(mode === "live" ? "完成：兩位代理已分別分析，系統計算也已完成。" : "完成：計畫、系統計算與報告都已建立。", "success");
  } catch (error) {
    resetSession();
    const timedOut = error.name === "AbortError";
    setStatus(timedOut ? "執行逾時：沒有標示成功，請安全重試。" : `執行失敗：${friendlyErrorMessage(error)}`, "error");
    $("retry").hidden = false;
    setRunProgress(1);
  } finally { setBusy(false); }
};

const askDecision = (decision) => {
  pendingDecision = decision;
  $("confirm-copy").textContent = `你即將送出決定「${decisionLabels[decision]}」。送出後系統不會替你修改，而且同一項決定不能重複提交。`;
  $("decision-dialog").showModal();
  $("confirm-decision").focus();
};

const submitDecision = async (event) => {
  event.preventDefault();
  if (!approvalId || !pendingDecision) return;
  setDecisionDisabled(true); setStatus("正在記錄你的決定…");
  try {
    const result = await requestJson(`/api/approval/${approvalId}`, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: JSON.stringify({ decision: pendingDecision }) }, 10000);
    $("decision-dialog").close();
    $("decision-state").textContent = `已記錄：${decisionLabels[result.decision]}`;
    setStatus(`你的決定已記錄：${decisionLabels[result.decision]}`, "success");
    approvalId = null; pendingDecision = null; await loadAudit();
  } catch (error) { setStatus(`決定失敗：${friendlyErrorMessage(error)}`, "error"); setDecisionDisabled(false); }
};

const askRescueSelection = () => {
  if (!rescueSimulationId || !selectedStrategyId) return;
  $("rescue-confirm-copy").textContent = `你將記錄選擇「${selectedStrategyName}」。這不會自動修改開幕日、預算或工作，而且同一情境只能記錄一次。`;
  $("rescue-dialog").showModal();
  $("confirm-rescue").focus();
};

const submitRescueSelection = async (event) => {
  event.preventDefault();
  if (!rescueSimulationId || !selectedStrategyId) return;
  $("adopt-rescue").disabled = true;
  setRescueStatus("正在記錄你的方案選擇；不會套用到原計畫…");
  try {
    const result = await requestJson(`/api/rescue-decision/${encodeURIComponent(rescueSimulationId)}`, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: JSON.stringify({ strategy_id: selectedStrategyId }) }, 10000);
    $("rescue-dialog").close();
    $("rescue-choice-state").textContent = `已記錄：${selectedStrategyName}（尚未套用）`;
    setRescueStatus("已記錄你的選擇；原計畫、日期與預算都沒有變更。", "success");
    [...document.querySelectorAll('input[name="rescue-strategy"]')].forEach((item) => { item.disabled = true; });
    rescueSimulationId = result.simulation_id;
    await loadAudit();
  } catch (error) {
    setRescueStatus(`方案記錄失敗：${friendlyErrorMessage(error)}`, "error");
    $("adopt-rescue").disabled = false;
  }
};

$("sample-fill").addEventListener("click", () => { setFormPayload(demoPayload); setStatus("示範資料已帶入，可直接開始分析。"); $("project-form").elements.store_type.focus(); });
$("store-type").addEventListener("change", (event) => {
  updateGuidedFields();
  applyFocusPreset(event.target.value, true);
});
[$("location-city"), $("location-area"), $("budget-range")].forEach((control) => control.addEventListener("change", updateGuidedFields));
$("project-form").addEventListener("submit", (event) => { event.preventDefault(); execute("offline"); });
$("rescue-form").addEventListener("submit", (event) => { event.preventDefault(); executeRescue("offline"); });
$("live-run").addEventListener("click", () => execute("live"));
$("live-rescue").addEventListener("click", () => executeRescue("live"));
$("retry").addEventListener("click", () => { if (lastOperation) lastOperation(); });
$("rescue-retry").addEventListener("click", () => { if (lastRescueOperation) lastRescueOperation(); });
$("approve").addEventListener("click", () => askDecision("approved"));
$("reject").addEventListener("click", () => askDecision("rejected"));
$("defer").addEventListener("click", () => askDecision("deferred"));
$("confirm-decision").addEventListener("click", submitDecision);
$("cancel-decision").addEventListener("click", () => { pendingDecision = null; });
$("adopt-rescue").addEventListener("click", askRescueSelection);
$("confirm-rescue").addEventListener("click", submitRescueSelection);
$("print-report").addEventListener("click", () => window.print());

applyFocusPreset("", false);
updateGuidedFields();

requestJson("/ready", {}, 5000).then((data) => {
  liveAvailable = Boolean(data.live_enabled);
  $("live-run").hidden = !liveAvailable;
  $("live-rescue").hidden = !liveAvailable;
  $("live-run").disabled = !liveAvailable;
  $("live-rescue").disabled = !liveAvailable || !currentProjectId;
  $("live-run").title = liveAvailable ? "執行雙代理分析" : "";
  $("service-state").textContent = "服務就緒";
  $("service-state").classList.add("ready");
}).catch(() => { $("service-state").textContent = "服務暫時無法連線"; setStatus("服務尚未就緒，請稍後重試。", "error"); });
