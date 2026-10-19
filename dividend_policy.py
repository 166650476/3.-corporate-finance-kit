"""模块 10：股利分配管理。

覆盖四种股利政策，以及股票股利、股票分割和股票回购的影响。
"""

from __future__ import annotations

from typing import List

import pandas as pd

from utils import (
    CalcResult,
    ValidationError,
    ask_float,
    ask_int,
    ask_rate_percent,
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


MODULE = "模块10 股利分配管理"


def residual_dividend_result(
    capital_budget: float,
    target_debt_ratio: float,
    net_income: float,
    shares: float = 1000000,
) -> CalcResult:
    """剩余股利政策。"""
    budget = require_positive(capital_budget, "投资资金预算")
    debt_ratio = require_rate(target_debt_ratio, "目标资产负债率", max_value=1.0)
    income = require_nonnegative(net_income, "净利润")
    share_count = require_positive(shares, "普通股股数")
    equity_needed = budget * (1.0 - debt_ratio)
    dividends = max(income - equity_needed, 0.0)
    external_equity = max(equity_needed - income, 0.0)
    payout_ratio = dividends / income if income > 0 else 0.0
    dps = dividends / share_count
    retained = income - dividends
    result = CalcResult(
        MODULE,
        "剩余股利政策",
        {
            "投资资金预算": f"{money(budget)} 元",
            "目标资产负债率": percent(debt_ratio),
            "净利润": f"{money(income)} 元",
            "普通股股数": f"{share_count:,.0f} 股",
        },
    )
    result.add_step("剩余股利政策优先满足目标资本结构下的权益资金需求，剩余利润再分配股利。")
    result.add_step(
        f"投资所需权益资金 = 资金预算×(1-负债比例) = {money(budget)}×(1-{percent(debt_ratio)}) "
        f"= {money(equity_needed)} 元。"
    )
    result.add_step(
        f"可分配股利 = max(净利润-权益资金需求,0) = max({money(income)}-{money(equity_needed)},0) "
        f"= {money(dividends)} 元。"
    )
    result.add_step(
        f"留存收益 = 净利润-股利 = {money(income)}-{money(dividends)} = {money(retained)} 元。"
    )
    if external_equity > 0:
        result.add_step(f"净利润不足以满足权益资金需求，需外部权益融资 {money(external_equity)} 元。")
    result.add_step(f"每股股利 = 股利总额/股数 = {money(dps, 4)} 元/股。")
    result.put("投资所需权益资金", f"{money(equity_needed)} 元")
    result.put("股利总额", f"{money(dividends)} 元")
    result.put("每股股利 DPS", f"{money(dps, 4)} 元/股")
    result.put("留存收益", f"{money(retained)} 元")
    result.put("股利支付率", percent(payout_ratio))
    result.put("需外部权益融资", f"{money(external_equity)} 元")
    result.add_note("剩余股利政策有利于保持目标资本结构、降低资本成本，但股利波动较大。")
    return result


def stable_dividend_result(
    prior_dps: float,
    growth_rate: float,
    years: int,
    shares: float,
    net_income: float,
) -> CalcResult:
    """固定或稳定增长股利政策；增长率为 0 即固定股利。"""
    prior = require_positive(prior_dps, "上年每股股利")
    g = require_rate(growth_rate, "股利增长率", allow_negative=True)
    n = require_int(years, "预测年数")
    share_count = require_positive(shares, "普通股股数")
    income = require_nonnegative(net_income, "预计年净利润")
    rows: List[dict] = []
    dps = prior
    for year in range(1, n + 1):
        dps = dps * (1.0 + g)
        total = dps * share_count
        payout = total / income if income > 0 else None
        rows.append(
            {
                "年份": year,
                "每股股利（元/股）": round(dps, 4),
                "股利总额（元）": round(total, 2),
                "股利支付率": "不适用" if payout is None else f"{payout * 100:.2f}%",
            }
        )
    final_dps = rows[-1]["每股股利（元/股）"]
    final_total = final_dps * share_count
    result = CalcResult(
        MODULE,
        "固定或稳定增长股利政策",
        {
            "上年每股股利": f"{money(prior, 4)} 元/股",
            "股利增长率": percent(g),
            "预测年数": f"{n} 年",
            "普通股股数": f"{share_count:,.0f} 股",
            "预计年净利润": f"{money(income)} 元",
        },
    )
    result.add_step("固定或稳定增长股利政策：DPS_t = DPS_0×(1+g)^t。")
    if abs(g) < 1e-12:
        result.add_step("增长率 g=0，即每年保持固定每股股利。")
    result.add_step(
        f"第 {n} 年每股股利 = {money(prior, 4)}×(1+{percent(g)})^{n} = {money(final_dps, 4)} 元/股。"
    )
    result.add_step(
        f"第 {n} 年股利总额 = {money(final_dps, 4)}×{share_count:,.0f} = {money(final_total)} 元。"
    )
    result.put("预测期每股股利", f"{money(final_dps, 4)} 元/股")
    result.put("预测期股利总额", f"{money(final_total)} 元")
    result.add_table("固定/稳定增长股利预测表", pd.DataFrame(rows))
    result.add_note("该政策向市场传递稳定信号，有利于股价稳定，但股利与盈利脱节时可能增加财务压力。")
    return result


def fixed_payout_result(net_income: float, payout_ratio: float, shares: float) -> CalcResult:
    """固定股利支付率政策。"""
    income = require_nonnegative(net_income, "净利润")
    ratio = require_rate(payout_ratio, "股利支付率", max_value=1.0)
    share_count = require_positive(shares, "普通股股数")
    dividends = income * ratio
    dps = dividends / share_count
    retained = income - dividends
    result = CalcResult(
        MODULE,
        "固定股利支付率政策",
        {
            "净利润": f"{money(income)} 元",
            "股利支付率": percent(ratio),
            "普通股股数": f"{share_count:,.0f} 股",
        },
    )
    result.add_step("固定股利支付率政策：股利总额=净利润×股利支付率。")
    result.add_step(f"股利总额 = {money(income)}×{percent(ratio)} = {money(dividends)} 元。")
    result.add_step(f"每股股利 = {money(dividends)}÷{share_count:,.0f} = {money(dps, 4)} 元/股。")
    result.add_step(
        f"留存收益 = 净利润×(1-支付率) = {money(income)}×{percent(1 - ratio)} = {money(retained)} 元。"
    )
    result.put("股利总额", f"{money(dividends)} 元")
    result.put("每股股利 DPS", f"{money(dps, 4)} 元/股")
    result.put("留存收益", f"{money(retained)} 元")
    result.put("利润留存率", percent(1.0 - ratio))
    result.add_note("固定支付率政策使股利随盈利同比例波动，不利于股价稳定。")
    return result


def low_regular_extra_result(
    net_income: float,
    shares: float,
    regular_dps: float,
    extra_dps: float,
) -> CalcResult:
    """低正常股利加额外股利政策。"""
    income = require_nonnegative(net_income, "净利润")
    share_count = require_positive(shares, "普通股股数")
    regular = require_nonnegative(regular_dps, "低正常每股股利")
    extra = require_nonnegative(extra_dps, "额外每股股利")
    total_dps = regular + extra
    dividends = total_dps * share_count
    regular_total = regular * share_count
    extra_total = extra * share_count
    payout = dividends / income if income > 0 else 0.0
    result = CalcResult(
        MODULE,
        "低正常股利加额外股利政策",
        {
            "净利润": f"{money(income)} 元",
            "普通股股数": f"{share_count:,.0f} 股",
            "低正常每股股利": f"{money(regular, 4)} 元/股",
            "额外每股股利": f"{money(extra, 4)} 元/股",
        },
    )
    result.add_step("低正常股利加额外股利政策：每股股利=低正常股利+额外股利。")
    result.add_step(
        f"正常股利 = {money(regular, 4)}×{share_count:,.0f} = {money(regular_total)} 元；"
        f"额外股利 = {money(extra, 4)}×{share_count:,.0f} = {money(extra_total)} 元。"
    )
    result.add_step(
        f"每股股利 = {money(regular, 4)}+{money(extra, 4)} = {money(total_dps, 4)} 元/股；"
        f"股利总额 = {money(dividends)} 元。"
    )
    result.add_step(f"股利支付率 = {money(dividends)}/{money(income)} = {percent(payout)}。")
    result.put("每股股利 DPS", f"{money(total_dps, 4)} 元/股")
    result.put("股利总额", f"{money(dividends)} 元")
    result.put("其中：正常股利", f"{money(regular_total)} 元")
    result.put("其中：额外股利", f"{money(extra_total)} 元")
    result.put("股利支付率", percent(payout))
    result.add_note("该政策兼顾稳定性和灵活性：盈利好时发放额外股利，盈利差时仍保证低正常股利。")
    return result


# ---------------------------------------------------------------------------
# 股票股利、股票分割与股票回购
# ---------------------------------------------------------------------------
def stock_dividend_result(
    shares: float,
    stock_dividend_ratio: float,
    price: float,
    net_profit: float,
) -> CalcResult:
    """股票股利影响：股数增加、每股价格与 EPS 被摊薄。"""
    old_shares = require_positive(shares, "原普通股股数")
    ratio = require_nonnegative(stock_dividend_ratio, "股票股利比例")
    pre_price = require_positive(price, "发放前股价")
    profit = require_nonnegative(net_profit, "净利润")
    new_shares = old_shares * (1.0 + ratio)
    theoretical_price = old_shares * pre_price / new_shares
    eps_before = profit / old_shares
    eps_after = profit / new_shares
    market_cap_before = old_shares * pre_price
    market_cap_after = new_shares * theoretical_price
    result = CalcResult(
        MODULE,
        "股票股利影响",
        {
            "原普通股股数": f"{old_shares:,.0f} 股",
            "股票股利比例": f"每10股送{ratio * 10:.2f}股（{percent(ratio)}）",
            "发放前股价": f"{money(pre_price, 2)} 元",
            "净利润": f"{money(profit)} 元",
        },
    )
    result.add_step("股票股利不改变股东权益总额，只把留存收益转为股本，增加股数。")
    result.add_step(
        f"新股数 = 原股数×(1+送股比例) = {old_shares:,.0f}×(1+{percent(ratio)}) "
        f"= {new_shares:,.0f} 股。"
    )
    result.add_step(
        f"理论除权价 = 原市值/新股数 = {money(market_cap_before)}/{new_shares:,.0f} "
        f"= {money(theoretical_price, 4)} 元/股。"
    )
    result.add_step(
        f"EPS 由 {money(eps_before, 4)} 元/股降至 {money(eps_after, 4)} 元/股；"
        "原股东持股数量增加但持股比例不变。"
    )
    result.put("发放后股数", f"{new_shares:,.0f} 股")
    result.put("理论除权价", f"{money(theoretical_price, 4)} 元/股")
    result.put("发放前 EPS", f"{money(eps_before, 4)} 元/股")
    result.put("发放后 EPS", f"{money(eps_after, 4)} 元/股")
    result.put("原市值", f"{money(market_cap_before)} 元")
    result.put("理论总市值", f"{money(market_cap_after)} 元")
    result.add_note("理论上股票股利不改变股东财富，但可能传递成长信号；实际股价还受市场因素影响。")
    return result


def stock_split_result(
    shares: float,
    split_ratio: float,
    price: float,
    net_profit: float,
) -> CalcResult:
    """股票分割影响；split_ratio=2 表示 1 股拆为 2 股。"""
    old_shares = require_positive(shares, "分割前股数")
    ratio = require_positive(split_ratio, "股票分割比例")
    pre_price = require_positive(price, "分割前股价")
    profit = require_nonnegative(net_profit, "净利润")
    new_shares = old_shares * ratio
    theoretical_price = pre_price / ratio
    eps_before = profit / old_shares
    eps_after = profit / new_shares
    result = CalcResult(
        MODULE,
        "股票分割影响",
        {
            "分割前股数": f"{old_shares:,.0f} 股",
            "分割比例": f"1拆{ratio:g}",
            "分割前股价": f"{money(pre_price, 2)} 元",
            "净利润": f"{money(profit)} 元",
        },
    )
    result.add_step("股票分割降低每股面值和股价、增加股数，但不改变股东权益总额和持股比例。")
    result.add_step(f"分割后股数 = {old_shares:,.0f}×{ratio:g} = {new_shares:,.0f} 股。")
    result.add_step(
        f"理论分割后股价 = {money(pre_price, 2)}÷{ratio:g} = {money(theoretical_price, 4)} 元/股。"
    )
    result.add_step(
        f"EPS 由 {money(eps_before, 4)} 元/股变为 {money(eps_after, 4)} 元/股，"
        "总市值理论保持不变。"
    )
    result.put("分割后股数", f"{new_shares:,.0f} 股")
    result.put("理论分割后股价", f"{money(theoretical_price, 4)} 元/股")
    result.put("分割前 EPS", f"{money(eps_before, 4)} 元/股")
    result.put("分割后 EPS", f"{money(eps_after, 4)} 元/股")
    result.add_note("股票分割常用于降低股价、提高流动性；反向分割则提高股价、减少股数。")
    return result


def stock_repurchase_result(
    net_profit: float,
    shares: float,
    price: float,
    repurchase_amount: float,
) -> CalcResult:
    """股票回购影响：股数减少、EPS 提高（假设净利润不变）。"""
    profit = require_nonnegative(net_profit, "净利润")
    old_shares = require_positive(shares, "回购前股数")
    buyback_price = require_positive(price, "回购价格")
    amount = require_positive(repurchase_amount, "回购金额")
    market_cap = old_shares * buyback_price
    if amount >= market_cap:
        raise ValidationError("回购金额必须小于公司总市值，否则无法保留剩余股份。")
    repurchased = amount / buyback_price
    remaining = old_shares - repurchased
    if remaining <= 0:
        raise ValidationError("回购后剩余股数必须大于 0。")
    eps_before = profit / old_shares
    eps_after = profit / remaining
    eps_change = (eps_after - eps_before) / eps_before if eps_before > 0 else 0.0
    theoretical_price = (market_cap - amount) / remaining
    result = CalcResult(
        MODULE,
        "股票回购影响",
        {
            "净利润": f"{money(profit)} 元",
            "回购前股数": f"{old_shares:,.0f} 股",
            "回购价格": f"{money(buyback_price, 2)} 元",
            "回购金额": f"{money(amount)} 元",
        },
    )
    result.add_step("股票回购减少流通股数；在净利润不变时，EPS 会因分母减少而提高。")
    result.add_step(
        f"回购股数 = 回购金额/回购价格 = {money(amount)}/{money(buyback_price, 2)} "
        f"= {repurchased:,.2f} 股。"
    )
    result.add_step(f"回购后股数 = {old_shares:,.0f}-{repurchased:,.2f} = {remaining:,.2f} 股。")
    result.add_step(
        f"回购前 EPS = {money(eps_before, 4)} 元/股；回购后 EPS = {money(eps_after, 4)} 元/股；"
        f"提高 {percent(eps_change)}。"
    )
    result.add_step(
        f"在忽略信号效应和税负的假设下，回购后理论股价 = "
        f"({money(market_cap)}-{money(amount)})/{remaining:,.2f} = "
        f"{money(theoretical_price, 4)} 元/股，与回购价基本一致。"
    )
    result.put("回购股数", f"{repurchased:,.2f} 股")
    result.put("回购后股数", f"{remaining:,.2f} 股")
    result.put("回购前 EPS", f"{money(eps_before, 4)} 元/股")
    result.put("回购后 EPS", f"{money(eps_after, 4)} 元/股")
    result.put("EPS 提高幅度", percent(eps_change))
    result.put("理论回购后股价", f"{money(theoretical_price, 4)} 元/股")
    result.add_note("回购可提高 EPS 和资金使用效率，但也可能减少现金、增加财务风险，并影响控制权。")
    return result


# ---------------------------------------------------------------------------
# 交互菜单与例题
# ---------------------------------------------------------------------------
def _interactive_residual() -> CalcResult:
    return residual_dividend_result(
        ask_float("投资资金预算（元）", 2000000, min_value=0, allow_negative=False),
        ask_rate_percent("目标资产负债率", 0.50, max_percent=100),
        ask_float("净利润（元）", 2000000, min_value=0, allow_negative=False),
        ask_float("普通股股数（股）", 1000000, min_value=0, allow_negative=False),
    )


def _interactive_stable() -> CalcResult:
    return stable_dividend_result(
        ask_float("上年每股股利（元/股）", 1.0, min_value=0, allow_negative=False),
        ask_rate_percent("股利增长率（0表示固定股利）", 0.05, allow_negative=True),
        ask_int("预测年数", 3),
        ask_float("普通股股数（股）", 1000000, min_value=0, allow_negative=False),
        ask_float("预计年净利润（元）", 3000000, min_value=0, allow_negative=False),
    )


def _interactive_fixed_payout() -> CalcResult:
    return fixed_payout_result(
        ask_float("净利润（元）", 3000000, min_value=0, allow_negative=False),
        ask_rate_percent("股利支付率", 0.40, max_percent=100),
        ask_float("普通股股数（股）", 1000000, min_value=0, allow_negative=False),
    )


def _interactive_low_regular() -> CalcResult:
    return low_regular_extra_result(
        ask_float("净利润（元）", 2000000, min_value=0, allow_negative=False),
        ask_float("普通股股数（股）", 1000000, min_value=0, allow_negative=False),
        ask_float("低正常每股股利（元/股）", 0.50, min_value=0, allow_negative=False),
        ask_float("额外每股股利（元/股）", 0.30, min_value=0, allow_negative=False),
    )


def _interactive_stock_dividend() -> CalcResult:
    return stock_dividend_result(
        ask_float("原普通股股数（股）", 1000000, min_value=0, allow_negative=False),
        ask_rate_percent("股票股利比例（10送X的比例）", 0.10, max_percent=100),
        ask_float("发放前股价（元）", 20, min_value=0, allow_negative=False),
        ask_float("净利润（元）", 2000000, min_value=0, allow_negative=False),
    )


def _interactive_stock_split() -> CalcResult:
    return stock_split_result(
        ask_float("分割前股数（股）", 1000000, min_value=0, allow_negative=False),
        ask_float("分割比例（如2表示1拆2）", 2, min_value=0, allow_negative=False),
        ask_float("分割前股价（元）", 20, min_value=0, allow_negative=False),
        ask_float("净利润（元）", 2000000, min_value=0, allow_negative=False),
    )


def _interactive_repurchase() -> CalcResult:
    return stock_repurchase_result(
        ask_float("净利润（元）", 2000000, min_value=0, allow_negative=False),
        ask_float("回购前股数（股）", 1000000, min_value=0, allow_negative=False),
        ask_float("回购价格（元/股）", 20, min_value=0, allow_negative=False),
        ask_float("回购金额（元）", 2000000, min_value=0, allow_negative=False),
    )


def _run_demo() -> None:
    """一键演示七类股利分配问题。"""
    print_heading("股利分配管理：全套例题一键演示", "★")
    show_result(residual_dividend_result(2000000, 0.50, 2000000, 1000000))
    show_result(stable_dividend_result(1.0, 0.05, 3, 1000000, 3000000))
    show_result(fixed_payout_result(3000000, 0.40, 1000000))
    show_result(low_regular_extra_result(2000000, 1000000, 0.50, 0.30))
    show_result(stock_dividend_result(1000000, 0.10, 20, 2000000))
    show_result(stock_split_result(1000000, 2, 20, 2000000))
    show_result(stock_repurchase_result(2000000, 1000000, 20, 2000000))
    print("\n[演示完成] 已覆盖四种股利政策及股票股利、拆股、回购影响。")


def run() -> None:
    """模块 10 控制台菜单。"""
    while True:
        print_heading("模块10 股利分配管理")
        print("  1. 剩余股利政策")
        print("  2. 固定或稳定增长股利政策")
        print("  3. 固定股利支付率政策")
        print("  4. 低正常股利加额外股利政策")
        print("  5. 股票股利影响")
        print("  6. 股票分割影响")
        print("  7. 股票回购影响")
        print("  8. 全套例题一键演示")
        print("  0. 返回主菜单")
        try:
            choice = input("请选择功能：").strip()
        except EOFError:
            return
        if choice == "0":
            return
        actions = {
            "1": _interactive_residual,
            "2": _interactive_stable,
            "3": _interactive_fixed_payout,
            "4": _interactive_low_regular,
            "5": _interactive_stock_dividend,
            "6": _interactive_stock_split,
            "7": _interactive_repurchase,
        }
        if choice == "8":
            _run_demo()
            pause()
        elif choice in actions:
            run_calculation(actions[choice])
            pause()
        else:
            print("[提示] 无效选项，请输入 0~8。")
