"""模块 3：资本成本。

覆盖 CAPM、债务资本成本（一般模式/贴现模式）、普通股资本成本
（股利增长模型/CAPM）、留存收益资本成本和加权平均资本成本 WACC。
"""

from __future__ import annotations

from typing import Dict, List, Sequence

from scipy.optimize import brentq

from utils import (
    CalcResult,
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


MODULE = "模块3 资本成本"


# ---------------------------------------------------------------------------
# 资本资产定价模型
# ---------------------------------------------------------------------------
def capm_required_return(risk_free_rate: float, beta: float, market_return: float) -> float:
    """CAPM：K = Rf + β × (Rm - Rf)。"""
    rf = require_rate(risk_free_rate, "无风险收益率")
    b = require_nonnegative(beta, "β系数")
    rm = require_rate(market_return, "市场组合收益率")
    return rf + b * (rm - rf)


def capm_result(risk_free_rate: float, beta: float, market_return: float) -> CalcResult:
    """构建 CAPM 必要收益率结果。"""
    rf = require_rate(risk_free_rate, "无风险收益率")
    b = require_nonnegative(beta, "β系数")
    rm = require_rate(market_return, "市场组合收益率")
    cost = capm_required_return(rf, b, rm)
    premium = rm - rf
    result = CalcResult(
        MODULE,
        "CAPM 必要收益率",
        {"无风险收益率 Rf": percent(rf), "β系数": f"{b:.4f}", "市场组合收益率 Rm": percent(rm)},
    )
    result.add_step("资本资产定价模型：K = Rf + β × (Rm - Rf)。")
    result.add_step(f"市场风险溢价 = Rm - Rf = {percent(rm)} - {percent(rf)} = {percent(premium)}。")
    result.add_step(f"K = {percent(rf)} + {b:.4f} × {percent(premium)} = {percent(cost, 4)}。")
    result.put("市场风险溢价", percent(premium, 4))
    result.put("必要收益率（资本成本）", percent(cost, 4))
    if b > 1:
        result.add_note("β>1，说明该资产系统风险高于市场平均水平，要求更高的风险补偿。")
    elif b < 1:
        result.add_note("β<1，说明该资产系统风险低于市场平均水平。")
    else:
        result.add_note("β=1，说明该资产系统风险与市场组合相同。")
    return result


# ---------------------------------------------------------------------------
# 债务资本成本
# ---------------------------------------------------------------------------
def debt_cost_general(
    annual_interest: float,
    debt_amount: float,
    tax_rate: float,
    flotation_rate: float = 0.0,
) -> float:
    """债务资本成本——一般模式。

    Kd = 年利息 × (1-所得税税率) / [债务筹资额 × (1-筹资费率)]。
    """
    interest = require_nonnegative(annual_interest, "年利息")
    amount = require_positive(debt_amount, "债务筹资额")
    tax = require_rate(tax_rate, "所得税税率", max_value=1.0)
    fee = require_rate(flotation_rate, "筹资费率", max_value=0.999)
    return interest * (1.0 - tax) / (amount * (1.0 - fee))


def debt_cost_general_result(
    annual_interest: float,
    debt_amount: float,
    tax_rate: float,
    flotation_rate: float = 0.0,
) -> CalcResult:
    """构建债务资本成本一般模式结果。"""
    interest = require_nonnegative(annual_interest, "年利息")
    amount = require_positive(debt_amount, "债务筹资额")
    tax = require_rate(tax_rate, "所得税税率", max_value=1.0)
    fee = require_rate(flotation_rate, "筹资费率", max_value=0.999)
    cost = debt_cost_general(interest, amount, tax, fee)
    result = CalcResult(
        MODULE,
        "债务资本成本——一般模式",
        {
            "年利息 I": f"{money(interest)} 元",
            "债务筹资额 L": f"{money(amount)} 元",
            "所得税税率 T": percent(tax),
            "筹资费率 f": percent(fee),
        },
    )
    result.add_step("一般模式公式：Kd = I × (1-T) / [L × (1-f)]。")
    result.add_step(
        f"债务利息具有抵税作用，税后利息 = {money(interest)} × (1-{percent(tax)}) = "
        f"{money(interest * (1 - tax))} 元。"
    )
    result.add_step(
        f"实际筹资净额 = {money(amount)} × (1-{percent(fee)}) = {money(amount * (1 - fee))} 元。"
    )
    result.add_step(
        f"Kd = {money(interest * (1 - tax))} ÷ {money(amount * (1 - fee))} = {percent(cost, 4)}。"
    )
    result.put("债务资本成本 Kd", percent(cost, 4))
    result.add_note("一般模式计算简便，但没有考虑利息支付时间分布和本金偿还时点。")
    return result


def debt_cost_discount(
    face_value: float,
    coupon_rate: float,
    years: int,
    issue_price: float,
    tax_rate: float,
    flotation_rate: float = 0.0,
) -> tuple[float, float]:
    """债务资本成本——贴现模式，返回（税后成本，税前成本）。"""
    face = require_positive(face_value, "债券面值")
    coupon = require_rate(coupon_rate, "票面利率")
    n = require_int(years, "债券期限")
    price = require_positive(issue_price, "发行价格")
    tax = require_rate(tax_rate, "所得税税率", max_value=1.0)
    fee = require_rate(flotation_rate, "筹资费率", max_value=0.999)
    proceeds = price * (1.0 - fee)
    annual_interest = face * coupon

    def after_tax_npv(rate: float) -> float:
        pv_coupons = sum(
            annual_interest * (1.0 - tax) / ((1.0 + rate) ** t) for t in range(1, n + 1)
        )
        return pv_coupons + face / ((1.0 + rate) ** n) - proceeds

    def before_tax_npv(rate: float) -> float:
        pv_coupons = sum(annual_interest / ((1.0 + rate) ** t) for t in range(1, n + 1))
        return pv_coupons + face / ((1.0 + rate) ** n) - proceeds

    after_tax = brentq(after_tax_npv, -0.999, 10.0, maxiter=300)
    before_tax = brentq(before_tax_npv, -0.999, 10.0, maxiter=300)
    return float(after_tax), float(before_tax)


def debt_cost_discount_result(
    face_value: float,
    coupon_rate: float,
    years: int,
    issue_price: float,
    tax_rate: float,
    flotation_rate: float = 0.0,
) -> CalcResult:
    """构建债务资本成本贴现模式结果与求解步骤。"""
    face = require_positive(face_value, "债券面值")
    coupon = require_rate(coupon_rate, "票面利率")
    n = require_int(years, "债券期限")
    price = require_positive(issue_price, "发行价格")
    tax = require_rate(tax_rate, "所得税税率", max_value=1.0)
    fee = require_rate(flotation_rate, "筹资费率", max_value=0.999)
    proceeds = price * (1.0 - fee)
    interest = face * coupon
    after_tax, before_tax = debt_cost_discount(face, coupon, n, price, tax, fee)

    pv_coupons = interest * (1.0 - tax) * annuity_pv_factor(after_tax, n)
    pv_face = face * pv_factor(after_tax, n)
    result = CalcResult(
        MODULE,
        "债务资本成本——贴现模式",
        {
            "债券面值": f"{money(face)} 元",
            "票面利率": percent(coupon),
            "期限": f"{n} 年",
            "发行价格": f"{money(price)} 元",
            "筹资费率": percent(fee),
            "所得税税率": percent(tax),
        },
    )
    result.add_step(
        f"实际筹资净额 = 发行价格 × (1-筹资费率) = {money(price)} × "
        f"(1-{percent(fee)}) = {money(proceeds)} 元。"
    )
    result.add_step(
        "贴现模式方程：筹资净额 = Σ[面值×票面利率×(1-T)/(1+Kd)^t] + 面值/(1+Kd)^n。"
    )
    result.add_step(
        f"代入数据：{money(proceeds)} = {money(interest)}×(1-{percent(tax)})×"
        f"(P/A, Kd, {n}) + {money(face)}×(P/F, Kd, {n})。"
    )
    result.add_step(
        "采用逐步测试结合内插法（程序用 Brent 数值求根）求解，得到税后债务资本成本 "
        f"Kd = {percent(after_tax, 4)}。"
    )
    result.add_step(
        f"将 Kd 代回：税后利息现值 {money(pv_coupons)} + 本金现值 {money(pv_face)} "
        f"= {money(pv_coupons + pv_face)} 元，与筹资净额基本相等。"
    )
    result.add_step(
        f"税前债务资本成本（未考虑利息抵税）= {percent(before_tax, 4)}；"
        f"税后成本约等于税前成本 × (1-T) = {percent(before_tax * (1 - tax), 4)}。"
    )
    result.put("实际筹资净额", f"{money(proceeds)} 元")
    result.put("税后债务资本成本 Kd", percent(after_tax, 4))
    result.put("税前债务资本成本", percent(before_tax, 4))
    result.put("税后利息现值", f"{money(pv_coupons)} 元")
    result.put("本金现值", f"{money(pv_face)} 元")
    result.add_note("贴现模式同时考虑利息时间分布、本金偿还和筹资费用，结果比一般模式更精确。")
    return result


# ---------------------------------------------------------------------------
# 普通股与留存收益资本成本
# ---------------------------------------------------------------------------
def equity_cost_dividend_growth(
    current_dividend: float,
    share_price: float,
    growth_rate: float,
    flotation_rate: float = 0.0,
) -> float:
    """普通股资本成本——股利增长模型：Ks = D1/[P0(1-f)] + g。"""
    d0 = require_nonnegative(current_dividend, "当前每股股利 D0")
    price = require_positive(share_price, "每股市价 P0")
    g = require_rate(growth_rate, "股利增长率 g", allow_negative=True)
    fee = require_rate(flotation_rate, "筹资费率 f", max_value=0.999)
    d1 = d0 * (1.0 + g)
    return d1 / (price * (1.0 - fee)) + g


def equity_cost_growth_result(
    current_dividend: float,
    share_price: float,
    growth_rate: float,
    flotation_rate: float = 0.0,
) -> CalcResult:
    """构建普通股股利增长模型结果。"""
    d0 = require_nonnegative(current_dividend, "当前每股股利 D0")
    price = require_positive(share_price, "每股市价 P0")
    g = require_rate(growth_rate, "股利增长率 g", allow_negative=True)
    fee = require_rate(flotation_rate, "筹资费率 f", max_value=0.999)
    d1 = d0 * (1.0 + g)
    cost = equity_cost_dividend_growth(d0, price, g, fee)
    net_price = price * (1.0 - fee)
    result = CalcResult(
        MODULE,
        "普通股资本成本——股利增长模型",
        {
            "当前每股股利 D0": f"{money(d0, 4)} 元",
            "每股市价 P0": f"{money(price, 2)} 元",
            "股利增长率 g": percent(g),
            "筹资费率 f": percent(fee),
        },
    )
    result.add_step("股利增长模型：Ks = D1 / [P0 × (1-f)] + g，其中 D1 = D0 × (1+g)。")
    result.add_step(f"D1 = {money(d0, 4)} × (1+{percent(g)}) = {money(d1, 4)} 元。")
    result.add_step(
        f"筹资净额 = P0 × (1-f) = {money(price, 2)} × (1-{percent(fee)}) = {money(net_price, 2)} 元。"
    )
    result.add_step(
        f"Ks = {money(d1, 4)} ÷ {money(net_price, 2)} + {percent(g)} = {percent(cost, 4)}。"
    )
    result.put("预计每股股利 D1", f"{money(d1, 4)} 元")
    result.put("普通股资本成本 Ks", percent(cost, 4))
    result.add_note("留存收益没有筹资费用；普通股若考虑发行费用，分母应使用筹资净额。")
    return result


def retained_earnings_cost(
    current_dividend: float, share_price: float, growth_rate: float
) -> float:
    """留存收益资本成本：Ks = D1/P0 + g（无筹资费率）。"""
    return equity_cost_dividend_growth(current_dividend, share_price, growth_rate, 0.0)


def retained_earnings_result(
    current_dividend: float, share_price: float, growth_rate: float
) -> CalcResult:
    """构建留存收益资本成本结果。"""
    d0 = require_nonnegative(current_dividend, "当前每股股利 D0")
    price = require_positive(share_price, "每股市价 P0")
    g = require_rate(growth_rate, "股利增长率 g", allow_negative=True)
    d1 = d0 * (1.0 + g)
    cost = retained_earnings_cost(d0, price, g)
    result = CalcResult(
        MODULE,
        "留存收益资本成本",
        {
            "当前每股股利 D0": f"{money(d0, 4)} 元",
            "每股市价 P0": f"{money(price, 2)} 元",
            "股利增长率 g": percent(g),
        },
    )
    result.add_step("留存收益属于股东权益，其机会成本按普通股股利增长模型计算，但不扣筹资费用。")
    result.add_step(f"Ks = D1/P0 + g = {money(d1, 4)} / {money(price, 2)} + {percent(g)}。")
    result.add_step(f"Ks = {percent(cost, 4)}。")
    result.put("留存收益资本成本", percent(cost, 4))
    result.add_note("留存收益成本低于新发行普通股成本，因为不发生发行费用。")
    return result


# ---------------------------------------------------------------------------
# 加权平均资本成本
# ---------------------------------------------------------------------------
def wacc(weights: Sequence[float], costs: Sequence[float]) -> float:
    """WACC = Σ(Wj × Kj)，权重之和须为 1。"""
    if len(weights) != len(costs):
        raise ValueError("权重与资本成本数量必须一致。")
    weight_values = [require_rate(w, f"第{i + 1}项权重", max_value=1.0) for i, w in enumerate(weights)]
    if abs(sum(weight_values) - 1.0) > 1e-6:
        raise ValueError("各项资本权重之和必须等于 1。")
    cost_values = [require_rate(c, f"第{i + 1}项资本成本") for i, c in enumerate(costs)]
    return sum(weight * cost for weight, cost in zip(weight_values, cost_values))


def wacc_result(components: Sequence[Dict[str, object]]) -> CalcResult:
    """按金额权重计算 WACC。

    components: [{"name": "长期借款", "amount": 400, "cost": 0.05}, ...]
    """
    if not components:
        raise ValueError("至少需要一项资本来源。")
    names: List[str] = []
    amounts: List[float] = []
    costs: List[float] = []
    for raw in components:
        name = str(raw.get("name", "资本来源"))
        amount = require_positive(raw.get("amount"), f"{name}金额")
        cost = require_rate(raw.get("cost"), f"{name}资本成本")
        names.append(name)
        amounts.append(amount)
        costs.append(cost)
    total = sum(amounts)
    weights = [amount / total for amount in amounts]
    value = sum(weight * cost for weight, cost in zip(weights, costs))
    result = CalcResult(
        MODULE,
        "加权平均资本成本 WACC",
        {"资本总额": f"{money(total)} 元", "资本来源数量": len(components)},
    )
    result.add_step("WACC = Σ(第 j 种资本比重 × 第 j 种资本成本)。")
    result.add_step(
        "各资本来源比重："
        + "；".join(f"{name}={money(amount)}/{money(total)}={percent(weight)}"
                  for name, amount, weight in zip(names, amounts, weights))
        + "。"
    )
    result.add_step(
        "加权计算："
        + " + ".join(
            f"{percent(weight)}×{percent(cost)}" for weight, cost in zip(weights, costs)
        )
        + f" = {percent(value, 4)}。"
    )
    result.put("WACC", percent(value, 4))
    for name, weight, cost in zip(names, weights, costs):
        result.put(f"{name}比重", percent(weight, 2))
        result.put(f"{name}资本成本", percent(cost, 2))
    result.add_note("权重可采用账面价值、市场价值或目标资本结构；计算口径应保持一致。")
    return result


# ---------------------------------------------------------------------------
# 交互菜单与例题
# ---------------------------------------------------------------------------
def _interactive_capm() -> CalcResult:
    rf = ask_rate_percent("无风险收益率 Rf", 0.03)
    beta = ask_float("β系数", 1.2, min_value=0, allow_negative=False)
    rm = ask_rate_percent("市场组合收益率 Rm", 0.09)
    return capm_result(rf, beta, rm)


def _interactive_debt_general() -> CalcResult:
    interest = ask_float("年利息 I（元）", 80, min_value=0, allow_negative=False)
    amount = ask_float("债务筹资额 L（元）", 1000, min_value=0, allow_negative=False)
    tax = ask_rate_percent("所得税税率 T", 0.25, max_percent=100)
    fee = ask_rate_percent("筹资费率 f", 0.02, max_percent=100)
    return debt_cost_general_result(interest, amount, tax, fee)


def _interactive_debt_discount() -> CalcResult:
    face = ask_float("债券面值（元）", 1000, min_value=0, allow_negative=False)
    coupon = ask_rate_percent("票面利率", 0.08)
    years = ask_int("债券期限（年）", 5)
    price = ask_float("发行价格（元）", 1050, min_value=0, allow_negative=False)
    tax = ask_rate_percent("所得税税率", 0.25, max_percent=100)
    fee = ask_rate_percent("筹资费率", 0.02, max_percent=100)
    return debt_cost_discount_result(face, coupon, years, price, tax, fee)


def _interactive_equity_growth() -> CalcResult:
    d0 = ask_float("当前每股股利 D0（元）", 1.2, min_value=0, allow_negative=False)
    price = ask_float("每股市价 P0（元）", 20, min_value=0, allow_negative=False)
    growth = ask_rate_percent("股利增长率 g", 0.05, allow_negative=True)
    fee = ask_rate_percent("筹资费率 f", 0.03, max_percent=100)
    return equity_cost_growth_result(d0, price, growth, fee)


def _interactive_retained() -> CalcResult:
    d0 = ask_float("当前每股股利 D0（元）", 1.2, min_value=0, allow_negative=False)
    price = ask_float("每股市价 P0（元）", 20, min_value=0, allow_negative=False)
    growth = ask_rate_percent("股利增长率 g", 0.05, allow_negative=True)
    return retained_earnings_result(d0, price, growth)


def _interactive_wacc() -> CalcResult:
    count = ask_int("资本来源数量", 2, min_value=1, max_value=10)
    defaults = [
        ("长期借款", 400, 0.0612),
        ("普通股权益", 600, 0.1149),
        ("优先股", 200, 0.09),
    ]
    components: List[Dict[str, object]] = []
    for index in range(count):
        default_name, default_amount, default_cost = defaults[min(index, len(defaults) - 1)]
        print(f"\n第 {index + 1} 项资本：")
        name = ask_text("名称", default_name)
        amount = ask_float("金额（元）", default_amount, min_value=0, allow_negative=False)
        cost = ask_rate_percent("资本成本", default_cost)
        components.append({"name": name, "amount": amount, "cost": cost})
    return wacc_result(components)


def _run_demo() -> None:
    """一键演示资本成本全套公式。"""
    print_heading("资本成本：全套例题一键演示", "★")
    results = [
        capm_result(0.03, 1.2, 0.09),
        debt_cost_general_result(80, 1000, 0.25, 0.02),
        debt_cost_discount_result(1000, 0.08, 5, 1050, 0.25, 0.02),
        equity_cost_growth_result(1.2, 20, 0.05, 0.03),
        retained_earnings_result(1.2, 20, 0.05),
    ]
    for result in results:
        show_result(result)
    demo_wacc = wacc_result(
        [
            {"name": "长期借款", "amount": 400, "cost": debt_cost_general(80, 1000, 0.25, 0.02)},
            {"name": "普通股权益", "amount": 600, "cost": equity_cost_dividend_growth(1.2, 20, 0.05, 0.03)},
        ]
    )
    show_result(demo_wacc)
    print("\n[演示完成] 已覆盖 CAPM、债务一般/贴现模式、股票、留存收益与 WACC。")


def run() -> None:
    """模块 3 控制台菜单。"""
    while True:
        print_heading("模块3 资本成本（CAPM/债务/股票/留存收益/WACC）")
        print("  1. CAPM 必要收益率")
        print("  2. 债务资本成本——一般模式")
        print("  3. 债务资本成本——贴现模式")
        print("  4. 普通股资本成本——股利增长模型")
        print("  5. 普通股资本成本——CAPM（与选项1同源）")
        print("  6. 留存收益资本成本")
        print("  7. 加权平均资本成本 WACC")
        print("  8. 全套例题一键演示")
        print("  0. 返回主菜单")
        try:
            choice = input("请选择功能：").strip()
        except EOFError:
            return
        if choice == "0":
            return
        actions = {
            "1": _interactive_capm,
            "2": _interactive_debt_general,
            "3": _interactive_debt_discount,
            "4": _interactive_equity_growth,
            "5": _interactive_capm,
            "6": _interactive_retained,
            "7": _interactive_wacc,
        }
        if choice == "8":
            _run_demo()
            pause()
        elif choice in actions:
            run_calculation(actions[choice])
            pause()
        else:
            print("[提示] 无效选项，请输入 0~8。")
