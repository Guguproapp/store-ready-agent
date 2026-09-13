"use strict";

const $ = (id) => document.getElementById(id);
const runSteps = [...document.querySelectorAll("#run-steps li")];
const documentRows = [...document.querySelectorAll("[data-document-name]")];
const taskChoices = [...document.querySelectorAll("[data-task-name]")];
const budgetInputs = [...document.querySelectorAll("[data-budget-item]")];
const budgetLabels = [...document.querySelectorAll("[data-budget-label]")];
const actionIds = ["sample-fill", "submit-plan", "live-run"];
const decisionIds = ["approve", "reject", "defer"];
const decisionLabels = {
  approved: "Approve plan",
  rejected: "Reject plan",
  deferred: "Defer decision",
};
const categoryLabels = {
  document: "Documents",
  documents: "Documents",
  budget: "Budget",
  budget_data: "Budget details",
  data: "Missing information",
  training: "Training",
  timeline: "Dates",
  site: "Site and equipment",
  operations: "Supply and operations",
  people: "People",
  readiness: "Launch review",
  general: "Other risk",
};
const severityLabels = { high: "High risk", medium: "Medium risk", low: "Low risk" };

const canonicalStoreTypes = {
  "Street coffee shop": "街邊咖啡店",
  "Beverage shop": "飲料店",
  "Restaurant or food stall": "餐廳／小吃店",
  "Bakery or dessert shop": "烘焙／甜點店",
  "Food retail store": "食品零售店",
  "General retail store": "一般零售門市",
  "Beauty, hair, or nail studio": "美容／美髮／美甲工作室",
  "Pet service store": "寵物服務店",
  "Fitness or sports studio": "健身／運動工作室",
  "Education or arts classroom": "教育／才藝教室",
  "Lifestyle service store": "生活服務門市",
  "Food cart or pop-up store": "攤車／快閃店",
};
const displayStoreTypes = Object.fromEntries(
  Object.entries(canonicalStoreTypes).map(([display, canonical]) => [canonical, display]),
);

