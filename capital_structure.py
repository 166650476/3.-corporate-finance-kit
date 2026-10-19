"""模块 5：资本结构。

覆盖每股收益无差别点法（EBIT-EPS 分析）和公司价值分析法。
"""

from __future__ import annotations

from typing import Dict, List, Sequence

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
    require_nonnegative,
    require_positive,
    require_rate,
    run_calculation,
    show_result,
)


MODULE = "模块5 资本结构"


def earnings_per_share(
    ebit: float,
    interest: float,
    preferred_dividend: float,
    shares: float,
    tax_rate: float,
) -> float:
    """每股收益 EPS = [(EBIT-I)(1-T)-Dp] / N。"""
    earnings = require_nonnegative(ebit, "息税前利润 EBIT")
    interest_value = require_nonnegative(interest, "利息费用")
    preferred = require_nonnegative(preferred_dividend, "优先股股利")
    share_count = require_positive(shares, "普通股股数")
    tax = require_rate(tax_rate, "所得税税率", max_value=1.0)
    return ((earnings - interest_value) * (1.0 - tax) - preferred) / share_count


def eps_indifference_point(
    plan_a: Dict[str, float], plan_b: Dict[str, float], tax_rate: float
) -> tuple[float, float]:
    """求解两个筹资方案的每股收益无差别点，返回（EBIT，EPS）。"""
    tax = require_rate(tax_rate, "所得税税率", max_value=0.999999)
    ia = require_nonnegative(plan_a.get("interest", 0), "方案A利息")
    ib = require_nonnegative(plan_b.get("interest", 0), "方案B利息")
    da = require_nonnegative(plan_a.get("preferred_dividend", 0), "方案A优先股股利")
    db = require_nonnegative(plan_b.get("preferred_dividend", 0), "方案B优先股股利")
    na = require_positive(plan_a.get("shares"), "方案A普通股股数")
    nb = require_positive(plan_b.get("shares"), "方案B普通股股数")
    if abs(na - nb) < 1e-12:
        raise ValidationError(
            "两个方案普通股股数相同，EPS 直线平行，不存在唯一无差别点。"
        )
    ebit = (
        nb * ia * (1.0 - tax)
        + nb * da
        - na * ib * (1.0 - tax)
        - na * db
    ) / ((nb - na) * (1.0 - tax))
    eps = earnings_per_share(ebit, ia, da, na, tax)
    return ebit, eps


