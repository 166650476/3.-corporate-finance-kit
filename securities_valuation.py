"""模块 8：证券估值。

覆盖债券价值、债券到期收益率、固定股利/零增长/固定增长股票估值，
以及股票内部收益率。
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
from scipy.optimize import brentq

from utils import (
    CalcResult,
    ValidationError,
    ask_float,
    ask_int,
    ask_rate_percent,
    ask_text,
    money,
    pause,
    percent,
    print_heading,
    require_int,
    require_nonnegative,
    require_positive,
    require_rate,
    run_calculation,
    show_result,
)
from time_value import annuity_pv_factor, pv_factor


MODULE = "模块8 证券估值"


# ---------------------------------------------------------------------------
# 债券估值
# ---------------------------------------------------------------------------
def bond_value(
    face_value: float, coupon_rate: float, years: int, required_yield: float
) -> float:
    """每年付息一次、到期还本的债券价值。"""
    face = require_positive(face_value, "债券面值")
    coupon = require_rate(coupon_rate, "票面利率")
    n = require_int(years, "剩余期限")
    required = require_rate(required_yield, "市场必要收益率")
    annual_interest = face * coupon
    return annual_interest * annuity_pv_factor(required, n) + face * pv_factor(required, n)


def bond_value_result(
    face_value: float, coupon_rate: float, years: int, required_yield: float
) -> CalcResult:
    """构建债券估值结果。"""
    face = require_positive(face_value, "债券面值")
    coupon = require_rate(coupon_rate, "票面利率")
    n = require_int(years, "剩余期限")
    required = require_rate(required_yield, "市场必要收益率")
    annual_interest = face * coupon
    value = bond_value(face, coupon, n, required)
    pv_interest = annual_interest * annuity_pv_factor(required, n)
    pv_face = face * pv_factor(required, n)
    result = CalcResult(
        MODULE,
        "债券价值估算",
        {
            "债券面值": f"{money(face)} 元",
            "票面利率": percent(coupon),
            "剩余期限": f"{n} 年",
            "市场必要收益率": percent(required),
        },
    )
    result.add_step("每年付息一次、到期还本的债券价值：")
    result.add_step(
        "V = 年利息 × (P/A, r, n) + 面值 × (P/F, r, n)。"
    )
    result.add_step(
        f"V = {money(annual_interest)} × {annuity_pv_factor(required, n):.6f} + "
        f"{money(face)} × {pv_factor(required, n):.6f}。"
    )
    result.add_step(
        f"V = 利息现值 {money(pv_interest)} + 本金现值 {money(pv_face)} = {money(value)} 元。"
    )
    result.put("债券价值 V", f"{money(value)} 元")
    result.put("利息现值", f"{money(pv_interest)} 元")
    result.put("本金现值", f"{money(pv_face)} 元")
    if abs(required - coupon) < 1e-12:
        result.add_note("必要收益率等于票面利率，债券价值等于面值（平价）。")
    elif required > coupon:
        result.add_note("必要收益率高于票面利率，债券价值低于面值（折价）。")
    else:
        result.add_note("必要收益率低于票面利率，债券价值高于面值（溢价）。")

    rows = []
    for t in range(1, n + 1):
        cash_flow = annual_interest + (face if t == n else 0.0)
        factor = pv_factor(required, t)
        rows.append(
            {
                "年份": t,
                "现金流入": round(cash_flow, 2),
                "复利现值系数": round(factor, 6),
                "现值": round(cash_flow * factor, 2),
            }
        )
    result.add_table("债券分年现金流折现表", pd.DataFrame(rows))
    return result


def bond_ytm(price: float, face_value: float, coupon_rate: float, years: int) -> float:
    """债券到期收益率：使债券未来现金流现值等于当前价格的折现率。"""
    current_price = require_positive(price, "债券当前价格")
    face = require_positive(face_value, "债券面值")
    coupon = require_rate(coupon_rate, "票面利率")
    n = require_int(years, "剩余期限")
    annual_interest = face * coupon

    def difference(rate: float) -> float:
        return (
            annual_interest * annuity_pv_factor(rate, n)
            + face * pv_factor(rate, n)
            - current_price
        )

    return float(brentq(difference, 0.0, 10.0, maxiter=300))


def bond_ytm_result(
    price: float, face_value: float, coupon_rate: float, years: int
) -> CalcResult:
    """构建债券到期收益率结果。"""
    current_price = require_positive(price, "债券当前价格")
    face = require_positive(face_value, "债券面值")
    coupon = require_rate(coupon_rate, "票面利率")
    n = require_int(years, "剩余期限")
    annual_interest = face * coupon
    ytm = bond_ytm(current_price, face, coupon, n)
    current_yield = annual_interest / current_price
    result = CalcResult(
        MODULE,
        "债券到期收益率（内部收益率）",
        {
            "债券当前价格": f"{money(current_price)} 元",
            "债券面值": f"{money(face)} 元",
            "票面利率": percent(coupon),
            "剩余期限": f"{n} 年",
        },
    )
    result.add_step(
        "到期收益率 r 满足：当前价格 = 年利息×(P/A, r, n) + 面值×(P/F, r, n)。"
    )
    result.add_step(
        f"即 {money(current_price)} = {money(annual_interest)}×(P/A, r, {n}) + "
        f"{money(face)}×(P/F, r, {n})。"
    )
    result.add_step(
        f"用试错法/内插法或数值求根，解得到期收益率 r = {percent(ytm, 4)}。"
    )
    result.add_step(f"当期收益率 = 年利息/当前价格 = {percent(current_yield, 4)}。")
    result.put("到期收益率 YTM", percent(ytm, 4))
    result.put("年利息", f"{money(annual_interest)} 元")
    result.put("当期收益率", percent(current_yield, 4))
    result.add_note("到期收益率假设持有至到期且收到的利息按同一收益率再投资。")
    return result


# ---------------------------------------------------------------------------
# 股票估值
# ---------------------------------------------------------------------------
def zero_growth_stock_value(dividend: float, required_return: float) -> float:
    """零增长（固定）股利永续模型：V = D/r。"""
    d = require_nonnegative(dividend, "每股股利 D")
    r = require_positive(required_return, "必要收益率 r")
    return d / r


def fixed_dividend_stock_value(
    dividend: float, required_return: float, years: int, selling_price: float
) -> float:
    """有限持有期固定股利模型：V=D×(P/A,r,n)+Pn×(P/F,r,n)。"""
    d = require_nonnegative(dividend, "每股固定股利 D")
    r = require_positive(required_return, "必要收益率 r")
    n = require_int(years, "持有期")
    pn = require_nonnegative(selling_price, "期末售价 Pn")
    return d * annuity_pv_factor(r, n) + pn * pv_factor(r, n)


def constant_growth_stock_value(
    current_dividend: float, required_return: float, growth_rate: float
) -> float:
    """固定增长股利模型：V = D1/(r-g) = D0(1+g)/(r-g)。"""
    d0 = require_nonnegative(current_dividend, "当前股利 D0")
    r = require_positive(required_return, "必要收益率 r")
    g = require_rate(growth_rate, "股利增长率 g", allow_negative=True)
    if r <= g:
        raise ValidationError("必要收益率 r 必须大于股利增长率 g，否则固定增长模型无有限价值。")
    return d0 * (1.0 + g) / (r - g)


def zero_growth_stock_result(dividend: float, required_return: float) -> CalcResult:
    """构建零增长股票估值结果。"""
    d = require_nonnegative(dividend, "每股股利 D")
    r = require_positive(required_return, "必要收益率 r")
    value = zero_growth_stock_value(d, r)
    result = CalcResult(
        MODULE,
        "股票价值——零增长（固定）股利模型",
        {"每股股利 D": f"{money(d, 4)} 元", "必要收益率 r": percent(r)},
    )
    result.add_step("零增长股利意味着 D1=D2=…=D，股票价值 V=D/r。")
    result.add_step(f"V = {money(d, 4)} ÷ {percent(r)} = {money(value)} 元/股。")
    result.put("股票价值 V", f"{money(value)} 元/股")
    result.add_note("零增长股利模型假设股利永久保持不变，适用于成熟稳定、股利政策固定的公司。")
    return result


def fixed_dividend_stock_result(
    dividend: float, required_return: float, years: int, selling_price: float
) -> CalcResult:
    """构建有限持有期固定股利股票估值结果。"""
    d = require_nonnegative(dividend, "每股固定股利 D")
    r = require_positive(required_return, "必要收益率 r")
    n = require_int(years, "持有期")
    pn = require_nonnegative(selling_price, "期末售价 Pn")
    value = fixed_dividend_stock_value(d, r, n, pn)
    pv_dividends = d * annuity_pv_factor(r, n)
    pv_price = pn * pv_factor(r, n)
    result = CalcResult(
        MODULE,
        "股票价值——固定股利模型（有限持有期）",
        {
            "每股固定股利 D": f"{money(d, 4)} 元",
            "必要收益率 r": percent(r),
            "持有期 n": f"{n} 年",
            "期末售价 Pn": f"{money(pn, 2)} 元",
        },
    )
    result.add_step("有限持有期固定股利模型：V=D×(P/A,r,n)+Pn×(P/F,r,n)。")
    result.add_step(
        f"股利现值 = {money(d, 4)}×{annuity_pv_factor(r, n):.6f} = {money(pv_dividends)} 元。"
    )
    result.add_step(
        f"售价现值 = {money(pn, 2)}×{pv_factor(r, n):.6f} = {money(pv_price)} 元。"
    )
    result.add_step(f"V = {money(pv_dividends)} + {money(pv_price)} = {money(value)} 元/股。")
    result.put("股票价值 V", f"{money(value)} 元/股")
    result.put("股利现值", f"{money(pv_dividends)} 元")
    result.put("售价现值", f"{money(pv_price)} 元")
    result.add_note("“固定股利模型”在本程序中按有限持有期处理；若永久持有，则使用零增长模型 D/r。")
    return result


def constant_growth_stock_result(
    current_dividend: float, required_return: float, growth_rate: float
) -> CalcResult:
    """构建固定增长股票估值结果。"""
    d0 = require_nonnegative(current_dividend, "当前股利 D0")
    r = require_positive(required_return, "必要收益率 r")
    g = require_rate(growth_rate, "股利增长率 g", allow_negative=True)
    if r <= g:
        raise ValidationError("必要收益率 r 必须大于股利增长率 g。")
    d1 = d0 * (1.0 + g)
    value = constant_growth_stock_value(d0, r, g)
    result = CalcResult(
        MODULE,
        "股票价值——固定增长股利模型",
        {
            "当前每股股利 D0": f"{money(d0, 4)} 元",
            "必要收益率 r": percent(r),
            "股利增长率 g": percent(g),
        },
    )
    result.add_step("固定增长股利模型（Gordon 模型）：V=D1/(r-g)，D1=D0(1+g)。")
    result.add_step(f"D1 = {money(d0, 4)} × (1+{percent(g)}) = {money(d1, 4)} 元。")
    result.add_step(
        f"V = {money(d1, 4)} ÷ ({percent(r)}-{percent(g)}) = {money(value)} 元/股。"
    )
    result.put("预计股利 D1", f"{money(d1, 4)} 元")
    result.put("股票价值 V", f"{money(value)} 元/股")
    result.add_note("固定增长模型要求 r>g；当 g 接近 r 时，估值对假设极其敏感。")
    return result


def stock_internal_return_zero(dividend: float, price: float) -> float:
    """零增长股票内部收益率：r=D/P。"""
    return require_nonnegative(dividend, "每股股利 D") / require_positive(price, "股票价格 P")


def stock_internal_return_growth(
    current_dividend: float, price: float, growth_rate: float
) -> float:
    """固定增长股票内部收益率：r=D1/P+g。"""
    d0 = require_nonnegative(current_dividend, "当前股利 D0")
    p = require_positive(price, "股票价格 P")
    g = require_rate(growth_rate, "股利增长率 g", allow_negative=True)
    return d0 * (1.0 + g) / p + g


def stock_internal_return_fixed(
    dividend: float, price: float, years: int, selling_price: float
) -> float:
    """有限持有期固定股利股票内部收益率。"""
    d = require_nonnegative(dividend, "每股固定股利")
    p = require_positive(price, "股票价格")
    n = require_int(years, "持有期")
    pn = require_nonnegative(selling_price, "期末售价")

    def difference(rate: float) -> float:
        return d * annuity_pv_factor(rate, n) + pn * pv_factor(rate, n) - p

    return float(brentq(difference, 0.0, 10.0, maxiter=300))


def stock_irr_result(
    mode: str,
    price: float,
    dividend: float,
    *,
    growth_rate: float = 0.0,
    years: int = 1,
    selling_price: float = 0.0,
) -> CalcResult:
    """构建股票内部收益率结果。mode: zero / growth / fixed。"""
    p = require_positive(price, "股票价格")
    if mode == "zero":
        d = require_nonnegative(dividend, "每股股利")
        rate = stock_internal_return_zero(d, p)
        result = CalcResult(
            MODULE,
            "股票内部收益率——零增长模型",
            {"股票价格 P": f"{money(p, 2)} 元", "每股股利 D": f"{money(d, 4)} 元"},
        )
        result.add_step("零增长股票内部收益率：r = D / P。")
        result.add_step(f"r = {money(d, 4)} ÷ {money(p, 2)} = {percent(rate, 4)}。")
        result.put("股票内部收益率 r", percent(rate, 4))
    elif mode == "growth":
        d0 = require_nonnegative(dividend, "当前股利 D0")
        g = require_rate(growth_rate, "股利增长率 g", allow_negative=True)
        d1 = d0 * (1.0 + g)
        rate = stock_internal_return_growth(d0, p, g)
        result = CalcResult(
            MODULE,
            "股票内部收益率——固定增长模型",
            {
                "股票价格 P": f"{money(p, 2)} 元",
                "当前股利 D0": f"{money(d0, 4)} 元",
                "股利增长率 g": percent(g),
            },
        )
        result.add_step("由 P=D1/(r-g) 反解：r = D1/P + g，D1=D0(1+g)。")
        result.add_step(
            f"D1={money(d1, 4)} 元，r={money(d1, 4)}/{money(p, 2)}+{percent(g)}"
            f"={percent(rate, 4)}。"
        )
        result.put("预计股利 D1", f"{money(d1, 4)} 元")
        result.put("股票内部收益率 r", percent(rate, 4))
    elif mode == "fixed":
        d = require_nonnegative(dividend, "每股固定股利")
        n = require_int(years, "持有期")
        pn = require_nonnegative(selling_price, "期末售价")
        rate = stock_internal_return_fixed(d, p, n, pn)
        result = CalcResult(
            MODULE,
            "股票内部收益率——有限期固定股利模型",
            {
                "股票价格 P": f"{money(p, 2)} 元",
                "每股固定股利 D": f"{money(d, 4)} 元",
                "持有期 n": f"{n} 年",
                "期末售价 Pn": f"{money(pn, 2)} 元",
            },
        )
        result.add_step("令股票价格等于未来股利和售价的现值：P=D×(P/A,r,n)+Pn×(P/F,r,n)。")
        result.add_step(f"通过试错/内插或数值求根，得到 r={percent(rate, 4)}。")
        result.put("股票内部收益率 r", percent(rate, 4))
    else:
        raise ValidationError("股票内部收益率模型只能是 zero、growth 或 fixed。")
    result.add_note("内部收益率是使证券现金流入现值等于购买价格的折现率，可与投资者必要收益率比较。")
    return result


# ---------------------------------------------------------------------------
# 交互菜单与例题
# ---------------------------------------------------------------------------
def _interactive_bond_value() -> CalcResult:
    return bond_value_result(
        ask_float("债券面值（元）", 1000, min_value=0, allow_negative=False),
        ask_rate_percent("票面利率", 0.08),
        ask_int("剩余期限（年）", 5),
        ask_rate_percent("市场必要收益率", 0.10),
    )


def _interactive_bond_ytm() -> CalcResult:
    return bond_ytm_result(
        ask_float("债券当前价格（元）", 950, min_value=0, allow_negative=False),
        ask_float("债券面值（元）", 1000, min_value=0, allow_negative=False),
        ask_rate_percent("票面利率", 0.08),
        ask_int("剩余期限（年）", 5),
    )


def _interactive_zero_stock() -> CalcResult:
    return zero_growth_stock_result(
        ask_float("每股股利 D（元）", 1.2, min_value=0, allow_negative=False),
        ask_rate_percent("必要收益率 r", 0.10),
    )


def _interactive_fixed_stock() -> CalcResult:
    return fixed_dividend_stock_result(
        ask_float("每股固定股利 D（元）", 1.2, min_value=0, allow_negative=False),
        ask_rate_percent("必要收益率 r", 0.10),
        ask_int("持有期 n（年）", 5),
        ask_float("期末售价 Pn（元）", 22, min_value=0, allow_negative=False),
    )


def _interactive_growth_stock() -> CalcResult:
    return constant_growth_stock_result(
        ask_float("当前每股股利 D0（元）", 1.2, min_value=0, allow_negative=False),
        ask_rate_percent("必要收益率 r", 0.10),
        ask_rate_percent("股利增长率 g", 0.05, allow_negative=True),
    )


def _interactive_stock_irr() -> CalcResult:
    print("  1. 零增长模型 r=D/P")
    print("  2. 固定增长模型 r=D1/P+g")
    print("  3. 有限期固定股利模型")
    mode_choice = input("请选择股票 IRR 模型：").strip()
    price = ask_float("股票价格 P（元）", 20, min_value=0, allow_negative=False)
    if mode_choice == "1":
        return stock_irr_result(
            "zero",
            price,
            ask_float("每股股利 D（元）", 1.2, min_value=0, allow_negative=False),
        )
    if mode_choice == "2":
        return stock_irr_result(
            "growth",
            price,
            ask_float("当前每股股利 D0（元）", 1.2, min_value=0, allow_negative=False),
            growth_rate=ask_rate_percent("股利增长率 g", 0.05, allow_negative=True),
        )
    if mode_choice == "3":
        return stock_irr_result(
            "fixed",
            price,
            ask_float("每股固定股利 D（元）", 1.2, min_value=0, allow_negative=False),
            years=ask_int("持有期 n（年）", 5),
            selling_price=ask_float("期末售价 Pn（元）", 22, min_value=0, allow_negative=False),
        )
    raise ValidationError("股票 IRR 模型只能选择 1、2 或 3。")


def _run_demo() -> None:
    """一键演示债券和股票估值。"""
    print_heading("证券估值：全套例题一键演示", "★")
    show_result(bond_value_result(1000, 0.08, 5, 0.10))
    show_result(bond_ytm_result(950, 1000, 0.08, 5))
    show_result(zero_growth_stock_result(1.2, 0.10))
    show_result(fixed_dividend_stock_result(1.2, 0.10, 5, 22))
    show_result(constant_growth_stock_result(1.2, 0.10, 0.05))
    show_result(stock_irr_result("zero", 20, 1.2))
    show_result(stock_irr_result("growth", 20, 1.2, growth_rate=0.05))
    show_result(stock_irr_result("fixed", 20, 1.2, years=5, selling_price=22))
    print("\n[演示完成] 已覆盖债券价值、YTM、三种股票估值及股票内部收益率。")


def run() -> None:
    """模块 8 控制台菜单。"""
    while True:
        print_heading("模块8 证券估值（债券 / 股票）")
        print("  1. 债券价值估算")
        print("  2. 债券到期收益率（内部收益率）")
        print("  3. 股票价值——零增长（固定）股利模型")
        print("  4. 股票价值——固定股利模型（有限持有期）")
        print("  5. 股票价值——固定增长股利模型")
        print("  6. 股票内部收益率（三种模型）")
        print("  7. 全套例题一键演示")
        print("  0. 返回主菜单")
        try:
            choice = input("请选择功能：").strip()
        except EOFError:
            return
        if choice == "0":
            return
        actions = {
            "1": _interactive_bond_value,
            "2": _interactive_bond_ytm,
            "3": _interactive_zero_stock,
            "4": _interactive_fixed_stock,
            "5": _interactive_growth_stock,
            "6": _interactive_stock_irr,
        }
        if choice == "7":
            _run_demo()
            pause()
        elif choice in actions:
            run_calculation(actions[choice])
            pause()
        else:
            print("[提示] 无效选项，请输入 0~7。")