const focusPresets = {
  retail: {
    summary: "General retail: focus on permitted use, displays and checkout, product sourcing, inventory, and opening shifts.",
    documents: [
      ["Lease and retail-use consent", "店面租約與零售用途同意文件"],
      ["Business registration materials", "商業登記申請資料"],
      ["Building-use and business-premises proof", "建物使用與營業場所證明"],
      ["Fire safety equipment inspection records", "消防安全設備檢查資料"],
      ["Product sourcing and liability insurance records", "商品來源與責任保險資料"],
      ["Product labeling and price checklist", "商品標示與價格檢查表"],
      ["Checkout and invoice setup records", "收銀與發票設定資料"],
      ["Staff emergency contact and safety records", "人員緊急聯絡與安全紀錄"],
    ],
    tasks: [
      ["Confirm lease and retail use", "確認租約與零售用途"],
      ["Review registration, premises, and fire documents", "完成登記、場所與消防文件盤點"],
      ["Confirm power, internet, and security conditions", "確認用電、網路與保全條件"],
      ["Complete layout, display, and safety work", "完成店面動線、陳列與安全工程"],
      ["Test shelving, checkout, and inventory equipment", "完成貨架、收銀與盤點設備測試"],
      ["Complete suppliers, product specifications, and initial stock", "完成供應商、商品規格與首批進貨"],
      ["Complete pricing, checkout, and return procedures", "完成定價、收銀與退換貨流程"],
      ["Complete hiring, shifts, and responsibilities", "完成招募、排班與職責配置"],
      ["Complete product, service, and safety training", "完成商品、服務與安全訓練"],
      ["Complete inventory, soft opening, and launch drill", "完成盤點、試營運與開幕演練"],
    ],
    budgets: [
      "Basic utilities and fit-out",
      "Shelving, checkout, and inventory equipment",
      "Registration, fire safety, and insurance",
      "Hiring, training, and initial stock",
    ],
  },
  food: {
    summary: "Food and beverage: focus on permitted use, utilities, exhaust, food hygiene, cold storage, production equipment, and opening prep.",
    documents: [
      ["Lease and food-service use consent", "店面租約與餐飲用途同意文件"],
      ["Business registration materials", "商業登記申請資料"],
      ["Building-use and business-premises proof", "建物使用與營業場所證明"],
      ["Fire safety equipment inspection records", "消防安全設備檢查資料"],
      ["Food business registration materials", "食品業者登錄相關資料"],
      ["Exhaust and grease-control equipment records", "排煙與油脂處理設備資料"],
      ["Staff health and hygiene records", "從業人員健康與衛生管理紀錄"],
      ["Product liability insurance records", "產品責任保險資料"],
    ],
    tasks: [
      ["Confirm lease and food-service use", "確認租約與餐飲用途"],
      ["Review registration, premises, and fire documents", "完成登記、場所與消防文件盤點"],
      ["Confirm power, water, drainage, and exhaust capacity", "確認用電、給排水與排煙容量"],
      ["Complete kitchen, service counter, and customer flow work", "完成廚房、吧台與顧客動線工程"],
      ["Test cold storage, production, and checkout equipment", "完成冷藏、製作與收銀設備測試"],
      ["Complete suppliers, ingredient specifications, and opening stock", "完成供應商、食材規格與首批備料"],
      ["Complete menu, pricing, and food storage procedures", "完成菜單、定價與食品保存流程"],
      ["Complete hiring, shifts, and responsibilities", "完成招募、排班與職責配置"],
      ["Complete food safety and service training", "完成食品安全與服務訓練"],
      ["Complete cleaning, soft opening, and launch drill", "完成清潔、試營運與開幕演練"],
    ],
    budgets: [
      "Utilities and exhaust work",
      "Production, cold storage, and checkout equipment",
      "Registration, fire safety, and insurance",
      "Hiring, training, and opening stock",
    ],
  },
  personal: {
    summary: "Beauty and pet services: focus on permitted use, utilities, ventilation, sanitation, service consent, qualifications, and hygiene.",
    documents: [
      ["Lease and service-use consent", "店面租約與服務用途同意文件"],
      ["Business registration materials", "商業登記申請資料"],
      ["Building-use and business-premises proof", "建物使用與營業場所證明"],
      ["Fire safety equipment inspection records", "消防安全設備檢查資料"],
      ["Professional qualification and technician records", "專業資格與技術人員資料"],
      ["Tool sanitation and hygiene records", "器具清潔消毒與衛生紀錄"],
      ["Service, pricing, and customer consent records", "服務內容、價格與客戶同意資料"],
      ["Public accident and liability insurance records", "公共意外與責任保險資料"],
    ],
    tasks: [
      ["Confirm lease and service use", "確認租約與服務用途"],
      ["Review registration, premises, and fire documents", "完成登記、場所與消防文件盤點"],
      ["Confirm power, water, drainage, and ventilation safety", "確認用電、給排水與通風安全"],
      ["Complete reception, service, and cleaning flow work", "完成接待、服務與清潔動線工程"],
      ["Test service, sanitation, and checkout equipment", "完成服務、消毒與收銀設備測試"],
      ["Set suppliers and safety stock for consumables", "完成耗材供應商與安全庫存設定"],
      ["Complete booking, pricing, and service consent procedures", "完成預約、定價與服務同意流程"],
      ["Complete qualification checks, hiring, and shifts", "完成資格確認、招募與排班配置"],
      ["Complete hygiene, safety, and complaint training", "完成衛生、安全與客訴處理訓練"],
      ["Complete cleaning, soft opening, and launch drill", "完成清潔、試營運與開幕演練"],
    ],
    budgets: [
      "Utilities and ventilation work",
      "Service, sanitation, and checkout equipment",
      "Registration, fire safety, and insurance",
      "Hiring, training, and opening supplies",
    ],
  },
  studio: {
    summary: "Classrooms and sports studios: focus on capacity, exits, equipment checks, bookings, instructor qualifications, and emergencies.",
    documents: [
      ["Lease and teaching or sports-use consent", "場地租約與教學運動用途同意文件"],
      ["Business registration materials", "商業登記申請資料"],
      ["Building-use and capacity records", "建物使用與可容納人數相關資料"],
      ["Fire exit and safety equipment inspection records", "消防逃生與安全設備檢查資料"],
      ["Instructor or coach qualification records", "師資或教練資格資料"],
      ["Equipment inspection and maintenance records", "器材檢查與維護紀錄"],
      ["Course, pricing, and participant consent records", "課程、收費與參與同意文件"],
      ["Public accident and liability insurance records", "公共意外與責任保險資料"],
    ],
    tasks: [
      ["Confirm lease, permitted use, and capacity", "確認租約、用途與場所容量"],
      ["Review registration, premises, and fire documents", "完成登記、場所與消防文件盤點"],
      ["Confirm power, ventilation, lighting, and exits", "確認用電、通風、照明與逃生條件"],
      ["Complete teaching, activity, and reception flow work", "完成教學、運動與接待動線工程"],
      ["Test equipment, audio, and checkout systems", "完成器材、音響與收銀設備測試"],
      ["Set teaching supplies and safety stock", "完成教材耗材與安全庫存設定"],
      ["Complete booking, course, and payment procedures", "完成預約、課程與收費流程"],
      ["Complete instructor qualifications, hiring, and shifts", "完成師資資格、招募與排班配置"],
      ["Complete equipment safety and emergency training", "完成器材安全與緊急應變訓練"],
      ["Complete trial class, evacuation, and launch drill", "完成試課、疏散與開幕演練"],
    ],
    budgets: [
      "Site safety and ventilation work",
      "Teaching, activity, and checkout equipment",
      "Registration, fire safety, and insurance",
      "Instructors, training, and opening materials",
    ],
  },
};

const foodStoreTypes = new Set([
  "Street coffee shop",
  "Beverage shop",
  "Restaurant or food stall",
  "Bakery or dessert shop",
  "Food retail store",
  "Food cart or pop-up store",
]);
const personalStoreTypes = new Set(["Beauty, hair, or nail studio", "Pet service store"]);
const studioStoreTypes = new Set([
  "Fitness or sports studio",
  "Education or arts classroom",
  "Lifestyle service store",
]);

const allDocumentLabels = new Map();
const allTaskLabels = new Map();
Object.values(focusPresets).forEach((preset) => {
  preset.documents.forEach(([display, canonical]) => allDocumentLabels.set(canonical, display));
  preset.tasks.forEach(([display, canonical]) => allTaskLabels.set(canonical, display));
});