def eps_indifference_result(
    plan_a: Dict[str, object],
    plan_b: Dict[str, object],
    tax_rate: float,
    expected_ebit: float,
) -> CalcResult:
    """构建每股收益无差别点分析结果。"""
    tax = require_rate(tax_rate, "所得税税率", max_value=0.999999)
    expected = require_nonnegative(expected_ebit, "预期息税前利润")
    data_a = {
        "interest": require_nonnegative(plan_a.get("interest", 0), "方案A利息"),
        "preferred_dividend": require_nonnegative(
            plan_a.get("preferred_dividend", 0), "方案A优先股股利"
        ),
        "shares": require_positive(plan_a.get("shares"), "方案A普通股股数"),
    }
    data_b = {
        "interest": require_nonnegative(plan_b.get("interest", 0), "方案B利息"),
        "preferred_dividend": require_nonnegative(
            plan_b.get("preferred_dividend", 0), "方案B优先股股利"
        ),
        "shares": require_positive(plan_b.get("shares"), "方案B普通股股数"),
    }
    name_a = str(plan_a.get("name", "方案A"))
    name_b = str(plan_b.get("name", "方案B"))
    point, point_eps = eps_indifference_point(data_a, data_b, tax)
    eps_a = earnings_per_share(
        expected, data_a["interest"], data_a["preferred_dividend"], data_a["shares"], tax
    )
    eps_b = earnings_per_share(
        expected, data_b["interest"], data_b["preferred_dividend"], data_b["shares"], tax
    )
    chosen = name_a if eps_a > eps_b else name_b
    if abs(eps_a - eps_b) < 1e-10:
        chosen = "两方案EPS相同"

    result = CalcResult(
        MODULE,
        "每股收益无差别点分析",
        {
            f"{name_a}利息": f"{money(data_a['interest'])} 元",
            f"{name_a}优先股股利": f"{money(data_a['preferred_dividend'])} 元",
            f"{name_a}普通股股数": f"{data_a['shares']:,.0f} 股",
            f"{name_b}利息": f"{money(data_b['interest'])} 元",
            f"{name_b}优先股股利": f"{money(data_b['preferred_dividend'])} 元",
            f"{name_b}普通股股数": f"{data_b['shares']:,.0f} 股",
            "所得税税率": percent(tax),
            "预期 EBIT": f"{money(expected)} 元",
        },
    )
    result.add_step(
        "两个方案的每股收益分别为：EPS_A=[(EBIT-I_A)(1-T)-Dp_A]/N_A，"
        "EPS_B=[(EBIT-I_B)(1-T)-Dp_B]/N_B。"
    )
    result.add_step("令 EPS_A = EPS_B，得到：")
    result.add_step(
        f"[(EBIT-{money(data_a['interest'])})×(1-{percent(tax)})-"
        f"{money(data_a['preferred_dividend'])}]/{data_a['shares']:,.0f} = "
        f"[(EBIT-{money(data_b['interest'])})×(1-{percent(tax)})-"
        f"{money(data_b['preferred_dividend'])}]/{data_b['shares']:,.0f}。"
    )
    result.add_step(
        f"解方程得每股收益无差别点 EBIT* = {money(point)} 元；"
        f"此时两方案 EPS 均为 {money(point_eps, 4)} 元/股。"
    )
    result.add_step(
        f"当预期 EBIT={money(expected)} 元时：{name_a} EPS={money(eps_a, 4)} 元/股，"
        f"{name_b} EPS={money(eps_b, 4)} 元/股。"
    )
    result.add_step(f"比较可知，在预期 EBIT 水平下应选择：{chosen}。")
    result.add_step(
        "决策规律：预期 EBIT 高于无差别点时，通常负债融资（股数较少）的 EPS 更高；"
        "低于无差别点时，权益融资更有利。"
    )
    result.put("每股收益无差别点 EBIT*", f"{money(point)} 元")
    result.put("无差别点 EPS", f"{money(point_eps, 4)} 元/股")
    result.put(f"{name_a} 预期 EPS", f"{money(eps_a, 4)} 元/股")
    result.put(f"{name_b} 预期 EPS", f"{money(eps_b, 4)} 元/股")
    result.put("推荐筹资方案", chosen)
    result.add_note("无差别点法只比较每股收益，不考虑风险变化；实际决策还应结合财务风险与公司价值。")
    return result


