"""模块 4：杠杆原理。

覆盖经营杠杆 DOL、财务杠杆 DFL、总杠杆 DTL，以及杠杆系数的风险解读。
"""

from __future__ import annotations

from utils import (
    CalcResult,
    ValidationError,
    ask_float,
    ask_rate_percent,
    money,
    pause,
    percent,
    print_heading,
    require_nonnegative,
    require_positive,
    require_rate,
    run_calculation,
    show_result,
)


MODULE = "模块4 杠杆原理"


def degree_operating_leverage(
    quantity: float, unit_price: float, unit_variable_cost: float, fixed_cost: float
) -> tuple[float, float, float]:
    """经营杠杆系数 DOL，返回（DOL，边际贡献，EBIT）。"""
    q = require_positive(quantity, "销售量 Q")
    price = require_positive(unit_price, "单价 P")
    variable = require_nonnegative(unit_variable_cost, "单位变动成本 V")
    fixed = require_nonnegative(fixed_cost, "固定经营成本 F")
    if price <= variable:
        raise ValidationError("单价必须大于单位变动成本，否则边际贡献不为正。")
    contribution = q * (price - variable)
    ebit = contribution - fixed
    if abs(ebit) < 1e-12:
        raise ValidationError("EBIT 等于 0，经营杠杆系数无定义（处于盈亏临界点）。")
    return contribution / ebit, contribution, ebit


def degree_financial_leverage(
    ebit: float,
    interest: float,
    preferred_dividend: float = 0.0,
    tax_rate: float = 0.25,
) -> float:
    """财务杠杆系数 DFL = EBIT / [EBIT-I-Dp/(1-T)]。"""
    earnings = require_nonnegative(ebit, "息税前利润 EBIT")
    interest_value = require_nonnegative(interest, "利息费用 I")
    preferred = require_nonnegative(preferred_dividend, "优先股股利 Dp")
    tax = require_rate(tax_rate, "所得税税率 T", max_value=1.0)
    if preferred > 0 and abs(1.0 - tax) < 1e-12:
        raise ValidationError("所得税税率为 100% 时，优先股股利的税前调整无意义。")
    denominator = earnings - interest_value - preferred / (1.0 - tax)
    if abs(denominator) < 1e-12:
        raise ValidationError("普通股股东利润为 0，财务杠杆系数无定义。")
    return earnings / denominator


def degree_total_leverage(dol: float, dfl: float) -> float:
    """总杠杆系数 DTL = DOL × DFL。"""
    return require_positive(dol, "DOL") * require_positive(dfl, "DFL")