const errorLabels = {
  INVALID_OPENING_DATE: "Opening date must be between January 1, 2000 and December 31, 2100",
  INVALID_STORE_TYPE: "Choose a valid store type",
  INVALID_LOCATION: "Choose a valid location",
  INVALID_BUDGET: "Enter a valid budget",
  INVALID_BUDGET_ITEMS: "Budget details are not valid",
  CONTRADICTORY_DOCUMENT_STATUS: "Document statuses contradict each other",
  CONTRADICTORY_TASK_STATUS: "Task statuses contradict each other",
  RESCUE_STRATEGY_ALREADY_SELECTED: "A choice has already been recorded for this scenario",
  APPROVAL_ALREADY_DECIDED: "This approval has already been submitted",
  INVALID_RESCUE_TASK: "Choose a task that can be delayed",
  UNKNOWN_RESCUE_TASK: "The selected task could not be found. Choose it again",
  COMPLETED_TASK_CANNOT_BE_SHOCKED: "A completed task cannot be used in a delay scenario",
  INVALID_DELAY_WORKDAYS: "Enter 1 to 60 delay workdays",
  INVALID_BUDGET_SHOCK: "Enter a valid added cost",
  INVALID_RECOVERY_CAPACITY: "Enter a valid number of recoverable days",
  INVALID_RECOVERY_COST: "Enter a valid cost per recovered day",
  MONEY_LIMIT_EXCEEDED: "The amount is above the allowed limit",
  CSRF_REQUIRED: "This session has expired. Refresh the page and try again",
  DEMO_SESSION_REQUIRED: "This session has expired. Refresh the page and try again",
  PROJECT_SESSION_MISMATCH: "This plan cannot be opened in the current session. Build it again",
  APPROVAL_SESSION_MISMATCH: "This decision cannot be submitted. Build the plan again",
  DEMO_ANALYSIS_LIMIT_REACHED: "The session limit has been reached. Try again later",
  LIVE_AGENT_DISABLED_FOR_PUBLIC_DEMO: "Live dual-agent analysis is unavailable in this version",
  LIVE_AGENT_TIMEOUT: "Dual-agent analysis timed out and was not marked complete. Retry safely",
  RESCUE_STRATEGY_BLOCKED: "This option is unavailable until required information is complete",
  RESCUE_SIMULATION_NOT_FOUND: "This simulation could not be found. Calculate it again",
  REPORT_NOT_FOUND: "This report could not be found. Build the plan again",
  PROJECT_NOT_FOUND: "This plan could not be found. Build it again",
};
const auditEventLabels = {
  deterministic_analysis_completed: "System calculation completed",
  human_decision_recorded: "Human decision recorded",
  rescue_simulation_completed: "Opening delay simulation completed",
  rescue_strategy_recorded: "Recovery choice recorded",
};
const auditDetailLabels = {
  "deterministic tools completed": "The system completed all checks using fixed calculations",
};
const strategyLabels = {
  "守住開幕日": "Keep the planned opening date",
  "守住核准預算": "Stay within the approved budget",
  "預算內壓低時程風險": "Reduce delay within budget",
};
const rescueBlockerLabels = {
  BUDGET_DETAILS_REQUIRED: "Complete budget details are required",
  RECOVERY_QUOTE_REQUIRED: "Enter the cost per recovered day",
  RECOVERY_CAPACITY_INSUFFICIENT: "There are not enough recoverable days to keep the opening date",
  DIRECT_SHOCK_EXCEEDS_BUDGET: "The added cost is above the budget limit",
  NO_WITHIN_BUDGET_OPTION: "There is not enough budget to reduce this delay",
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
  store_type: "Street coffee shop",
  location_city: "Taipei City",
  location_area: "Residential commercial area",
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
  budget_items: [330000, 240000, 100000, 65000],
};

const formatCurrency = (value) =>
  value == null
    ? "—"
    : `TWD ${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value)}`;
const counted = (value, singular, plural = `${singular}s`) =>
  `${value} ${Number(value) === 1 ? singular : plural}`;
const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      }).format(new Date(`${value}T00:00:00`))
    : "—";
const formatDateTime = (value) =>
  value
    ? new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date(value))
    : "—";
const clear = (node) => {
  while (node.firstChild) node.removeChild(node.firstChild);
};
const text = (tag, value, className = "") => {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
};
const translateTaskName = (name) => allTaskLabels.get(name) || "Other launch task";
const translateDocumentName = (name) => allDocumentLabels.get(name) || "Other required document";
const translatePayload = (payload) => ({
  ...payload,
  store_type: canonicalStoreTypes[payload.store_type] || payload.store_type,
});
const friendlyErrorMessage = (error) => {
  const message = String(error?.message || "").trim();
  return message && !/[\u3400-\u9fff]/.test(message) && !/[A-Z_]{4,}/.test(message)
    ? message
    : "The service is unavailable. Try again shortly";
};

const requestJson = async (url, options = {}, timeoutMs = 120000) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    let data;
    try {
      data = await response.json();
    } catch {
      data = { error: "INVALID_SERVER_RESPONSE" };
    }
    if (!response.ok) {
      throw new Error(errorLabels[data.error] || "The service could not complete this action. Try again");
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
};