def company_value_analysis(
    ebit: float,
    tax_rate: float,
    structures: Sequence[Dict[str, object]],
) -> CalcResult:
    """公司价值分析法。

    每个方案包含 name、debt、debt_cost、equity_cost。
    S=(EBIT-I)(1-T)/Ks，V=S+B，WACC=Kd(1-T)B/V+KsS/V；
    选择公司价值 V 最大（通常也是 WACC 最低）的资本结构。
    """
    if not structures:
        raise ValidationError("至少需要一个资本结构方案。")
    import pandas as pd

    earnings = require_nonnegative(ebit, "息税前利润 EBIT")
    tax = require_rate(tax_rate, "所得税税率", max_value=0.999999)
    rows = []
    details: List[Dict[str, object]] = []
    for raw in structures:
        name = str(raw.get("name", "方案"))
        debt = require_nonnegative(raw.get("debt"), f"{name}债务价值")
        debt_cost = require_rate(raw.get("debt_cost"), f"{name}税前债务成本")
        equity_cost = require_positive(raw.get("equity_cost"), f"{name}股权资本成本")
        interest = debt * debt_cost
        equity_value = (earnings - interest) * (1.0 - tax) / equity_cost
        if equity_value < 0:
            raise ValidationError(
                f"{name}的 EBIT 小于利息，股权价值为负，不能直接套用公司价值模型。"
            )
        total_value = equity_value + debt
        if total_value <= 0:
            raise ValidationError(f"{name}的公司价值必须大于 0。")
        after_tax_debt = debt_cost * (1.0 - tax)
        wacc_value = (
            after_tax_debt * debt / total_value
            + equity_cost * equity_value / total_value
        )
        rows.append(
            {
                "方案": name,
                "债务价值 B": round(debt, 2),
                "股权价值 S": round(equity_value, 2),
                "公司价值 V=S+B": round(total_value, 2),
                "税前债务成本": f"{debt_cost * 100:.2f}%",
                "股权成本": f"{equity_cost * 100:.2f}%",
                "WACC": f"{wacc_value * 100:.2f}%",
            }
        )
        details.append(
            {
                "name": name,
                "debt": debt,
                "equity": equity_value,
                "value": total_value,
                "wacc": wacc_value,
                "interest": interest,
            }
        )

    best_value = max(details, key=lambda item: float(item["value"]))
    best_wacc = min(details, key=lambda item: float(item["wacc"]))
    result = CalcResult(
        MODULE,
        "资本结构决策——公司价值分析法",
        {"息税前利润 EBIT": f"{money(earnings)} 元", "所得税税率": percent(tax), "方案数": len(details)},
    )
    result.add_step("对每个资本结构方案，先按债务成本计算利息 I=B×Kd，再估计股权价值。")
    result.add_step("股权价值 S=(EBIT-I)(1-T)/Ks；公司价值 V=S+B。")
    result.add_step(
        "加权平均资本成本 WACC=Kd×(1-T)×B/V+Ks×S/V，其中 Kd 为税前债务成本。"
    )
    for item in details:
        result.add_step(
            f"{item['name']}：I={money(item['interest'])} 元，S={money(item['equity'])} 元，"
            f"V={money(item['value'])} 元，WACC={percent(item['wacc'], 4)}。"
        )
    result.add_step(
        f"比较公司价值：{best_value['name']} 的 V={money(best_value['value'])} 元为最大值；"
        f"最低 WACC 方案为 {best_wacc['name']}（{percent(best_wacc['wacc'], 4)}）。"
    )
    result.add_step(f"因此，按公司价值最大化标准，应选择：{best_value['name']}。")
    result.put("推荐资本结构", str(best_value["name"]))
    result.put("最大公司价值 V", f"{money(best_value['value'])} 元")
    result.put("该方案 WACC", percent(best_value["wacc"], 4))
    result.put("最低 WACC 方案", str(best_wacc["name"]))
    result.put("最低 WACC", percent(best_wacc["wacc"], 4))
    result.add_table("各资本结构方案公司价值与WACC比较表", pd.DataFrame(rows))
    if abs(float(best_value["wacc"]) - float(best_wacc["wacc"])) > 1e-10:
        result.add_note("公司价值最大方案与最低 WACC 方案不一致，应结合风险、控制权和融资约束综合判断。")
    result.add_note("公司价值分析法将资本结构变化通过股权成本和债务成本反映到公司价值，较 EPS 法更重视风险。")
    return result


# ---------------------------------------------------------------------------
# 交互菜单与例题
# ---------------------------------------------------------------------------
def _input_plan(default_name: str, default_interest: float, default_shares: float) -> Dict[str, object]:
    """录入一个筹资方案的 EPS 参数。"""
    name = ask_text("方案名称", default_name)
    interest = ask_float("年利息 I（元）", default_interest, min_value=0, allow_negative=False)
    preferred = ask_float("优先股股利 Dp（元，无则0）", 0, min_value=0, allow_negative=False)
    shares = ask_float("普通股股数 N（股）", default_shares, min_value=0, allow_negative=False)
    return {
        "name": name,
        "interest": interest,
        "preferred_dividend": preferred,
        "shares": shares,
    }