def leverage_result(
    quantity: float,
    unit_price: float,
    unit_variable_cost: float,
    fixed_cost: float,
    interest: float,
    preferred_dividend: float = 0.0,
    tax_rate: float = 0.25,
    sales_change: float = 0.10,
) -> CalcResult:
    """完整计算三大杠杆并输出风险解读。"""
    q = require_positive(quantity, "销售量 Q")
    price = require_positive(unit_price, "单价 P")
    variable = require_nonnegative(unit_variable_cost, "单位变动成本 V")
    fixed = require_nonnegative(fixed_cost, "固定经营成本 F")
    interest_value = require_nonnegative(interest, "利息费用 I")
    preferred = require_nonnegative(preferred_dividend, "优先股股利 Dp")
    tax = require_rate(tax_rate, "所得税税率 T", max_value=1.0)
    dol, contribution, ebit = degree_operating_leverage(q, price, variable, fixed)
    dfl = degree_financial_leverage(ebit, interest_value, preferred, tax)
    dtl = degree_total_leverage(dol, dfl)
    break_even_q = fixed / (price - variable)
    margin_of_safety = (q - break_even_q) / q

    result = CalcResult(
        MODULE,
        "经营杠杆、财务杠杆与总杠杆",
        {
            "销售量 Q": f"{q:,.2f} 件",
            "单价 P": f"{money(price)} 元",
            "单位变动成本 V": f"{money(variable)} 元",
            "固定经营成本 F": f"{money(fixed)} 元",
            "利息费用 I": f"{money(interest_value)} 元",
            "优先股股利 Dp": f"{money(preferred)} 元",
            "所得税税率 T": percent(tax),
            "预计销售变动率": percent(sales_change),
        },
    )
    result.add_step(
        f"边际贡献 = Q(P-V) = {q:,.2f} × ({money(price)}-{money(variable)}) = "
        f"{money(contribution)} 元。"
    )
    result.add_step(
        f"息税前利润 EBIT = 边际贡献 - F = {money(contribution)} - {money(fixed)} = "
        f"{money(ebit)} 元。"
    )
    result.add_step(
        f"经营杠杆系数 DOL = 边际贡献 / EBIT = {money(contribution)} ÷ {money(ebit)} = "
        f"{dol:.4f}。"
    )
    after_tax_preferred = preferred / (1.0 - tax) if preferred else 0.0
    denominator = ebit - interest_value - after_tax_preferred
    result.add_step(
        "财务杠杆系数 DFL = EBIT / [EBIT-I-Dp/(1-T)]"
        + (f"，优先股股利税前调整 = {money(after_tax_preferred)} 元" if preferred else "")
        + f" = {money(ebit)} ÷ {money(denominator)} = {dfl:.4f}。"
    )
    result.add_step(
        f"总杠杆系数 DTL = DOL × DFL = {dol:.4f} × {dfl:.4f} = {dtl:.4f}。"
    )
    result.add_step(
        f"若销售量变动 {percent(sales_change)}，则 EBIT 约变动 "
        f"{percent(dol * sales_change)}，普通股每股收益约变动 {percent(dtl * sales_change)}。"
    )

    result.put("边际贡献", f"{money(contribution)} 元")
    result.put("息税前利润 EBIT", f"{money(ebit)} 元")
    result.put("经营杠杆系数 DOL", f"{dol:.4f}")
    result.put("财务杠杆系数 DFL", f"{dfl:.4f}")
    result.put("总杠杆系数 DTL", f"{dtl:.4f}")
    result.put("盈亏临界点销售量", f"{break_even_q:,.2f} 件")
    result.put("安全边际率", percent(margin_of_safety))
    result.put("EBIT 变动幅度", percent(dol * sales_change))
    result.put("每股收益变动幅度", percent(dtl * sales_change))

    if dol > 2:
        result.add_note("DOL 较高：固定经营成本占比大，销量下降会显著放大 EBIT 下降，经营风险较高。")
    elif dol > 1:
        result.add_note("DOL>1：存在经营杠杆效应，销量变化会被放大为 EBIT 变化。")
    else:
        result.add_note("DOL≈1：经营杠杆较低，EBIT 对销量变化不敏感。")
    if dfl > 2:
        result.add_note("DFL 较高：固定融资成本负担重，EBIT 波动会显著放大普通股收益波动。")
    elif dfl > 1:
        result.add_note("DFL>1：存在财务杠杆效应，债务或优先股使普通股收益波动被放大。")
    else:
        result.add_note("DFL≈1：固定融资成本很低，财务风险较小。")
    result.add_note("总杠杆把经营风险与财务风险叠加；高 DTL 意味着销售波动对股东收益影响剧烈。")
    result.add_note("当 EBIT 接近盈亏临界点时，DOL、DFL 会急剧上升，公式结果对参数非常敏感。")
    return result


def _interactive() -> CalcResult:
    q = ask_float("销售量 Q（件）", 10000, min_value=0, allow_negative=False)
    price = ask_float("单价 P（元）", 100, min_value=0, allow_negative=False)
    variable = ask_float("单位变动成本 V（元）", 60, min_value=0, allow_negative=False)
    fixed = ask_float("固定经营成本 F（元）", 200000, min_value=0, allow_negative=False)
    interest = ask_float("利息费用 I（元）", 50000, min_value=0, allow_negative=False)
    preferred = ask_float("优先股股利 Dp（元，无则0）", 0, min_value=0, allow_negative=False)
    tax = ask_rate_percent("所得税税率 T", 0.25, max_percent=100)
    change = ask_rate_percent("预计销售变动率（可负）", 0.10, allow_negative=True)
    return leverage_result(q, price, variable, fixed, interest, preferred, tax, change)


def _run_demo() -> None:
    """一键演示三大杠杆与风险解读。"""
    print_heading("杠杆原理：例题一键演示", "★")
    show_result(leverage_result(10000, 100, 60, 200000, 50000, 0, 0.25, 0.10))
    print("\n[演示完成] DOL=2、DFL≈1.3333、DTL≈2.6667，可用于课堂讲解风险放大效应。")


def run() -> None:
    """模块 4 控制台菜单。"""
    while True:
        print_heading("模块4 杠杆原理（DOL / DFL / DTL）")
        print("  1. 三大杠杆计算与风险解读")
        print("  2. 例题一键演示")
        print("  0. 返回主菜单")
        try:
            choice = input("请选择功能：").strip()
        except EOFError:
            return
        if choice == "0":
            return
        if choice == "1":
            run_calculation(_interactive)
            pause()
        elif choice == "2":
            _run_demo()
            pause()
        else:
            print("[提示] 无效选项，请输入 0~2。")