let sessionRequest = null;
const resetSession = () => {
  sessionRequest = null;
  csrfToken = "";
};
const ensureSession = () => {
  if (!sessionRequest) {
    sessionRequest = requestJson("/api/session", {}, 5000)
      .then((data) => {
        csrfToken = data.csrf_token;
      })
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
  actionIds.forEach((id) => {
    $(id).disabled = busy || (id === "live-run" && !liveAvailable);
  });
  if (currentProjectId) setRescueBusy(busy);
};
const setDecisionDisabled = (disabled) => {
  decisionIds.forEach((id) => {
    $(id).disabled = disabled || !approvalId;
  });
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
  select.value = [...select.options].some((option) => option.value === String(value))
    ? String(value)
    : fallback;
};
const resolveFocusPreset = (storeType) => {
  if (foodStoreTypes.has(storeType)) return focusPresets.food;
  if (personalStoreTypes.has(storeType)) return focusPresets.personal;
  if (studioStoreTypes.has(storeType)) return focusPresets.studio;
  return focusPresets.retail;
};
const applyFocusPreset = (storeType, reset = true) => {
  const preset = resolveFocusPreset(storeType);
  $("focus-summary").textContent = storeType
    ? preset.summary
    : "Choose a store type to load its eight essential documents and ten opening tasks.";
  documentRows.forEach((row, index) => {
    const [display, canonical] = preset.documents[index];
    row.dataset.documentName = canonical;
    row.querySelector("span").textContent = display;
    const select = row.querySelector("select");
    select.setAttribute("aria-label", `${display} status`);
    if (reset) select.value = "";
  });
  taskChoices.forEach((choice, index) => {
    const [display, canonical] = preset.tasks[index];
    choice.dataset.taskName = canonical;
    choice.querySelector("span").textContent = display;
    if (reset) choice.querySelector('input[type="checkbox"]').checked = false;
  });
  budgetLabels.forEach((label, index) => {
    label.textContent = preset.budgets[index];
  });
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
  if (storeTypeChoice === "other" && !customStoreType) throw new Error("Enter the other store type");
  const cityChoice = String(form.get("location_city") || "");
  const areaChoice = String(form.get("location_area") || "");
  const customLocation = String(form.get("location_other") || "").trim();
  if (areaChoice === "other" && !customLocation) {
    throw new Error("Enter the area details");
  }
  const locationParts = [cityChoice];
  if (areaChoice === "other") {
    locationParts.push(customLocation);
  } else locationParts.push(areaChoice);
  const budgetChoice = String(form.get("budget_range") || "");
  const budget = Number(budgetChoice === "custom" ? form.get("budget_custom") : budgetChoice);
  if (!Number.isFinite(budget) || budget <= 0) throw new Error("Choose or enter a valid total budget");
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
    const target = choice.querySelector('input[type="checkbox"]').checked
      ? completedItems
      : pendingItems;
    target.push(choice.dataset.taskName);
  });
  const rawBudgetItems = budgetInputs.map((input) => input.value.trim());
  if (rawBudgetItems.some(Boolean) && !rawBudgetItems.every(Boolean)) {
    throw new Error("Complete all four budget details or leave all four blank");
  }
  const budgetItems = rawBudgetItems.filter(Boolean).map(Number);
  if (budgetItems.some((item) => !Number.isFinite(item) || item < 0)) {
    throw new Error("Each budget item must be zero or a positive amount");
  }
  const payload = translatePayload({
    store_type: storeTypeChoice === "other" ? customStoreType : storeTypeChoice,
    location: locationParts.filter(Boolean).join(" / "),
    budget,
    opening_date: String(form.get("opening_date") || ""),
    acquired_documents: acquiredDocuments,
    missing_documents: missingDocuments,
    completed_items: completedItems,
    pending_items: pendingItems,
  });
  if (budgetItems.length) payload.budget_items = budgetItems;
  return payload;
};

const setFormPayload = (payload) => {
  const form = $("project-form").elements;
  setSelectValue(form.store_type, payload.store_type);
  form.store_type_other.value = form.store_type.value === "other" ? payload.store_type : "";
  setSelectValue(form.location_city, payload.location_city || "Taipei City");
  setSelectValue(form.location_area, payload.location_area || "Residential commercial area");
  form.location_other.value = "";
  setSelectValue(form.budget_range, payload.budget, "custom");
  form.budget_custom.value = form.budget_range.value === "custom" ? payload.budget : "";
  form.opening_date.value = payload.opening_date;
  applyFocusPreset(payload.store_type, false);
  documentRows.forEach((row) => {
    row.querySelector("select").value = payload.acquired_documents.includes(row.dataset.documentName)
      ? "acquired"
      : payload.missing_documents.includes(row.dataset.documentName)
        ? "missing"
        : "na";
  });
  taskChoices.forEach((choice) => {
    choice.querySelector('input[type="checkbox"]').checked = payload.completed_items.includes(
      choice.dataset.taskName,
    );
  });
  budgetInputs.forEach((input, index) => {
    input.value = payload.budget_items[index] ?? "";
  });
  updateGuidedFields();
};