def _interactive_eps() -> CalcResult:
    print("方案A（如全部普通股融资）：")
    plan_a = _input_plan("方案A：增发普通股", 0, 1000000)
    print("\n方案B（如债务融资）：")
    plan_b = _input_plan("方案B：债务融资", 400000, 700000)
    tax = ask_rate_percent("所得税税率", 0.25, max_percent=100)
    expected = ask_float("预期息税前利润 EBIT（元）", 2000000, min_value=0, allow_negative=False)
    return eps_indifference_result(plan_a, plan_b, tax, expected)


def _interactive_company_value() -> CalcResult:
    ebit = ask_float("息税前利润 EBIT（元）", 2000000, min_value=0, allow_negative=False)
    tax = ask_rate_percent("所得税税率", 0.25, max_percent=100)
    count = ask_int("资本结构方案数量", 3, min_value=1, max_value=8)
    defaults = [(0.0, 0.06, 0.10), (5000000.0, 0.06, 0.11), (10000000.0, 0.07, 0.125)]
    structures: List[Dict[str, object]] = []
    for index in range(count):
        debt_default, debt_cost_default, equity_cost_default = defaults[min(index, 2)]
        print(f"\n第 {index + 1} 个资本结构方案：")
        name = ask_text("方案名称", f"结构{index + 1}")
        debt = ask_float("债务价值 B（元）", debt_default, min_value=0, allow_negative=False)
        debt_cost = ask_rate_percent("税前债务成本 Kd", debt_cost_default)
        equity_cost = ask_rate_percent("股权资本成本 Ks", equity_cost_default)
        structures.append(
            {
                "name": name,
                "debt": debt,
                "debt_cost": debt_cost,
                "equity_cost": equity_cost,
            }
        )
    return company_value_analysis(ebit, tax, structures)


def _run_demo() -> None:
    """一键演示资本结构两类决策。"""
    print_heading("资本结构：全套例题一键演示", "★")
    show_result(
        eps_indifference_result(
            {"name": "全部权益", "interest": 0, "preferred_dividend": 0, "shares": 1000000},
            {"name": "债务融资", "interest": 400000, "preferred_dividend": 0, "shares": 700000},
            0.25,
            2000000,
        )
    )
    show_result(
        company_value_analysis(
            2000000,
            0.25,
            [
                {"name": "无负债", "debt": 0, "debt_cost": 0.06, "equity_cost": 0.10},
                {"name": "负债500万", "debt": 5000000, "debt_cost": 0.06, "equity_cost": 0.11},
                {"name": "负债1000万", "debt": 10000000, "debt_cost": 0.07, "equity_cost": 0.125},
            ],
        )
    )
    print("\n[演示完成] 已演示 EBIT-EPS 无差别点与公司价值分析法。")


def run() -> None:
    """模块 5 控制台菜单。"""
    while True:
        print_heading("模块5 资本结构（EPS无差别点 / 公司价值分析）")
        print("  1. 每股收益无差别点 EBIT 与方案选择")
        print("  2. 公司价值分析法（V=S+B，WACC比较）")
        print("  3. 全套例题一键演示")
        print("  0. 返回主菜单")
        try:
            choice = input("请选择功能：").strip()
        except EOFError:
            return
        if choice == "0":
            return
        if choice == "1":
            run_calculation(_interactive_eps)
            pause()
        elif choice == "2":
            run_calculation(_interactive_company_value)
            pause()
        elif choice == "3":
            _run_demo()
            pause()
        else:
            print("[提示] 无效选项，请输入 0~3。")
