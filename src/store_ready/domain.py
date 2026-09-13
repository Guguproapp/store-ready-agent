"""Deterministic launch-readiness calculations.

The model may explain these results, but it never owns the arithmetic. This
module has no network or AI dependency so it can be tested offline.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date, timedelta
from math import floor, isfinite

MAX_MONEY_TWD = 1_000_000_000_000


@dataclass(frozen=True)
class ProjectInput:
    store_type: str
    location: str
    budget: float
    opening_date: date
    acquired_documents: tuple[str, ...] = ()
    missing_documents: tuple[str, ...] = ()
    completed_items: tuple[str, ...] = ()
    pending_items: tuple[str, ...] = ()


@dataclass(frozen=True)
class LaunchTask:
    task_id: str
    name: str
    duration_days: int
    depends_on: tuple[str, ...] = ()
    category: str = "general"
    completed: bool = False


@dataclass(frozen=True)
class TaskSchedule:
    task_id: str
    name: str
    start_date: date
    due_date: date
    duration_days: int
    critical: bool
    completed: bool


@dataclass(frozen=True)
class GapFinding:
    kind: str
    title: str
    detail: str
    severity: str


@dataclass(frozen=True)
class ReadinessResult:
    score: int
    task_completion_percent: int
    missing_documents: tuple[str, ...]
    budget_total: float | None
    budget_overage: float | None
    schedule: tuple[TaskSchedule, ...]
    gaps: tuple[GapFinding, ...]
    delayed_days: int


@dataclass(frozen=True)
class TaskTiming:
    task_id: str
    name: str
    earliest_completion: date
    latest_safe_completion: date
    slack_workdays: int
    critical: bool


@dataclass(frozen=True)
class RescueScenario:
    task_id: str
    delay_workdays: int
    direct_budget_shock: int
    max_recoverable_workdays: int
    recovery_cost_per_day: int | None


@dataclass(frozen=True)
class RescueStrategy:
    strategy_id: str
    name: str
    recovered_workdays: int
    residual_delay_workdays: int
    resulting_opening_date: date
    budget_total: float | None
    budget_overage: float | None
    budget_status: str
    feasible: bool
    selectable: bool
    blockers: tuple[str, ...]
    assumptions: tuple[str, ...]


@dataclass(frozen=True)
class RescueSimulation:
    baseline_project_workdays: int
    scenario_project_workdays: int
    projected_delay_workdays: int
    scenario_opening_date: date
    affected_task_ids: tuple[str, ...]
    timings: tuple[TaskTiming, ...]
    strategies: tuple[RescueStrategy, ...]


@dataclass(frozen=True)
class _CpmOffsets:
    ordered: tuple[LaunchTask, ...]
    earliest_start: dict[str, int]
    earliest_finish: dict[str, int]
    latest_start: dict[str, int]
    latest_finish: dict[str, int]
    project_duration: int


def add_workdays(start: date, days: int) -> date:
    """Add weekdays, excluding Saturday and Sunday."""

    current = start
    remaining = max(days, 0)
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def subtract_workdays(end: date, days: int) -> date:
    """Subtract weekdays, excluding Saturday and Sunday."""

    current = end
    remaining = max(days, 0)
    while remaining:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def workdays_late(planned_start: date, as_of_date: date) -> int:
    """Count elapsed weekdays after a missed planned start."""

    current = planned_start
    late_days = 0
    while current < as_of_date:
        current += timedelta(days=1)
        if current.weekday() < 5:
            late_days += 1
    return late_days


_RETAIL_TASK_NAMES = (
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
)
_FOOD_TASK_NAMES = (
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
)
_PERSONAL_TASK_NAMES = (
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
)
_STUDIO_TASK_NAMES = (
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
)
_FOOD_STORE_TYPES = {
    "街邊咖啡店",
    "飲料店",
    "餐廳／小吃店",
    "烘焙／甜點店",
    "食品零售店",
    "攤車／快閃店",
}
_PERSONAL_STORE_TYPES = {"美容／美髮／美甲工作室", "寵物服務店"}
_STUDIO_STORE_TYPES = {"健身／運動工作室", "教育／才藝教室", "生活服務門市"}


def task_names_for_store_type(store_type: str) -> tuple[str, ...]:
    """Return the focused ten-step checklist for a supported store family."""

    if store_type in _FOOD_STORE_TYPES:
        return _FOOD_TASK_NAMES
    if store_type in _PERSONAL_STORE_TYPES:
        return _PERSONAL_TASK_NAMES
    if store_type in _STUDIO_STORE_TYPES:
        return _STUDIO_TASK_NAMES
    return _RETAIL_TASK_NAMES


def default_tasks(project: ProjectInput) -> tuple[LaunchTask, ...]:
    completed = set(project.completed_items)
    names = task_names_for_store_type(project.store_type)
    return (
        LaunchTask(
            "lease",
            names[0],
            3,
            category="documents",
            completed=names[0] in completed,
        ),
        LaunchTask(
            "permits",
            names[1],
            4,
            ("lease",),
            "documents",
            names[1] in completed,
        ),
        LaunchTask(
            "utilities",
            names[2],
            3,
            ("lease",),
            "site",
            names[2] in completed,
        ),
        LaunchTask(
            "fitout",
            names[3],
            8,
            ("lease",),
            "site",
            names[3] in completed,
        ),
        LaunchTask(
            "equipment",
            names[4],
            2,
            ("fitout", "utilities"),
            "site",
            names[4] in completed,
        ),
        LaunchTask(
            "supply",
            names[5],
            3,
            ("permits",),
            "operations",
            names[5] in completed,
        ),
        LaunchTask(
            "operations",
            names[6],
            2,
            ("equipment", "supply"),
            "operations",
            names[6] in completed,
        ),
        LaunchTask(
            "staffing",
            names[7],
            1,
            ("fitout",),
            "people",
            names[7] in completed,
        ),
        LaunchTask(
            "training",
            names[8],
            4,
            ("staffing",),
            "training",
            names[8] in completed,
        ),
        LaunchTask(
            "inspection",
            names[9],
            2,
            ("permits", "operations", "training"),
            "readiness",
            names[9] in completed,
        ),
    )


def _topological_order(tasks: tuple[LaunchTask, ...]) -> list[LaunchTask]:
    by_id = {task.task_id: task for task in tasks}
    if len(by_id) != len(tasks):
        raise ValueError("DUPLICATE_TASK_ID")
    if any(task.duration_days < 1 for task in tasks):
        raise ValueError("INVALID_TASK_DURATION")
    visiting: set[str] = set()
    visited: set[str] = set()
    result: list[LaunchTask] = []

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError("TASK_DEPENDENCY_CYCLE")
        if task_id in visited:
            return
        if task_id not in by_id:
            raise ValueError(f"UNKNOWN_TASK_DEPENDENCY:{task_id}")
        visiting.add(task_id)
        for dependency in by_id[task_id].depends_on:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)
        result.append(by_id[task_id])

    for task in tasks:
        visit(task.task_id)
    return result


def _cpm_offsets(tasks: tuple[LaunchTask, ...]) -> _CpmOffsets:
    ordered = tuple(_topological_order(tasks))
    successors: dict[str, list[str]] = {task.task_id: [] for task in ordered}
    for task in ordered:
        for dependency in task.depends_on:
            successors[dependency].append(task.task_id)

    earliest_start: dict[str, int] = {}
    earliest_finish: dict[str, int] = {}
    for task in ordered:
        start = max((earliest_finish[item] for item in task.depends_on), default=0)
        earliest_start[task.task_id] = start
        earliest_finish[task.task_id] = start + task.duration_days

    terminals = [task.task_id for task in ordered if not successors[task.task_id]]
    project_duration = max((earliest_finish[item] for item in terminals), default=0)
    latest_start: dict[str, int] = {}
    latest_finish: dict[str, int] = {}
    for task in reversed(ordered):
        finish = min(
            (latest_start[item] for item in successors[task.task_id]),
            default=project_duration,
        )
        latest_finish[task.task_id] = finish
        latest_start[task.task_id] = finish - task.duration_days
    return _CpmOffsets(
        ordered,
        earliest_start,
        earliest_finish,
        latest_start,
        latest_finish,
        project_duration,
    )


def calculate_critical_path(
    tasks: Iterable[LaunchTask], opening_date: date
) -> tuple[TaskSchedule, ...]:
    """Calculate deterministic task dates and critical-path membership."""

    ordered = _topological_order(tuple(tasks))
    successors: dict[str, list[str]] = {task.task_id: [] for task in ordered}
    by_id = {task.task_id: task for task in ordered}
    for task in ordered:
        for dependency in task.depends_on:
            successors[dependency].append(task.task_id)

    start_by_id: dict[str, date] = {}
    due_by_id: dict[str, date] = {}
    for task in reversed(ordered):
        successor_starts = [start_by_id[item] for item in successors[task.task_id]]
        due = (
            min(subtract_workdays(item, 1) for item in successor_starts)
            if successor_starts
            else opening_date
        )
        start = subtract_workdays(due, task.duration_days - 1)
        start_by_id[task.task_id] = start
        due_by_id[task.task_id] = due

    longest_to: dict[str, int] = {}
    for task in ordered:
        longest_to[task.task_id] = task.duration_days + max(
            (longest_to[item] for item in task.depends_on), default=0
        )
    terminals = [task.task_id for task in ordered if not successors[task.task_id]]
    project_duration = max((longest_to[item] for item in terminals), default=0)
    critical_ids: set[str] = set()

    def mark_critical(task_id: str) -> None:
        if task_id in critical_ids:
            return
        critical_ids.add(task_id)
        task = by_id[task_id]
        predecessor_length = longest_to[task_id] - task.duration_days
        for dependency in task.depends_on:
            if longest_to[dependency] == predecessor_length:
                mark_critical(dependency)

    for task_id in terminals:
        if longest_to[task_id] == project_duration:
            mark_critical(task_id)

    schedules = (
        TaskSchedule(
            task.task_id,
            task.name,
            start_by_id[task.task_id],
            due_by_id[task.task_id],
            task.duration_days,
            task.task_id in critical_ids,
            task.completed,
        )
        for task in ordered
    )
    return tuple(replace(item) for item in schedules)


def calculate_task_timing(
    tasks: Iterable[LaunchTask], opening_date: date
) -> tuple[TaskTiming, ...]:
    """Return deterministic CPM slack and last-safe dates for every task."""

    task_list = tuple(tasks)
    offsets = _cpm_offsets(task_list)
    schedule = calculate_critical_path(task_list, opening_date)
    schedule_by_id = {item.task_id: item for item in schedule}
    project_start = min((item.start_date for item in schedule), default=opening_date)
    return tuple(
        TaskTiming(
            task_id=task.task_id,
            name=task.name,
            earliest_completion=add_workdays(
                project_start, offsets.earliest_finish[task.task_id] - 1
            ),
            latest_safe_completion=schedule_by_id[task.task_id].due_date,
            slack_workdays=(
                offsets.latest_start[task.task_id] - offsets.earliest_start[task.task_id]
            ),
            critical=(offsets.latest_start[task.task_id] == offsets.earliest_start[task.task_id]),
        )
        for task in offsets.ordered
    )


def _validated_budget_total(budget_items: Iterable[float] | None) -> float | None:
    if budget_items is None:
        return None
    values = tuple(float(item) for item in budget_items)
    if any(not isfinite(item) or item < 0 for item in values):
        raise ValueError("INVALID_BUDGET_ITEMS")
    total = sum(values)
    if not isfinite(total) or total > MAX_MONEY_TWD:
        raise ValueError("MONEY_LIMIT_EXCEEDED")
    return total


def _validate_rescue_scenario(scenario: RescueScenario) -> None:
    integer_fields = (
        scenario.delay_workdays,
        scenario.direct_budget_shock,
        scenario.max_recoverable_workdays,
    )
    if any(type(item) is not int for item in integer_fields):
        raise ValueError("INVALID_RESCUE_SCENARIO")
    if not 1 <= scenario.delay_workdays <= 60:
        raise ValueError("INVALID_DELAY_WORKDAYS")
    if not 0 <= scenario.max_recoverable_workdays <= 60:
        raise ValueError("INVALID_RECOVERY_CAPACITY")
    if not 0 <= scenario.direct_budget_shock <= MAX_MONEY_TWD:
        raise ValueError("INVALID_BUDGET_SHOCK")
    if scenario.recovery_cost_per_day is not None and (
        type(scenario.recovery_cost_per_day) is not int
        or not 0 <= scenario.recovery_cost_per_day <= MAX_MONEY_TWD
    ):
        raise ValueError("INVALID_RECOVERY_COST")


def _money_outcome(
    project_budget: float,
    baseline_total: float | None,
    direct_shock: int,
    recovered_days: int,
    recovery_cost_per_day: int | None,
) -> tuple[float | None, float | None, str]:
    if baseline_total is None or recovery_cost_per_day is None:
        return None, None, "unknown"
    total = baseline_total + direct_shock + recovered_days * recovery_cost_per_day
    if not isfinite(total) or total > MAX_MONEY_TWD:
        raise ValueError("MONEY_LIMIT_EXCEEDED")
    overage = max(0.0, total - project_budget)
    return total, overage, "over" if overage else "within"


def simulate_opening_rescue(
    project: ProjectInput,
    tasks: Iterable[LaunchTask],
    budget_items: Iterable[float] | None,
    scenario: RescueScenario,
) -> RescueSimulation:
    """Simulate one bounded pre-opening shock and exactly three rescue policies."""

    _validate_rescue_scenario(scenario)
    task_list = tuple(tasks)
    by_id = {task.task_id: task for task in task_list}
    selected = by_id.get(scenario.task_id)
    if selected is None:
        raise ValueError("UNKNOWN_RESCUE_TASK")
    if selected.completed:
        raise ValueError("COMPLETED_TASK_CANNOT_BE_SHOCKED")

    baseline_offsets = _cpm_offsets(task_list)
    shocked_tasks = tuple(
        replace(task, duration_days=task.duration_days + scenario.delay_workdays)
        if task.task_id == scenario.task_id
        else task
        for task in task_list
    )
    scenario_offsets = _cpm_offsets(shocked_tasks)
    projected_delay = max(0, scenario_offsets.project_duration - baseline_offsets.project_duration)
    affected = tuple(
        task.task_id
        for task in baseline_offsets.ordered
        if (
            baseline_offsets.earliest_start[task.task_id]
            != scenario_offsets.earliest_start[task.task_id]
            or baseline_offsets.earliest_finish[task.task_id]
            != scenario_offsets.earliest_finish[task.task_id]
        )
    )
    baseline_total = _validated_budget_total(budget_items)
    if baseline_total is not None and baseline_total + scenario.direct_budget_shock > MAX_MONEY_TWD:
        raise ValueError("MONEY_LIMIT_EXCEEDED")

    def make_strategy(
        strategy_id: str,
        name: str,
        recovered: int,
        extra_blockers: tuple[str, ...] = (),
        *,
        require_quote: bool,
    ) -> RescueStrategy:
        residual = projected_delay - recovered
        blockers = list(extra_blockers)
        if baseline_total is None:
            blockers.append("BUDGET_DETAILS_REQUIRED")
        if require_quote and scenario.recovery_cost_per_day is None:
            blockers.append("RECOVERY_QUOTE_REQUIRED")
        cost_per_day = scenario.recovery_cost_per_day if require_quote else 0
        budget_total, budget_overage, budget_status = _money_outcome(
            project.budget,
            baseline_total,
            scenario.direct_budget_shock,
            recovered,
            cost_per_day,
        )
        assumptions = (
            "weekdays_only_no_holiday_calendar",
            "recovery_capacity_and_quote_are_human_supplied",
            "selection_does_not_modify_baseline",
        )
        return RescueStrategy(
            strategy_id=strategy_id,
            name=name,
            recovered_workdays=recovered,
            residual_delay_workdays=residual,
            resulting_opening_date=add_workdays(project.opening_date, residual),
            budget_total=budget_total,
            budget_overage=budget_overage,
            budget_status=budget_status,
            feasible=not blockers,
            selectable=not blockers,
            blockers=tuple(dict.fromkeys(blockers)),
            assumptions=assumptions,
        )

    date_recovered = min(projected_delay, scenario.max_recoverable_workdays)
    date_blockers = ("RECOVERY_CAPACITY_INSUFFICIENT",) if date_recovered < projected_delay else ()
    protect_date = make_strategy(
        "protect_date",
        "守住開幕日",
        date_recovered,
        date_blockers,
        require_quote=True,
    )

    budget_blockers: tuple[str, ...] = ()
    if baseline_total is not None and (
        baseline_total + scenario.direct_budget_shock > project.budget
    ):
        budget_blockers = ("DIRECT_SHOCK_EXCEEDS_BUDGET",)
    protect_budget = make_strategy(
        "protect_budget",
        "守住核准預算",
        0,
        budget_blockers,
        require_quote=False,
    )

    lowest_blockers: tuple[str, ...] = ()
    affordable_recovery = 0
    if baseline_total is not None and scenario.recovery_cost_per_day is not None:
        available = max(
            project.budget - baseline_total - scenario.direct_budget_shock,
            0,
        )
        affordable_recovery = (
            scenario.max_recoverable_workdays
            if scenario.recovery_cost_per_day == 0
            else floor(available / scenario.recovery_cost_per_day)
        )
        if baseline_total + scenario.direct_budget_shock > project.budget:
            lowest_blockers = ("NO_WITHIN_BUDGET_OPTION",)
    lowest_recovered = min(
        projected_delay,
        scenario.max_recoverable_workdays,
        affordable_recovery,
    )
    lowest_risk = make_strategy(
        "lowest_risk",
        "預算內壓低時程風險",
        lowest_recovered,
        lowest_blockers,
        require_quote=True,
    )

    return RescueSimulation(
        baseline_project_workdays=baseline_offsets.project_duration,
        scenario_project_workdays=scenario_offsets.project_duration,
        projected_delay_workdays=projected_delay,
        scenario_opening_date=add_workdays(project.opening_date, projected_delay),
        affected_task_ids=affected,
        timings=calculate_task_timing(task_list, project.opening_date),
        strategies=(protect_date, protect_budget, lowest_risk),
    )


def detect_readiness_gaps(
    project: ProjectInput,
    tasks: Iterable[LaunchTask],
    budget_items: Iterable[float] | None,
) -> tuple[GapFinding, ...]:
    """Find missing documents, budget overage and incomplete training."""

    gaps: list[GapFinding] = []
    acquired = set(project.acquired_documents)
    missing = tuple(dict.fromkeys(project.missing_documents))
    unresolved = tuple(item for item in missing if item not in acquired)
    if unresolved:
        gaps.append(GapFinding("document", "文件缺口", "、".join(unresolved), "high"))

    if budget_items is None:
        gaps.append(
            GapFinding(
                "budget_data",
                "預算明細不足",
                "尚未提供各項預估金額，無法判定預算是否超支",
                "medium",
            )
        )
    else:
        total = sum(budget_items)
        if total > project.budget:
            gaps.append(
                GapFinding(
                    "budget",
                    "預算超支",
                    f"超出新臺幣 {total - project.budget:,.0f} 元",
                    "high",
                )
            )

    known_task_names = {task.name for task in tasks}
    unmapped_pending = tuple(
        item for item in dict.fromkeys(project.pending_items) if item not in known_task_names
    )
    if unmapped_pending:
        gaps.append(
            GapFinding(
                "data",
                "待辦尚未排程",
                "、".join(unmapped_pending),
                "medium",
            )
        )

    training = next((task for task in tasks if task.category == "training"), None)
    if training is not None and not training.completed:
        gaps.append(GapFinding("training", "訓練未完成", training.name, "medium"))
    return tuple(gaps)


def calculate_readiness(
    project: ProjectInput,
    tasks: Iterable[LaunchTask],
    budget_items: Iterable[float] | None,
    as_of_date: date | None = None,
) -> ReadinessResult:
    task_list = tuple(tasks)
    budget_list = tuple(budget_items) if budget_items is not None else None
    schedule = calculate_critical_path(task_list, project.opening_date)
    gaps = detect_readiness_gaps(project, task_list, budget_list)
    total = sum(budget_list) if budget_list is not None else None
    completed = sum(item.completed for item in task_list)
    task_percent = round(completed / len(task_list) * 100) if task_list else 0
    docs_percent = (
        100
        if not project.missing_documents
        else round(
            len(project.acquired_documents)
            / (len(project.acquired_documents) + len(project.missing_documents))
            * 100
        )
    )
    budget_percent = (
        None
        if total is None
        else 100
        if total <= project.budget
        else max(0, round(project.budget / total * 100))
    )
    risk_percent = 100 if not gaps else 50
    weighted_total = task_percent * 0.4 + docs_percent * 0.25 + risk_percent * 0.15
    known_weight = 0.8
    if budget_percent is not None:
        weighted_total += budget_percent * 0.2
        known_weight += 0.2
    score = max(
        0,
        min(100, round(weighted_total / known_weight)),
    )
    reference_date = as_of_date or date.today()
    unfinished_critical = [item for item in schedule if item.critical and not item.completed]
    next_required_start = min(
        (item.start_date for item in unfinished_critical), default=project.opening_date
    )
    delayed = workdays_late(next_required_start, reference_date)
    overage = None if total is None else max(0.0, total - project.budget)
    return ReadinessResult(
        score, task_percent, project.missing_documents, total, overage, schedule, gaps, delayed
    )


def demo_project() -> ProjectInput:
    return ProjectInput(
        store_type="街邊咖啡店",
        location="台北市大安區（虛構示例）",
        budget=800_000,
        opening_date=date(2026, 10, 30),
        acquired_documents=("店面租約與餐飲用途同意文件", "商業登記申請資料"),
        missing_documents=(
            "建物使用與營業場所證明",
            "消防安全設備檢查資料",
            "食品業者登錄準備資料",
            "排煙與油脂截留設備確認資料",
        ),
        completed_items=("確認租約與餐飲用途", "完成登記、場所與消防文件盤點"),
        pending_items=(
            "確認用電、給排水與排煙容量",
            "完成廚房、吧台與顧客動線工程",
            "完成冷藏、製作與收銀設備測試",
            "完成供應商、食材規格與首批備料",
            "完成菜單、定價與食品保存流程",
            "完成招募、排班與職責配置",
            "完成食品安全與服務訓練",
            "完成清潔、試營運與開幕演練",
        ),
    )


def demo_budget_items() -> tuple[float, ...]:
    return (350_000, 280_000, 120_000, 95_000)
