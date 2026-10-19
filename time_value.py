"""模块 1：资金时间价值。

覆盖复利终值/现值、普通年金、预付年金、递延年金、永续年金，以及内插法求折现率。
所有函数中的利率均为小数形式，例如 8% 写成 0.08。
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

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
    require_int,
    require_positive,
    require_rate,
    run_calculation,
    show_result,
    validate_discount_rate,
)


MODULE = "模块1 资金时间价值"


# ---------------------------------------------------------------------------
# 基础系数与公式
# ---------------------------------------------------------------------------
def pv_factor(rate: float, periods: int) -> float:
    """复利现值系数 (P/F, i, n) = 1/(1+i)^n。"""
    r = require_rate(rate)
    n = require_int(periods)
    return 1.0 / ((1.0 + r) ** n)


def fv_factor(rate: float, periods: int) -> float:
    """复利终值系数 (F/P, i, n) = (1+i)^n。"""
    r = require_rate(rate)
    n = require_int(periods)
    return (1.0 + r) ** n


def annuity_pv_factor(rate: float, periods: int) -> float:
    """普通年金现值系数 (P/A, i, n)，利率为 0 时退化为 n。"""
    r = validate_discount_rate(rate)
    n = require_int(periods)
    if abs(r) < 1e-15:
        return float(n)
    return (1.0 - (1.0 + r) ** (-n)) / r


def annuity_fv_factor(rate: float, periods: int) -> float:
    """普通年金终值系数 (F/A, i, n)，利率为 0 时退化为 n。"""
    r = validate_discount_rate(rate)
    n = require_int(periods)
    if abs(r) < 1e-15:
        return float(n)
    return ((1.0 + r) ** n - 1.0) / r


def compound_future_value(present_value: float, rate: float, periods: int) -> float:
    """复利终值 F = P × (F/P, i, n)。"""
    p = require_positive(present_value, "复利现值")
    r = validate_discount_rate(rate)
    n = require_int(periods)
    return p * (1.0 + r) ** n


def compound_present_value(future_value: float, rate: float, periods: int) -> float:
    """复利现值 P = F × (P/F, i, n)。"""
    f = require_positive(future_value, "复利终值")
    r = validate_discount_rate(rate)
    n = require_int(periods)
    return f / ((1.0 + r) ** n)


def ordinary_annuity_present_value(payment: float, rate: float, periods: int) -> float:
    """普通年金现值 P = A × (P/A, i, n)。"""
    a = require_positive(payment, "年金")
    return a * annuity_pv_factor(rate, periods)


def ordinary_annuity_future_value(payment: float, rate: float, periods: int) -> float:
    """普通年金终值 F = A × (F/A, i, n)。"""
    a = require_positive(payment, "年金")
    return a * annuity_fv_factor(rate, periods)


def annuity_due_present_value(payment: float, rate: float, periods: int) -> float:
    """预付年金现值 = 普通年金现值 × (1+i)。"""
    return ordinary_annuity_present_value(payment, rate, periods) * (1.0 + validate_discount_rate(rate))


def annuity_due_future_value(payment: float, rate: float, periods: int) -> float:
    """预付年金终值 = 普通年金终值 × (1+i)。"""
    return ordinary_annuity_future_value(payment, rate, periods) * (1.0 + validate_discount_rate(rate))


def deferred_annuity_present_value(
    payment: float, rate: float, periods: int, deferred_periods: int
) -> float:
    """递延年金现值。

    假设从第 m+1 期期末开始连续支付 n 期：
    P = A × (P/A, i, n) × (P/F, i, m)。
    """
    a = require_positive(payment, "递延年金")
    r = validate_discount_rate(rate)
    n = require_int(periods)
    m = require_int(deferred_periods, "递延期数", min_value=0)
    return a * annuity_pv_factor(r, n) * pv_factor(r, m) if m else a * annuity_pv_factor(r, n)


def deferred_annuity_future_value(payment: float, rate: float, periods: int) -> float:
    """递延年金终值。

    递延只影响首次收付时点，不影响最后一期期末的累计终值，
    因此 F = A × (F/A, i, n)，n 为实际收付期数。
    """
    return ordinary_annuity_future_value(payment, rate, periods)


def perpetuity_present_value(payment: float, rate: float) -> float:
    """永续年金现值 P = A / i；永续年金没有终值。"""
    a = require_positive(payment, "永续年金")
    r = require_positive(rate, "折现率")
    return a / r


def net_present_value(cash_flows: Sequence[float], rate: float) -> float:
    """按 t=0,1,...,n 的现金流计算净现值，流出为负、流入为正。"""
    flows = require_cash_flows(cash_flows)
    r = validate_discount_rate(rate)
    return sum(cf / ((1.0 + r) ** t) for t, cf in enumerate(flows))


def _solve_irr(cash_flows: Sequence[float]) -> Optional[float]:
    """用区间扫描 + brentq 求精确 IRR，仅用于内插法结果校验。"""
    flows = require_cash_flows(cash_flows)
    try:
        from scipy.optimize import brentq
    except ImportError:
        return None

    def f(rate: float) -> float:
        return sum(cf / ((1.0 + rate) ** t) for t, cf in enumerate(flows))

    grid = np.concatenate((np.linspace(-0.8999, -0.01, 90), np.linspace(0.0, 5.0, 501)))
    previous_rate = float(grid[0])
    previous_value = f(previous_rate)
    for point in grid[1:]:
        current_rate = float(point)
        current_value = f(current_rate)
        if abs(current_value) < 1e-12:
            return current_rate
        if previous_value * current_value < 0:
            try:
                return float(brentq(f, previous_rate, current_rate, maxiter=200))
            except ValueError:
                pass
        previous_rate, previous_value = current_rate, current_value
    return None


def interpolate_discount_rate(
    cash_flows: Sequence[float], rate_low: float, rate_high: float
) -> CalcResult:
    """用内插法求使 NPV=0 的折现率，并输出考试答题步骤。

    NPV 与折现率通常呈反向关系；所选两个测试利率必须使 NPV 异号。
    """
    flows = require_cash_flows(cash_flows, min_length=2)
    low = require_rate(rate_low, "较低测试折现率")
    high = require_rate(rate_high, "较高测试折现率")
    if high <= low:
        raise ValidationError("较高测试折现率必须大于较低测试折现率。")
    npv_low = net_present_value(flows, low)
    npv_high = net_present_value(flows, high)
    if abs(npv_low) < 1e-12:
        estimated = low
    elif abs(npv_high) < 1e-12:
        estimated = high
    elif npv_low * npv_high > 0:
        raise ValidationError(
            "两个测试利率对应的 NPV 同号，无法直接内插。"
            "请重新选择使 NPV 一正一负的两个折现率。"
        )
    else:
        estimated = low + npv_low / (npv_low - npv_high) * (high - low)

    npv_estimated = net_present_value(flows, estimated)
    exact = _solve_irr(flows)

    result = CalcResult(
        MODULE,
        "内插法求折现率",
        {
            "现金流量（t=0 起）": flows,
            "较低测试折现率 i1": percent(low),
            "较高测试折现率 i2": percent(high),
            "NPV(i1)": money(npv_low),
            "NPV(i2)": money(npv_high),
        },
    )
    result.add_step(
        "列出净现值方程：NPV = Σ[CF_t/(1+i)^t] = 0，其中 t=0,1,…,n，"
        "初始投资在 t=0 以负数表示。"
    )
    result.add_step(
        f"以 i1={percent(low)} 测试：NPV1 = {money(npv_low)} 元；"
        f"以 i2={percent(high)} 测试：NPV2 = {money(npv_high)} 元。"
    )
    result.add_step(
        "由于 NPV1 与 NPV2 异号，说明真实折现率位于两个测试利率之间，可采用内插法。"
    )
    result.add_step(
        "内插公式：i ≈ i1 + NPV1/(NPV1-NPV2) × (i2-i1)。"
    )
    result.add_step(
        f"i ≈ {percent(low, 4)} + ({money(npv_low)})/"
        f"({money(npv_low)}-({money(npv_high)})) × "
        f"({percent(high, 4)}-{percent(low, 4)}) = {percent(estimated, 4)}。"
    )
    result.add_step(
        f"将估计折现率代回检验：NPV(i) = {money(npv_estimated)} 元，接近 0，结果合理。"
    )
    result.put("内插法折现率 i", percent(estimated, 4))
    result.put("回代净现值 NPV", f"{money(npv_estimated)} 元")
    if exact is not None:
        result.put("精确 IRR（数值求解，供校验）", percent(exact, 4))
        result.add_note("内插法属于线性近似；精确解由数值求根得到，二者可能存在少量差异。")
    result.add_note("答题时应写清测试利率、对应 NPV、异号判断、内插公式及回代检验。")
    result.parameters["NPV(估计 i)"] = money(npv_estimated)
    return result


# ---------------------------------------------------------------------------
# 结果构建（供交互菜单与一键例题复用）
# ---------------------------------------------------------------------------
def compound_fv_result(present_value: float, rate: float, periods: int) -> CalcResult:
    """构建复利终值结果与步骤。"""
    value = compound_future_value(present_value, rate, periods)
    factor = fv_factor(rate, periods)
    result = CalcResult(
        MODULE,
        "复利终值",
        {"复利现值 P": f"{money(present_value)} 元", "年利率 i": percent(rate), "期数 n": periods},
    )
    result.add_step("复利终值公式：F = P × (F/P, i, n) = P × (1+i)^n。")
    result.add_step(f"查/算复利终值系数：(F/P, {percent(rate)}, {periods}) = {factor:.6f}。")
    result.add_step(
        f"F = {money(present_value)} × {factor:.6f} = {money(value)} 元。"
    )
    result.put("复利终值 F", f"{money(value)} 元")
    result.put("复利终值系数", f"{factor:.6f}")
    return result


def compound_pv_result(future_value: float, rate: float, periods: int) -> CalcResult:
    """构建复利现值结果与步骤。"""
    value = compound_present_value(future_value, rate, periods)
    factor = pv_factor(rate, periods)
    result = CalcResult(
        MODULE,
        "复利现值",
        {"复利终值 F": f"{money(future_value)} 元", "年利率 i": percent(rate), "期数 n": periods},
    )
    result.add_step("复利现值公式：P = F × (P/F, i, n) = F ÷ (1+i)^n。")
    result.add_step(f"复利现值系数：(P/F, {percent(rate)}, {periods}) = {factor:.6f}。")
    result.add_step(f"P = {money(future_value)} × {factor:.6f} = {money(value)} 元。")
    result.put("复利现值 P", f"{money(value)} 元")
    result.put("复利现值系数", f"{factor:.6f}")
    return result


def annuity_result(
    payment: float, rate: float, periods: int, *, due: bool, value_type: str
) -> CalcResult:
    """构建普通/预付年金的现值或终值结果。"""
    if value_type not in {"PV", "FV"}:
        raise ValidationError("value_type 只能是 PV 或 FV。")
    if value_type == "PV":
        base = ordinary_annuity_present_value(payment, rate, periods)
        value = base * (1.0 + rate) if due else base
        base_factor = annuity_pv_factor(rate, periods)
        factor = base_factor * (1.0 + rate) if due else base_factor
        title = f"{'预付' if due else '普通'}年金现值"
        formula = "P = A × (P/A, i, n)"
        result = CalcResult(
            MODULE,
            title,
            {"年金 A": f"{money(payment)} 元", "年利率 i": percent(rate), "期数 n": periods},
        )
    else:
        base = ordinary_annuity_future_value(payment, rate, periods)
        value = base * (1.0 + rate) if due else base
        base_factor = annuity_fv_factor(rate, periods)
        factor = base_factor * (1.0 + rate) if due else base_factor
        title = f"{'预付' if due else '普通'}年金终值"
        formula = "F = A × (F/A, i, n)"
        result = CalcResult(
            MODULE,
            title,
            {"年金 A": f"{money(payment)} 元", "年利率 i": percent(rate), "期数 n": periods},
        )
    result.add_step(f"{'普通' if not due else '预付'}年金基本公式：{formula}。")
    result.add_step(
        f"普通年金系数 = {base_factor:.6f}；"
        + ("预付年金系数 = 普通年金系数 × (1+i)。" if due else "本题直接使用普通年金系数。")
    )
    if due:
        result.add_step(
            f"{'现值' if value_type == 'PV' else '终值'}系数 = {base_factor:.6f} × "
            f"(1+{percent(rate)}) = {factor:.6f}。"
        )
    result.add_step(f"计算结果 = {money(payment)} × {factor:.6f} = {money(value)} 元。")
    result.put(f"{title}", f"{money(value)} 元")
    result.put("年金系数", f"{factor:.6f}")
    if due:
        result.add_note("预付年金比普通年金多计一期利息，因此系数需乘以 (1+i)。")
    return result


def deferred_result(payment: float, rate: float, periods: int, deferred_periods: int) -> CalcResult:
    """构建递延年金现值与终值结果。"""
    pv = deferred_annuity_present_value(payment, rate, periods, deferred_periods)
    fv = deferred_annuity_future_value(payment, rate, periods)
    pv_factor_n = annuity_pv_factor(rate, periods)
    discount_factor = pv_factor(rate, deferred_periods)
    fv_factor_n = annuity_fv_factor(rate, periods)
    result = CalcResult(
        MODULE,
        "递延年金现值与终值",
        {
            "每期年金 A": f"{money(payment)} 元",
            "年利率 i": percent(rate),
            "连续收付期数 n": periods,
            "递延期数 m": deferred_periods,
        },
    )
    result.add_step(
        "递延年金从第 m+1 期期末开始连续收付 n 期，t=0 为现在。"
    )
    result.add_step(
        f"现值按两阶段折现：P = A × (P/A, {percent(rate)}, {periods}) × "
        f"(P/F, {percent(rate)}, {deferred_periods})。"
    )
    result.add_step(
        f"P = {money(payment)} × {pv_factor_n:.6f} × {discount_factor:.6f} = {money(pv)} 元。"
    )
    result.add_step(
        "递延年金终值只与连续收付期数 n 有关，递延期不影响累计终值："
        "F = A × (F/A, i, n)。"
    )
    result.add_step(
        f"F = {money(payment)} × {fv_factor_n:.6f} = {money(fv)} 元（发生在最后一期期末）。"
    )
    result.put("递延年金现值 P", f"{money(pv)} 元")
    result.put("递延年金终值 F", f"{money(fv)} 元")
    result.put("年金现值系数 (P/A,i,n)", f"{pv_factor_n:.6f}")
    result.put("复利现值系数 (P/F,i,m)", f"{discount_factor:.6f}")
    result.put("年金终值系数 (F/A,i,n)", f"{fv_factor_n:.6f}")
    return result


def perpetuity_result(payment: float, rate: float) -> CalcResult:
    """构建永续年金现值结果。"""
    pv = perpetuity_present_value(payment, rate)
    result = CalcResult(
        MODULE,
        "永续年金现值",
        {"每期永续年金 A": f"{money(payment)} 元", "折现率 i": percent(rate)},
    )
    result.add_step("永续年金为无限期等额收付，现值公式：P = A / i。")
    result.add_step(f"P = {money(payment)} ÷ {percent(rate)} = {money(pv)} 元。")
    result.put("永续年金现值 P", f"{money(pv)} 元")
    result.put("永续年金终值", "不存在（无限期收付，终值趋于无穷大）")
    result.add_note("永续年金没有终值；题目若要求终值，应说明“无终值/不适用”。")
    return result


def cash_flow_timeline_result(
    cash_flows: Sequence[float], rate: float, title: str = "现金流时间轴"
) -> CalcResult:
    """计算现金流现值并绘制时间轴。"""
    flows = require_cash_flows(cash_flows)
    r = validate_discount_rate(rate)
    npv = net_present_value(flows, r)
    pv_inflows = sum(
        flow / ((1.0 + r) ** t) for t, flow in enumerate(flows) if flow > 0
    )
    pv_outflows = sum(
        flow / ((1.0 + r) ** t) for t, flow in enumerate(flows) if flow < 0
    )
    from visual import plot_cash_flow

    image_path = plot_cash_flow(flows, title=title)
    result = CalcResult(
        MODULE,
        title,
        {"现金流量（t=0 起）": flows, "折现率": percent(r)},
    )
    result.add_step(
        "将各期现金流按发生期数 t 折现到 t=0：PV_t = CF_t/(1+i)^t。"
    )
    result.add_step(
        f"现金流入现值合计 = {money(pv_inflows)} 元；现金流出现值合计 = {money(pv_outflows)} 元。"
    )
    result.add_step(f"净现值 NPV = 流入现值 + 流出现值 = {money(npv)} 元。")
    result.put("现金流入现值", f"{money(pv_inflows)} 元")
    result.put("现金流出现值", f"{money(pv_outflows)} 元")
    result.put("净现值 NPV", f"{money(npv)} 元")
    result.put("时间轴图片", str(image_path))
    result.add_note("时间轴向上为现金流入、向下为现金流出；图片已保存到 image 文件夹。")
    return result


# ---------------------------------------------------------------------------
# 交互菜单
# ---------------------------------------------------------------------------
def _interactive_compound_fv() -> CalcResult:
    present = ask_float("复利现值 P（元）", 100000, min_value=0, allow_negative=False)
    rate = ask_rate_percent("年利率 i", 0.08)
    periods = ask_int("计息期数 n（年）", 5)
    return compound_fv_result(present, rate, periods)


def _interactive_compound_pv() -> CalcResult:
    future = ask_float("复利终值 F（元）", 146932.81, min_value=0, allow_negative=False)
    rate = ask_rate_percent("年利率 i", 0.08)
    periods = ask_int("计息期数 n（年）", 5)
    return compound_pv_result(future, rate, periods)


def _interactive_annuity(value_type: str, due: Optional[bool] = None) -> CalcResult:
    if due is None:
        due = ask_yes_no("是否为预付年金（每期期初收付）？", False)
    payment = ask_float("每期年金 A（元）", 10000, min_value=0, allow_negative=False)
    rate = ask_rate_percent("每期折现率 i", 0.06)
    periods = ask_int("收付期数 n", 5)
    return annuity_result(payment, rate, periods, due=due, value_type=value_type)


def _interactive_deferred() -> CalcResult:
    payment = ask_float("每期年金 A（元）", 10000, min_value=0, allow_negative=False)
    rate = ask_rate_percent("年利率 i", 0.08)
    periods = ask_int("连续收付期数 n", 5)
    deferred = ask_int("递延期数 m", 3, min_value=0)
    return deferred_result(payment, rate, periods, deferred)


def _interactive_perpetuity() -> CalcResult:
    payment = ask_float("每期永续年金 A（元）", 8000, min_value=0, allow_negative=False)
    rate = ask_rate_percent("折现率 i", 0.05)
    return perpetuity_result(payment, rate)


def _interactive_interpolation() -> CalcResult:
    flows = ask_series(
        "现金流量（t=0 起，流出为负）",
        [-10000, 2500, 2500, 2500, 2500, 2500],
        min_length=2,
    )
    low = ask_rate_percent("较低测试折现率 i1", 0.07)
    high = ask_rate_percent("较高测试折现率 i2", 0.09)
    return interpolate_discount_rate(flows, low, high)


def _interactive_timeline() -> CalcResult:
    flows = ask_series(
        "现金流量（t=0 起，流出为负）",
        [-100000, 30000, 35000, 40000, 45000],
        min_length=1,
    )
    rate = ask_rate_percent("折现率 i", 0.10)
    title = ask_text("图表标题", "项目现金流时间轴")
    return cash_flow_timeline_result(flows, rate, title)


def _run_demo() -> None:
    """一键展示模块 1 的全部公式。"""
    print_heading("资金时间价值：全套例题一键演示", "★")
    results = [
        compound_fv_result(100000, 0.08, 5),
        compound_pv_result(146932.81, 0.08, 5),
        annuity_result(10000, 0.06, 5, due=False, value_type="FV"),
        annuity_result(10000, 0.06, 5, due=False, value_type="PV"),
        annuity_result(10000, 0.06, 5, due=True, value_type="FV"),
        annuity_result(10000, 0.06, 5, due=True, value_type="PV"),
        deferred_result(10000, 0.08, 5, 3),
        perpetuity_result(8000, 0.05),
        interpolate_discount_rate([-10000, 2500, 2500, 2500, 2500, 2500], 0.07, 0.09),
    ]
    for result in results:
        show_result(result)
    from visual import plot_cash_flow

    path = plot_cash_flow(
        [-10000, 2500, 2500, 2500, 2500, 2500],
        title="内插法例题现金流时间轴",
        filename="time_value_demo",
    )
    print(f"\n[演示完成] 共 {len(results)} 个结果，已追加导出到 result.csv。")
    print(f"[时间轴图片] {path}")


def run() -> None:
    """模块 1 控制台菜单。"""
    while True:
        print_heading("模块1 资金时间价值（复利、年金、内插法）")
        print("  1. 复利终值 F")
        print("  2. 复利现值 P")
        print("  3. 普通年金终值 F")
        print("  4. 普通年金现值 P")
        print("  5. 预付年金终值 F")
        print("  6. 预付年金现值 P")
        print("  7. 递延年金现值与终值")
        print("  8. 永续年金现值（提示：无终值）")
        print("  9. 内插法求折现率（完整答题步骤）")
        print(" 10. 现金流时间轴与净现值（绘图）")
        print(" 11. 全套例题一键演示")
        print("  0. 返回主菜单")
        try:
            choice = input("请选择功能：").strip()
        except EOFError:
            return
        if choice == "0":
            return
        actions = {
            "1": _interactive_compound_fv,
            "2": _interactive_compound_pv,
            "3": lambda: _interactive_annuity("FV", due=False),
            "4": lambda: _interactive_annuity("PV", due=False),
            "5": lambda: _interactive_annuity("FV", due=True),
            "6": lambda: _interactive_annuity("PV", due=True),
            "7": _interactive_deferred,
            "8": _interactive_perpetuity,
            "9": _interactive_interpolation,
            "10": _interactive_timeline,
        }
        if choice == "11":
            _run_demo()
            pause()
        elif choice in actions:
            run_calculation(actions[choice])
            pause()
        else:
            print("[提示] 无效选项，请输入 0~11。")