const gapCopy = (risk) => {
  if (risk.kind === "document") {
    const names = String(risk.detail || "")
      .split("、")
      .filter(Boolean)
      .map(translateDocumentName);
    return { title: "Missing documents", detail: names.join(", ") || "Required documents are missing" };
  }
  if (risk.kind === "budget_data") {
    return { title: "Missing budget details", detail: "Itemized estimates are required before budget overrun can be calculated" };
  }
  if (risk.kind === "budget") {
    const amount = Number(String(risk.detail || "").replace(/[^0-9.-]/g, ""));
    return { title: "Budget overrun", detail: Number.isFinite(amount) ? `Over budget by ${formatCurrency(amount)}` : "The itemized total is above the approved budget" };
  }
  if (risk.kind === "training") {
    return { title: "Training incomplete", detail: translateTaskName(risk.detail) };
  }
  if (risk.kind === "data") {
    return { title: "Pending work not scheduled", detail: "Some pending items do not match the focused opening plan" };
  }
  return { title: "Readiness risk", detail: "Review the source data and confirm the required next action" };
};

const renderRisks = (gaps) => {
  const grid = $("risk-grid");
  clear(grid);
  $("risk-count").textContent = `${gaps.length} ${gaps.length === 1 ? "item" : "items"}`;
  if (!gaps.length) {
    grid.append(text("div", "No known gaps were found. Complete the final human review before opening.", "no-risk"));
    return;
  }
  gaps.forEach((risk) => {
    const copy = gapCopy(risk);
    const item = document.createElement("article");
    item.className = `risk-item ${risk.severity}`;
    const head = document.createElement("div");
    head.className = "risk-type";
    head.append(text("span", categoryLabels[risk.kind] || "Other risk"));
    head.append(text("b", severityLabels[risk.severity] || "Risk", "severity"));
    item.append(head, text("h3", copy.title), text("p", copy.detail));
    grid.append(item);
  });
};

const renderSchedule = (schedule) => {
  const body = $("schedule-body");
  clear(body);
  schedule.forEach((task) => {
    const row = document.createElement("tr");
    if (task.critical) row.className = "critical";
    const nameCell = document.createElement("td");
    nameCell.append(text("span", translateTaskName(task.name), "task-name"));
    const stateCell = document.createElement("td");
    stateCell.append(
      text(
        "span",
        task.completed ? "Completed" : "Pending",
        `status-chip ${task.completed ? "completed" : "pending"}`,
      ),
    );
    const dependencies = task.depends_on_names.length
      ? task.depends_on_names.map(translateTaskName).join(", ")
      : "None";
    row.append(
      nameCell,
      stateCell,
      text("td", dependencies, "dependency"),
      text("td", formatDate(task.start_date)),
      text("td", formatDate(task.earliest_completion)),
      text("td", formatDate(task.latest_safe_completion)),
      text(
        "td",
        task.slack_workdays === 0
          ? "0 days · Critical task"
          : counted(task.slack_workdays, "day"),
      ),
      text("td", counted(task.duration_days, "day")),
    );
    body.append(row);
  });
};

const populateRescueTasks = (schedule) => {
  const select = $("rescue-task");
  const previous = select.value;
  clear(select);
  schedule
    .filter((task) => !task.completed)
    .forEach((task) => {
      const option = document.createElement("option");
      option.value = task.task_id;
      option.textContent = `${translateTaskName(task.name)} | ${counted(task.slack_workdays, "delay-allowance day")}`;
      select.append(option);
    });
  if ([...select.options].some((option) => option.value === previous)) select.value = previous;
  else if ([...select.options].some((option) => option.value === "fitout")) select.value = "fitout";
  select.disabled = !select.options.length;
};

