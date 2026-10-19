"""模块 2：项目投资管理。

覆盖净现值、内含收益率、现值指数、年金净流量、静态/动态回收期，
以及年限相同和年限不同情形下的互斥方案比选。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from utils import (
    CalcResult,
    ValidationError,
    ask_float,
    ask_int,
    ask_rate_percent,
    ask_series,
    ask_text,
    ask_yes_no,
    money,
    pause,
    percent,
    print_heading,
    require_cash_flows,
    require_nonnegative,
    require_positive,
    run_calculation,
    show_result,
    validate_discount_rate,
)
from time_value import annuity_pv_factor


MODULE = "模块2 项目投资管理"


# ---------------------------------------------------------------------------
# 基础评价指标
# ---------------------------------------------------------------------------
def npv(rate: float, initial_outlay: float, cash_flows: Sequence[float]) -> float:
    """净现值 NPV = -初始投资 + Σ[CF_t/(1+i)^t]，t=1..n。"""
    r = validate_discount_rate(rate)
    initial = require_nonnegative(initial_outlay, "初始投资额")
    flows = require_cash_flows(cash_flows)
    return -initial + sum(cf / ((1.0 + r) ** (t + 1)) for t, cf in enumerate(flows))


def irr(initial_outlay: float, cash_flows: Sequence[float]) -> float:
    """内含收益率：使 NPV=0 的折现率，使用扫描 + Brent 数值求根。"""
    initial = require_positive(initial_outlay, "初始投资额")
    flows = require_cash_flows(cash_flows)
    from scipy.optimize import brentq

    def objective(rate: float) -> float:
        return -initial + sum(cf / ((1.0 + rate) ** (t + 1)) for t, cf in enumerate(flows))

    grid = np.linspace(-0.999, 10.0, 2000)
    previous_rate = float(grid[0])
    previous_value = objective(previous_rate)
    candidates: List[Tuple[float, float]] = []
    for point in grid[1:]:
        current_rate = float(point)
        current_value = objective(current_rate)
        if abs(current_value) < 1e-10:
            candidates.append((current_rate, current_rate))
        if previous_value * current_value < 0:
            candidates.append((previous_rate, current_rate))
        previous_rate, previous_value = current_rate, current_value
    if not candidates:
        raise ValidationError("项目现金流不存在可求解的 IRR（NPV 未发生正负号变化）。")
    # 常规项目取最小正根；若存在多个根，优先返回最小正根。
    roots = []
    for low, high in candidates:
        if abs(high - low) < 1e-12:
            roots.append(low)
        else:
            roots.append(float(brentq(objective, low, high, maxiter=300)))
    positive_roots = [root for root in roots if root > 0]
    return float(min(positive_roots) if positive_roots else min(roots))


def profitability_index(rate: float, initial_outlay: float, cash_flows: Sequence[float]) -> float:
    """现值指数 PI = 未来现金流入现值 / 初始投资。"""
    r = validate_discount_rate(rate)
    initial = require_positive(initial_outlay, "初始投资额")
    flows = require_cash_flows(cash_flows)
    pv_inflows = sum(cf / ((1.0 + r) ** (t + 1)) for t, cf in enumerate(flows))
    return pv_inflows / initial


def annual_net_cash_flow(
    rate: float, initial_outlay: float, cash_flows: Sequence[float]
) -> float:
    """年金净流量 ANCF = NPV / 年金现值系数，即等额年金（EAA）。"""
    r = validate_discount_rate(rate)
    flows = require_cash_flows(cash_flows)
    value = npv(r, initial_outlay, flows)
    factor = annuity_pv_factor(r, len(flows))
    return value / factor


def static_payback_period(initial_outlay: float, cash_flows: Sequence[float]) -> Optional[float]:
    """静态回收期：累计未折现现金流首次由负转正的时点。"""
    initial = require_positive(initial_outlay, "初始投资额")
    flows = require_cash_flows(cash_flows)
    cumulative = -initial
    for index, flow in enumerate(flows):
        if cumulative + flow >= 0 and flow > 0:
            return index + (-cumulative) / flow
        cumulative += flow
    return None


def dynamic_payback_period(
    rate: float, initial_outlay: float, cash_flows: Sequence[float]
) -> Optional[float]:
    """动态回收期：累计折现现金流首次由负转正的时点。"""
    r = validate_discount_rate(rate)
    initial = require_positive(initial_outlay, "初始投资额")
    flows = require_cash_flows(cash_flows)
    cumulative = -initial
    for index, flow in enumerate(flows):
        discounted = flow / ((1.0 + r) ** (index + 1))
        if cumulative + discounted >= 0 and discounted > 0:
            return index + (-cumulative) / discounted
        cumulative += discounted
    return None


def _payback_text(value: Optional[float]) -> str:
    return "项目寿命期内无法回收" if value is None else f"{value:.2f} 年"


# ---------------------------------------------------------------------------
# 综合项目评价
# ---------------------------------------------------------------------------
def project_appraisal_result(
    initial_outlay: float,
    cash_flows: Sequence[float],
    rate: float,
    *,
    project_name: str = "投资项目",
    plot: bool = False,
) -> CalcResult:
    """一次计算全部项目投资评价指标，并输出分年折现表。"""
    import pandas as pd

    initial = require_positive(initial_outlay, "初始投资额")
    flows = require_cash_flows(cash_flows)
    r = validate_discount_rate(rate)
    value = npv(r, initial, flows)
    pi = profitability_index(r, initial, flows)
    ancf = annual_net_cash_flow(r, initial, flows)
    static_pb = static_payback_period(initial, flows)
    dynamic_pb = dynamic_payback_period(r, initial, flows)
    irr_value: Optional[float]
    irr_note = ""
    try:
        irr_value = irr(initial, flows)
    except ValidationError as exc:
        irr_value = None
        irr_note = str(exc)

    result = CalcResult(
        MODULE,
        f"{project_name}：全面投资评价",
        {
            "初始投资": f"{money(initial)} 元",
            "建设期": "0 年",
            "经营期": f"{len(flows)} 年",
            "各年净现金流量": [money(x) for x in flows],
            "必要报酬率": percent(r),
        },
    )
    result.add_step(
        "整理项目现金流：t=0 发生初始投资（流出），第 1~n 年发生经营净现金流量（正数表示净流入）。"
    )
    result.add_step(
        f"净现值 NPV = -{money(initial)} + Σ[CF_t/(1+{percent(r)})^t] = {money(value)} 元。"
    )
    result.add_step(f"现值指数 PI = 未来现金流入现值 ÷ 初始投资 = {pi:.4f}。")
    result.add_step(
        f"年金净流量 ANCF = NPV ÷ (P/A, {percent(r)}, {len(flows)}) = {money(ancf)} 元/年。"
    )
    if irr_value is not None:
        result.add_step(
            f"内含收益率 IRR 为使 NPV=0 的折现率，经数值求解 IRR = {percent(irr_value, 4)}。"
        )
    else:
        result.add_step(f"内含收益率 IRR 无法求解：{irr_note}")
    result.add_step(
        f"静态回收期：累计未折现净现金流首次转正时点为 {_payback_text(static_pb)}。"
    )
    result.add_step(
        f"动态回收期：累计折现净现金流首次转正时点为 {_payback_text(dynamic_pb)}；"
        "动态回收期考虑了资金时间价值，通常长于静态回收期。"
    )

    result.put("净现值 NPV", f"{money(value)} 元")
    result.put("现值指数 PI", f"{pi:.4f}")
    result.put("年金净流量 ANCF", f"{money(ancf)} 元/年")
    result.put("内含收益率 IRR", percent(irr_value, 4) if irr_value is not None else "无法求解")
    result.put("静态回收期", _payback_text(static_pb))
    result.put("动态回收期", _payback_text(dynamic_pb))

    discount_factors = [1.0 / ((1.0 + r) ** (t + 1)) for t in range(len(flows))]
    discounted = [flow * factor for flow, factor in zip(flows, discount_factors)]
    cumulative = []
    running = -initial
    for flow in flows:
        running += flow
        cumulative.append(running)
    cumulative_discounted = []
    running = -initial
    for pv in discounted:
        running += pv
        cumulative_discounted.append(running)
    table = pd.DataFrame(
        {
            "年份": list(range(1, len(flows) + 1)),
            "净现金流量": [round(x, 2) for x in flows],
            "折现系数": [round(x, 6) for x in discount_factors],
            "折现现金流量": [round(x, 2) for x in discounted],
            "累计净现金流量": [round(x, 2) for x in cumulative],
            "累计折现现金流量": [round(x, 2) for x in cumulative_discounted],
        }
    )
    result.add_table("项目分年现金流与回收期计算表", table)

    decision_parts = []
    decision_parts.append("NPV>0，项目可行" if value > 0 else "NPV≤0，项目不可行")
    decision_parts.append("PI>1，可行" if pi > 1 else "PI≤1，不可行")
    if irr_value is not None:
        decision_parts.append(
            f"IRR {'>' if irr_value > r else '≤'} 必要报酬率，"
            f"{'可行' if irr_value > r else '不可行'}"
        )
    result.add_note("综合判断：" + "；".join(decision_parts) + "。")
    result.add_note(
        "若各指标结论冲突，互斥方案通常以 NPV 为主；独立项目在资金无限时以 NPV>0 为基本接受标准。"
    )
    result.parameters["IRR 求解说明"] = irr_note or "正常求解"

    if plot:
        from visual import plot_cash_flow

        image_path = plot_cash_flow(
            [-initial] + list(flows),
            title=f"{project_name}现金流时间轴",
            filename=f"{project_name}_cash_flow",
        )
        result.put("时间轴图片", str(image_path))
    return result


# ---------------------------------------------------------------------------
# 互斥方案比选
# ---------------------------------------------------------------------------
def compare_projects(projects: Sequence[Dict[str, object]], rate: float) -> CalcResult:
    """互斥方案比选。

    projects 每个元素包含 name、initial、cash_flows。
    年限相同：比较 NPV；年限不同：比较年金净流量 ANCF（等额年金法）。
    """
    if len(projects) < 2:
        raise ValidationError("互斥方案比选至少需要两个项目。")
    import pandas as pd

    r = validate_discount_rate(rate)
    rows = []
    details: List[Dict[str, object]] = []
    for raw in projects:
        name = str(raw.get("name", "方案"))
        initial = require_positive(raw.get("initial"), f"{name}初始投资")
        flows = require_cash_flows(raw.get("cash_flows"), f"{name}现金流量")
        value = npv(r, initial, flows)
        pi = profitability_index(r, initial, flows)
        ancf = annual_net_cash_flow(r, initial, flows)
        try:
            irr_value = irr(initial, flows)
        except ValidationError:
            irr_value = None
        rows.append(
            {
                "方案": name,
                "寿命（年）": len(flows),
                "初始投资": round(initial, 2),
                "NPV": round(value, 2),
                "IRR": f"{irr_value * 100:.2f}%" if irr_value is not None else "无法求解",
                "PI": round(pi, 4),
                "ANCF（元/年）": round(ancf, 2),
            }
        )
        details.append(
            {
                "name": name,
                "initial": initial,
                "flows": flows,
                "npv": value,
                "irr": irr_value,
                "pi": pi,
                "ancf": ancf,
            }
        )

    lives = {len(item["flows"]) for item in details}
    same_life = len(lives) == 1
    if same_life:
        best = max(details, key=lambda item: float(item["npv"]))
        criterion = "年限相同 → 比较净现值 NPV，选择 NPV 最大者"
    else:
        best = max(details, key=lambda item: float(item["ancf"]))
        criterion = "年限不同 → 比较年金净流量 ANCF（等额年金），选择 ANCF 最大者"

    result = CalcResult(
        MODULE,
        "互斥方案比选",
        {
            "必要报酬率": percent(r),
            "方案数量": len(details),
            "寿命是否相同": "是" if same_life else "否",
        },
    )
    result.add_step(
        "互斥方案只能选择其中一个，应统一折现率并分别计算各方案的 NPV、IRR、PI 与 ANCF。"
    )
    if same_life:
        result.add_step("各方案寿命相同，可直接比较净现值：NPV 越大，为股东增加的财富越多。")
        result.add_step(
            "NPV 排序："
            + " > ".join(
                f"{item['name']}({money(item['npv'])} 元)"
                for item in sorted(details, key=lambda x: float(x["npv"]), reverse=True)
            )
            + "。"
        )
    else:
        result.add_step(
            "各方案寿命不同，NPV 会受寿命长短影响，不能直接比较；应将 NPV 年金化，"
            "计算 ANCF = NPV ÷ (P/A, i, n)，比较每年等额价值。"
        )
        result.add_step(
            "ANCF 排序："
            + " > ".join(
                f"{item['name']}({money(item['ancf'])} 元/年)"
                for item in sorted(details, key=lambda x: float(x["ancf"]), reverse=True)
            )
            + "。"
        )
    result.add_step(f"依据“{criterion}”，推荐方案为：{best['name']}。")

    table = pd.DataFrame(rows)
    result.add_table("互斥方案评价指标比较表", table)
    result.put("比选方法", criterion)
    result.put("推荐方案", str(best["name"]))
    result.put("推荐方案 NPV", f"{money(best['npv'])} 元")
    result.put("推荐方案 ANCF", f"{money(best['ancf'])} 元/年")
    if best["irr"] is not None:
        result.put("推荐方案 IRR", percent(best["irr"], 4))

    if all(float(item["npv"]) <= 0 for item in details):
        result.add_note("所有方案 NPV 均不大于 0，理论上应全部拒绝；推荐结果仅为相对较优方案。")
    if not same_life:
        result.add_note(
            "等额年金法隐含“项目可重复实施、寿命可接续”的假设；若不可重复，应结合共同年限法判断。"
        )
    result.add_note("当 NPV 与 IRR 排序矛盾时，互斥方案应以 NPV 或 ANCF 的财富增量结论为准。")
    return result


# ---------------------------------------------------------------------------
# 交互菜单与例题
# ---------------------------------------------------------------------------
def _input_project(default_name: str, default_initial: float, default_flows: Sequence[float]) -> Dict[str, object]:
    """交互录入一个项目。"""
    name = ask_text("项目名称", default_name)
    initial = ask_float("初始投资额（元）", default_initial, min_value=0, allow_negative=False)
    flows = ask_series("第1~n年净现金流量（元）", default_flows, min_length=1)
    return {"name": name, "initial": initial, "cash_flows": flows}


def _interactive_appraisal() -> CalcResult:
    project = _input_project("A项目", 1000000, [280000, 300000, 320000, 300000, 280000])
    rate = ask_rate_percent("必要报酬率", 0.10)
    plot = ask_yes_no("是否绘制现金流时间轴？", True)
    return project_appraisal_result(
        float(project["initial"]),
        list(project["cash_flows"]),
        rate,
        project_name=str(project["name"]),
        plot=plot,
    )


def _interactive_compare() -> CalcResult:
    rate = ask_rate_percent("统一必要报酬率", 0.10)
    print("\n录入方案一：")
    first = _input_project(
        "方案A", 1000000, [280000, 300000, 320000, 300000, 280000]
    )
    print("\n录入方案二（可输入不同寿命）：")
    second = _input_project("方案B", 900000, [250000, 280000, 300000, 280000, 250000])
    return compare_projects([first, second], rate)


def _run_demo() -> None:
    """一键演示项目评价与两类互斥方案比选。"""
    print_heading("项目投资管理：全套例题一键演示", "★")
    project_a = project_appraisal_result(
        1000000,
        [280000, 300000, 320000, 300000, 280000],
        0.10,
        project_name="A项目",
        plot=True,
    )
    show_result(project_a)

    same_life = compare_projects(
        [
            {"name": "A方案", "initial": 1000000, "cash_flows": [280000, 300000, 320000, 300000, 280000]},
            {"name": "B方案", "initial": 900000, "cash_flows": [250000, 280000, 300000, 280000, 250000]},
        ],
        0.10,
    )
    show_result(same_life)

    different_life = compare_projects(
        [
            {"name": "短寿命C方案", "initial": 500000, "cash_flows": [220000, 240000, 260000]},
            {
                "name": "长寿命D方案",
                "initial": 800000,
                "cash_flows": [230000, 250000, 280000, 300000, 320000],
            },
        ],
        0.10,
    )
    show_result(different_life)
    print("\n[演示完成] 已演示全面评价、年限相同比选和年限不同比选。")


def run() -> None:
    """模块 2 控制台菜单。"""
    while True:
        print_heading("模块2 项目投资管理（NPV/IRR/PI/ANCF/回收期）")
        print("  1. 项目全面评价（全部指标 + 分年折现表）")
        print("  2. 互斥方案比选（自动识别年限相同/不同）")
        print("  3. 全套例题一键演示")
        print("  0. 返回主菜单")
        try:
            choice = input("请选择功能：").strip()
        except EOFError:
            return
        if choice == "0":
            return
        if choice == "1":
            run_calculation(_interactive_appraisal)
            pause()
        elif choice == "2":
            run_calculation(_interactive_compare)
            pause()
        elif choice == "3":
            _run_demo()
            pause()
        else:
            print("[提示] 无效选项，请输入 0~3。")