const renderAgents = (data) => {
  clear($("manager-facts"));
  clear($("reviewer-facts"));
  const live = data.status === "LIVE_AGENT_COMPLETE";
  $("manager").textContent = live
    ? `The Launch Manager Agent found ${data.gaps.length} risks and ${data.missing_documents.length} document gaps, then sent the original data to the reviewer for an independent check.`
    : "The system calculated tasks, dates, risks, and the readiness score.";
  [
    counted(data.critical_path.length, "critical task"),
    counted(data.missing_documents.length, "missing document"),
    `Budget difference: ${data.budget_data_status === "provided" ? formatCurrency(data.budget_overage) : "Itemized estimates not provided"}`,
  ].forEach((item) => $("manager-facts").append(text("li", item)));
  if (live && data.reviewer_report) {
    $("reviewer").textContent = "The Readiness Reviewer Agent recalculated from the original data without accepting the manager summary.";
    [
      `Independent score: ${data.reviewer_report.score}/100`,
      "Method: independent recalculation from source data",
      `Independent budget difference: ${data.reviewer_report.budget_total == null ? "Itemized estimates not provided" : formatCurrency(data.reviewer_report.budget_overage)}`,
    ].forEach((item) => $("reviewer-facts").append(text("li", item)));
    const scoreDifference = data.reviewer_report.score - data.score;
    $("agreement-state").textContent = scoreDifference === 0 ? "Conclusions match" : "Difference found";
    $("agent-difference").textContent =
      scoreDifference === 0
        ? "Both agents used the same original data and independently reached the same score."
        : `The reviewer score differs by ${Math.abs(scoreDifference)} points. Review the difference.`;
  } else {
    $("reviewer").textContent = "The reviewer calculation can be repeated from the original data.";
    $("reviewer-facts").append(text("li", "Status: calculation checked"), text("li", "System calculation: complete"));
    $("agreement-state").textContent = "Calculation checked";
    $("agent-difference").textContent = "This result uses system calculations. When live dual-agent analysis is enabled, an independent interpretation will also appear here.";
  }
  document.querySelector("#agents-title").textContent = live
    ? "Dual-agent conclusions and differences"
    : "Calculation results and review";
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
    ? `Without action, opening moves by ${counted(data.projected_delay_workdays, "workday")}`
    : "The delay remains within the task's delay allowance";
  const taskNames = new Map(
    currentData.schedule.map((task) => [task.task_id, translateTaskName(task.name)]),
  );
  const affectedNames = data.affected_task_ids.map(
    (taskId) => taskNames.get(taskId) || "Affected launch task",
  );
  $("rescue-affected-count").textContent = `${affectedNames.length} ${affectedNames.length === 1 ? "item" : "items"}`;
  $("rescue-affected-copy").textContent = affectedNames.length
    ? affectedNames.join(", ")
    : "No downstream tasks move";
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
      selectedStrategyName = strategyLabels[strategy.name] || "Recovery option";
      $("adopt-rescue").disabled = false;
      $("rescue-choice-state").textContent = `Selected: ${selectedStrategyName}; not recorded yet`;
    });
    const metrics = document.createElement("div");
    metrics.className = "strategy-metric";
    [
      ["Expected opening", formatDate(strategy.resulting_opening_date)],
      ["Days recovered / delay left", `${strategy.recovered_workdays} / ${strategy.residual_delay_workdays} days`],
      ["Resulting budget", strategy.budget_total == null ? "Itemized estimates not provided" : formatCurrency(strategy.budget_total)],
      ["Over budget", strategy.budget_overage == null ? "Cannot be calculated yet" : formatCurrency(strategy.budget_overage)],
    ].forEach(([label, value]) => {
      const item = document.createElement("div");
      item.append(text("span", label), text("strong", value));
      metrics.append(item);
    });
    const blockers = strategy.blockers.map(
      (item) => rescueBlockerLabels[item] || "Required information is missing",
    );
    const status = blockers.length
      ? `Unavailable: ${blockers.join("; ")}`
      : strategy.budget_status === "over"
        ? "Needs your approval: this result is above the budget limit"
        : "Information complete and ready to compare";
    card.append(
      radio,
      text("h4", strategyLabels[strategy.name] || "Recovery option"),
      metrics,
      text("p", status, "strategy-status"),
    );
    grid.append(card);
  });
  const live = data.status === "LIVE_RESCUE_COMPLETE";
  if (live && data.reviewer_report && data.reviewer_report.hash_match === true) {
    $("rescue-review-badge").textContent = "Both agents calculated the same result";
    $("rescue-manager").textContent = "The Launch Manager Agent compared three recovery options and sent the source data for review.";
    $("rescue-reviewer").textContent = "The Readiness Reviewer Agent independently recalculated the source data and matched the result.";
  } else {
    $("rescue-review-badge").textContent = "Calculation checked";
    $("rescue-manager").textContent = "Calculated three recovery options from this scenario.";
    $("rescue-reviewer").textContent = "Recalculated the same source data.";
  }
  $("adopt-rescue").disabled = true;
  $("rescue-choice-state").textContent = data.strategies.some((item) => item.selectable)
    ? "No option selected"
    : "No option is currently available. Adjust the scenario and calculate again";
  setRescueStatus(
    `Complete: ${live ? "both agents independently calculated and matched" : "system calculation checked"}. The original plan is unchanged.`,
    "success",
  );
};

const executeRescue = async (mode) => {
  if (!currentProjectId) return;
  const payload = rescuePayload();
  const endpoint =
    mode === "live"
      ? `/api/live-rescue/${encodeURIComponent(currentProjectId)}`
      : `/api/rescue/${encodeURIComponent(currentProjectId)}`;
  lastRescueOperation = () => executeRescue(mode);
  rescueSimulationId = null;
  selectedStrategyId = null;
  selectedStrategyName = "";
  $("rescue-result").hidden = true;
  $("rescue-choice-state").textContent = "Recalculating; no previous option can be recorded";
  setRescueBusy(true);
  $("rescue-retry").hidden = true;
  setRescueStatus(
    mode === "live"
      ? "The Launch Manager Agent is calculating. The reviewer will independently recalculate from the source scenario…"
      : "Recalculating task order, delay allowances, opening date, and three recovery options…",
  );
  try {
    await ensureSession();
    const data = await requestJson(
      endpoint,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify(payload),
      },
      mode === "live" ? 120000 : 10000,
    );
    renderRescue(data);
  } catch (error) {
    resetSession();
    const timedOut = error.name === "AbortError";
    setRescueStatus(
      timedOut
        ? "The simulation timed out and was not marked complete. Your input is preserved; retry safely."
        : `Simulation failed: ${friendlyErrorMessage(error)}`,
      "error",
    );
    $("rescue-retry").hidden = false;
    $("rescue-task").focus();
  } finally {
    setRescueBusy(false);
  }
};

const renderReport = (data) => {
  const storeType = displayStoreTypes[data.project.store_type] || data.project.store_type;
  $("report-project").textContent = `${storeType} | ${data.project.location}`;
  $("report-meta").textContent = `Planned opening ${formatDate(data.project.opening_date)} · Total budget ${formatCurrency(data.project.budget)}`;
  $("report-score").textContent = `${data.score}/100${data.score_status === "provisional" ? " (provisional)" : ""}`;
  $("report-critical").textContent = `${data.critical_path.length}`;
  $("report-risks").textContent = `${data.gaps.length}`;
  const conclusion =
    data.score >= 80
      ? "Readiness is strong. Complete the final human and on-site checks."
      : data.score >= 60
        ? "Critical gaps remain. Close them in critical-path order before confirming opening day."
        : "Significant readiness risk remains. Resolve high-risk documents, budget, and critical tasks first.";
  $("report-conclusion").textContent =
    data.score_status === "provisional"
      ? `This provisional score excludes unknown budget details. ${conclusion}`
      : conclusion;
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
  const readinessText = score >= 80 ? "Nearly ready to open" : score >= 60 ? "Needs improvement" : "High risk";
  $("readiness-label").textContent =
    data.score_status === "provisional" ? `Provisional · ${readinessText}` : readinessText;
  $("completion").textContent = `${data.task_completion_percent}%`;
  const completedCount = data.schedule.filter((task) => task.completed).length;
  $("completion-note").textContent = `${completedCount}/${data.schedule.length} ${data.schedule.length === 1 ? "task" : "tasks"} completed`;
  if (data.budget_data_status === "provided") {
    $("budget-state").textContent =
      data.budget_overage > 0
        ? `Over by ${formatCurrency(data.budget_overage)}`
        : `${formatCurrency(data.budget_remaining)} remaining`;
    $("budget-note").textContent = `Itemized total ${formatCurrency(data.budget_total)}`;
  } else {
    $("budget-state").textContent = "Itemized estimates not provided";
    $("budget-note").textContent = "Enter known estimates; the system will not invent them";
  }
  $("delay-state").textContent = String(data.delayed_days);
  $("source").textContent =
    data.status === "LIVE_AGENT_COMPLETE"
      ? "Source: dual-agent review and system calculations"
      : "Source: system calculations";
  renderRisks(data.gaps);
  renderSchedule(data.schedule);
  populateRescueTasks(data.schedule);
  rescueSimulationId = null;
  selectedStrategyId = null;
  $("rescue-result").hidden = true;
  $("rescue-retry").hidden = true;
  setRescueStatus(
    "The original plan is preserved. You can now add one delay scenario.",
    "success",
  );
  setRescueBusy(false);
  renderAgents(data);
  renderReport(data);
  setDecisionDisabled(false);
  $("decision-state").textContent = approvalId
    ? "Waiting for your decision"
    : "No approval is required for this run";
  loadAudit();
  $("dashboard").scrollIntoView({ behavior: "smooth", block: "start" });
};

const loadAudit = async () => {
  if (!currentProjectId) return;
  const list = $("audit-log");
  try {
    const data = await requestJson(
      `/api/project/${encodeURIComponent(currentProjectId)}/audit`,
      {},
      5000,
    );
    clear(list);
    if (!data.events.length) {
      list.append(text("li", "No activity yet."));
      return;
    }
    data.events.forEach((event) => {
      const item = document.createElement("li");
      const eventLabel = auditEventLabels[event.event_type] || "System activity";
      const detailLabel = auditDetailLabels[event.detail] || "An important action was completed and recorded";
      item.append(text("time", formatDateTime(event.created_at)), text("span", `${eventLabel} | ${detailLabel}`));
      list.append(item);
    });
  } catch {
    clear(list);
    list.append(text("li", "Activity is temporarily unavailable."));
  }
};

const execute = async (mode) => {
  if (!$("project-form").checkValidity()) {
    $("project-form").reportValidity();
    return;
  }
  let payload;
  try {
    payload = formPayload();
  } catch (error) {
    setStatus(friendlyErrorMessage(error), "error");
    return;
  }
  const endpoint = mode === "live" ? "/api/live-analyze" : "/api/analyze";
  lastOperation = () => execute(mode);
  setBusy(true);
  setDecisionDisabled(true);
  $("retry").hidden = true;
  $("run-mode").textContent = mode === "live" ? "Dual-agent analysis" : "System calculation";
  setRunProgress(0);
  setStatus("Validating source data and human-approval boundaries…");
  try {
    await ensureSession();
    setRunProgress(1);
    setStatus(
      mode === "live"
        ? "The Launch Manager Agent is analyzing. The reviewer will independently recalculate from the original data…"
        : "Calculating task order, completion deadlines, critical tasks, and risks…",
    );
    const data = await requestJson(
      endpoint,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify(payload),
      },
      mode === "live" ? 120000 : 10000,
    );
    setRunProgress(3);
    render(data);
    setRunProgress(4, true);
    setStatus(
      mode === "live"
        ? "Complete: both agents analyzed independently and system calculations finished."
        : "Complete: the plan, system calculations, and report are ready.",
      "success",
    );
  } catch (error) {
    resetSession();
    const timedOut = error.name === "AbortError";
    setStatus(
      timedOut
        ? "Analysis timed out and was not marked complete. Retry safely."
        : `Analysis failed: ${friendlyErrorMessage(error)}`,
      "error",
    );
    $("retry").hidden = false;
    setRunProgress(1);
  } finally {
    setBusy(false);
  }
};

const askDecision = (decision) => {
  pendingDecision = decision;
  $("confirm-copy").textContent = `You are about to submit “${decisionLabels[decision]}”. The system will not change it for you, and the same approval cannot be submitted twice.`;
  $("decision-dialog").showModal();
  $("confirm-decision").focus();
};
const submitDecision = async (event) => {
  event.preventDefault();
  if (!approvalId || !pendingDecision) return;
  setDecisionDisabled(true);
  setStatus("Recording your decision…");
  try {
    const result = await requestJson(
      `/api/approval/${approvalId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify({ decision: pendingDecision }),
      },
      10000,
    );
    $("decision-dialog").close();
    $("decision-state").textContent = `Recorded: ${decisionLabels[result.decision]}`;
    setStatus(`Your decision was recorded: ${decisionLabels[result.decision]}`, "success");
    approvalId = null;
    pendingDecision = null;
    await loadAudit();
  } catch (error) {
    setStatus(`Decision failed: ${friendlyErrorMessage(error)}`, "error");
    setDecisionDisabled(false);
  }
};
const askRescueSelection = () => {
  if (!rescueSimulationId || !selectedStrategyId) return;
  $("rescue-confirm-copy").textContent = `You are recording “${selectedStrategyName}”. This will not change opening day, budget, or tasks, and each scenario accepts one recorded choice.`;
  $("rescue-dialog").showModal();
  $("confirm-rescue").focus();
};
const submitRescueSelection = async (event) => {
  event.preventDefault();
  if (!rescueSimulationId || !selectedStrategyId) return;
  $("adopt-rescue").disabled = true;
  setRescueStatus("Recording your choice without applying it to the original plan…");
  try {
    const result = await requestJson(
      `/api/rescue-decision/${encodeURIComponent(rescueSimulationId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify({ strategy_id: selectedStrategyId }),
      },
      10000,
    );
    $("rescue-dialog").close();
    $("rescue-choice-state").textContent = `Recorded: ${selectedStrategyName} (not applied)`;
    setRescueStatus("Your choice is recorded. The original plan, dates, and budget are unchanged.", "success");
    [...document.querySelectorAll('input[name="rescue-strategy"]')].forEach((item) => {
      item.disabled = true;
    });
    rescueSimulationId = result.simulation_id;
    await loadAudit();
  } catch (error) {
    setRescueStatus(`Could not record the choice: ${friendlyErrorMessage(error)}`, "error");
    $("adopt-rescue").disabled = false;
  }
};

$("sample-fill").addEventListener("click", () => {
  setFormPayload(demoPayload);
  setStatus("Sample data loaded. You can run the analysis now.");
  $("project-form").elements.store_type.focus();
});
$("store-type").addEventListener("change", (event) => {
  updateGuidedFields();
  applyFocusPreset(event.target.value, true);
});
[$("location-city"), $("location-area"), $("budget-range")].forEach((control) =>
  control.addEventListener("change", updateGuidedFields),
);
$("project-form").addEventListener("submit", (event) => {
  event.preventDefault();
  execute("offline");
});
$("rescue-form").addEventListener("submit", (event) => {
  event.preventDefault();
  executeRescue("offline");
});
$("live-run").addEventListener("click", () => execute("live"));
$("live-rescue").addEventListener("click", () => executeRescue("live"));
$("retry").addEventListener("click", () => {
  if (lastOperation) lastOperation();
});
$("rescue-retry").addEventListener("click", () => {
  if (lastRescueOperation) lastRescueOperation();
});
$("approve").addEventListener("click", () => askDecision("approved"));
$("reject").addEventListener("click", () => askDecision("rejected"));
$("defer").addEventListener("click", () => askDecision("deferred"));
$("confirm-decision").addEventListener("click", submitDecision);
$("cancel-decision").addEventListener("click", () => {
  pendingDecision = null;
});
$("adopt-rescue").addEventListener("click", askRescueSelection);
$("confirm-rescue").addEventListener("click", submitRescueSelection);
$("print-report").addEventListener("click", () => window.print());

applyFocusPreset("", false);
updateGuidedFields();

requestJson("/ready", {}, 5000)
  .then((data) => {
    liveAvailable = Boolean(data.live_enabled);
    $("live-run").hidden = !liveAvailable;
    $("live-rescue").hidden = !liveAvailable;
    $("live-run").disabled = !liveAvailable;
    $("live-rescue").disabled = !liveAvailable || !currentProjectId;
    $("live-run").title = liveAvailable ? "Run dual-agent analysis" : "";
    $("service-state").textContent = "Service ready";
    $("service-state").classList.add("ready");
  })
  .catch(() => {
    $("service-state").textContent = "Service unavailable";
    setStatus("The service is not ready. Try again shortly.", "error");
  });
