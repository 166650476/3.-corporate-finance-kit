"""模块 6：营运资金管理。

覆盖现金管理（存货模型、Miller-Orr 随机模型）、应收账款管理
（机会成本、信用政策决策）和存货管理（EOQ、陆续供货、保险储备）。
"""

from __future__ import annotations

import math
from typing import Dict, Sequence

import pandas as pd

from utils import (
    CalcResult,
    ask_float,
    ask_int,
    ask_rate_percent,
    ask_yes_no,
    money,
    pause,
    percent,
    print_heading,
    require_nonnegative,
    require_positive,
    require_rate,
    run_calculation,
    show_result,
    safe_divide,
)


MODULE = "模块6 营运资金管理"


# ---------------------------------------------------------------------------
# 现金管理
# ---------------------------------------------------------------------------
def baumol_cash_model(
    annual_cash_demand: float, transaction_cost: float, opportunity_rate: float
) -> tuple[float, float, float, float]:
    """存货模型（Baumol）：返回（最佳现金持有量，最低总成本，交易成本，机会成本）。"""
    demand = require_positive(annual_cash_demand, "全年现金需求 T")
    cost_per_conversion = require_positive(transaction_cost, "每次转换成本 F")
    rate = require_rate(opportunity_rate, "有价证券收益率 K")
    if rate <= 0:
        raise ValueError("机会成本率必须大于 0，否则最佳现金持有量无有限解。")
    optimal = math.sqrt(2.0 * demand * cost_per_conversion / rate)
    transaction_total = demand / optimal * cost_per_conversion
    opportunity_total = optimal / 2.0 * rate
    return optimal, transaction_total + opportunity_total, transaction_total, opportunity_total


def baumol_result(
    annual_cash_demand: float, transaction_cost: float, opportunity_rate: float
) -> CalcResult:
    """构建最佳现金持有量存货模型结果。"""
    demand = require_positive(annual_cash_demand, "全年现金需求 T")
    cost = require_positive(transaction_cost, "每次转换成本 F")
    rate = require_rate(opportunity_rate, "有价证券收益率 K")
    optimal, total, transaction_total, opportunity_total = baumol_cash_model(demand, cost, rate)
    orders = demand / optimal
    cycle_days = 360.0 / orders
    result = CalcResult(
        MODULE,
        "现金管理——存货模型",
        {
            "全年现金需求 T": f"{money(demand)} 元",
            "每次转换成本 F": f"{money(cost)} 元",
            "有价证券收益率 K": percent(rate),
        },
    )
    result.add_step("存货模型假设现金均匀消耗，最佳现金持有量 C* = √(2×T×F/K)。")
    result.add_step(
        f"C* = √(2 × {money(demand)} × {money(cost)} ÷ {percent(rate)}) = {money(optimal)} 元。"
    )
    result.add_step(
        f"最佳转换次数 = T/C* = {money(demand)} ÷ {money(optimal)} = {orders:.2f} 次，"
        f"约每 {cycle_days:.2f} 天转换一次。"
    )
    result.add_step(
        f"交易成本 = T/C*×F = {money(transaction_total)} 元；"
        f"机会成本 = C*/2×K = {money(opportunity_total)} 元。"
    )
    result.add_step(f"相关总成本 = 交易成本 + 机会成本 = {money(total)} 元。")
    result.put("最佳现金持有量 C*", f"{money(optimal)} 元")
    result.put("最低相关总成本", f"{money(total)} 元")
    result.put("其中：交易成本", f"{money(transaction_total)} 元")
    result.put("其中：机会成本", f"{money(opportunity_total)} 元")
    result.put("最佳转换次数", f"{orders:.2f} 次")
    result.put("转换周期", f"{cycle_days:.2f} 天")
    result.add_note("在最佳点，交易成本与机会成本相等；这是存货模型的重要性质。")
    return result


def miller_orr_model(
    transaction_cost: float,
    daily_std_dev: float,
    daily_opportunity_rate: float,
    lower_limit: float,
) -> tuple[float, float, float]:
    """Miller-Orr 随机模型：返回（回归线 R，上限 H，现金返回幅度）。"""
    cost = require_positive(transaction_cost, "每次转换成本 F")
    sigma = require_positive(daily_std_dev, "每日现金流量标准差 σ")
    rate = require_rate(daily_opportunity_rate, "日机会成本率 i")
    lower = require_nonnegative(lower_limit, "最低控制线 L")
    if rate <= 0:
        raise ValueError("日机会成本率必须大于 0。")
    spread_component = (3.0 * cost * sigma ** 2 / (4.0 * rate)) ** (1.0 / 3.0)
    return_point = lower + spread_component
    upper_limit = 3.0 * return_point - 2.0 * lower
    return return_point, upper_limit, upper_limit - lower


def miller_orr_result(
    transaction_cost: float,
    daily_std_dev: float,
    daily_opportunity_rate: float,
    lower_limit: float,
) -> CalcResult:
    """构建 Miller-Orr 随机模型结果。"""
    cost = require_positive(transaction_cost, "每次转换成本 F")
    sigma = require_positive(daily_std_dev, "每日现金流量标准差 σ")
    rate = require_rate(daily_opportunity_rate, "日机会成本率 i")
    lower = require_nonnegative(lower_limit, "最低控制线 L")
    return_point, upper, spread = miller_orr_model(cost, sigma, rate, lower)
    result = CalcResult(
        MODULE,
        "现金管理——Miller-Orr 随机模型",
        {
            "每次转换成本 F": f"{money(cost)} 元",
            "每日现金流标准差 σ": f"{money(sigma)} 元",
            "日机会成本率 i": percent(rate, 4),
            "最低控制线 L": f"{money(lower)} 元",
        },
    )
    result.add_step(
        "随机模型回归线 R = L + [3Fσ^2/(4i)]^(1/3)，最高控制线 H = 3R - 2L。"
    )
    result.add_step(
        f"回归线增量 = [3×{money(cost)}×{money(sigma)}^2÷(4×{percent(rate, 4)})]^(1/3) "
        f"= {money(spread)} 元。"
    )
    result.add_step(f"R = {money(lower)} + {money(spread)} = {money(return_point)} 元。")
    result.add_step(f"H = 3×{money(return_point)} - 2×{money(lower)} = {money(upper)} 元。")
    result.add_step(
        "控制规则：现金余额触及上限 H 时，用超额现金购买有价证券，使余额回到 R；"
        "触及下限 L 时，出售有价证券补足现金至 R；在 L 与 H 之间不操作。"
    )
    result.put("回归线 R", f"{money(return_point)} 元")
    result.put("最高控制线 H", f"{money(upper)} 元")
    result.put("最低控制线 L", f"{money(lower)} 元")
    result.put("操作区间宽度 H-L", f"{money(spread)} 元")
    result.add_note("随机模型适用于现金流量不确定且波动较大的企业；现金余额在控制区间内不进行调整。")
    return result


# ---------------------------------------------------------------------------
# 应收账款管理
# ---------------------------------------------------------------------------
def ar_opportunity_cost(
    annual_sales: float,
    average_collection_days: float,
    variable_cost_ratio: float,
    opportunity_rate: float,
    *,
    days_per_year: int = 360,
) -> tuple[float, float]:
    """应收账款机会成本，返回（平均应收账款，机会成本）。"""
    sales = require_positive(annual_sales, "年销售额")
    dso = require_nonnegative(average_collection_days, "平均收现期")
    variable_ratio = require_rate(variable_cost_ratio, "变动成本率", max_value=1.0)
    rate = require_rate(opportunity_rate, "资金机会成本率")
    average_ar = sales / days_per_year * dso
    return average_ar, average_ar * variable_ratio * rate


def ar_opportunity_result(
    annual_sales: float,
    average_collection_days: float,
    variable_cost_ratio: float,
    opportunity_rate: float,
) -> CalcResult:
    """构建应收账款机会成本结果。"""
    sales = require_positive(annual_sales, "年销售额")
    dso = require_nonnegative(average_collection_days, "平均收现期")
    variable_ratio = require_rate(variable_cost_ratio, "变动成本率", max_value=1.0)
    rate = require_rate(opportunity_rate, "资金机会成本率")
    average_ar, cost = ar_opportunity_cost(sales, dso, variable_ratio, rate)
    result = CalcResult(
        MODULE,
        "应收账款机会成本",
        {
            "年销售额": f"{money(sales)} 元",
            "平均收现期": f"{dso:.1f} 天",
            "变动成本率": percent(variable_ratio),
            "资金机会成本率": percent(rate),
        },
    )
    result.add_step("平均应收账款 = 年销售额 ÷ 360 × 平均收现期。")
    result.add_step(
        f"平均应收账款 = {money(sales)} ÷ 360 × {dso:.1f} = {money(average_ar)} 元。"
    )
    result.add_step("应收账款机会成本 = 平均应收账款 × 变动成本率 × 资金机会成本率。")
    result.add_step(
        f"机会成本 = {money(average_ar)} × {percent(variable_ratio)} × {percent(rate)} "
        f"= {money(cost)} 元。"
    )
    result.put("平均应收账款", f"{money(average_ar)} 元")
    result.put("应收账款机会成本", f"{money(cost)} 元")
    result.add_note("若题目直接给出“应收账款平均余额”，可直接用余额×变动成本率×机会成本率。")
    return result


def _credit_metrics(policy: Dict[str, object], days_per_year: int = 360) -> Dict[str, float]:
    """计算一个信用政策方案的相关收益指标。"""
    sales = require_positive(policy.get("sales"), "年销售额")
    dso = require_nonnegative(policy.get("dso"), "平均收现期")
    bad_debt_rate = require_rate(policy.get("bad_debt_rate", 0), "坏账损失率", max_value=1.0)
    collection_cost = require_nonnegative(policy.get("collection_cost", 0), "收账费用")
    variable_ratio = require_rate(policy.get("variable_cost_ratio"), "变动成本率", max_value=1.0)
    opportunity_rate = require_rate(policy.get("opportunity_rate"), "资金机会成本率")
    discount_rate = require_rate(policy.get("discount_rate", 0), "现金折扣率", max_value=1.0)
    discount_proportion = require_rate(
        policy.get("discount_proportion", 0), "享受现金折扣比例", max_value=1.0
    )
    average_ar = sales / days_per_year * dso
    contribution = sales * (1.0 - variable_ratio)
    opportunity_cost = average_ar * variable_ratio * opportunity_rate
    bad_debt_loss = sales * bad_debt_rate
    discount_cost = sales * discount_proportion * discount_rate
    net_benefit = contribution - opportunity_cost - bad_debt_loss - collection_cost - discount_cost
    return {
        "sales": sales,
        "dso": dso,
        "average_ar": average_ar,
        "contribution": contribution,
        "opportunity_cost": opportunity_cost,
        "bad_debt_loss": bad_debt_loss,
        "collection_cost": collection_cost,
        "discount_cost": discount_cost,
        "net_benefit": net_benefit,
    }


def credit_policy_result(
    current_policy: Dict[str, object], proposed_policy: Dict[str, object]
) -> CalcResult:
    """信用政策决策：比较现行政策与拟议政策的增量相关收益。"""
    current = _credit_metrics(current_policy)
    proposed = _credit_metrics(proposed_policy)
    incremental = proposed["net_benefit"] - current["net_benefit"]
    accept = incremental > 0
    result = CalcResult(
        MODULE,
        "信用政策决策",
        {
            "现行政策销售额": f"{money(current['sales'])} 元",
            "拟议政策销售额": f"{money(proposed['sales'])} 元",
        },
    )
    result.add_step(
        "相关收益 = 边际贡献 - 应收账款机会成本 - 坏账损失 - 收账费用 - 现金折扣成本。"
    )
    result.add_step(
        "边际贡献 = 销售额 × (1-变动成本率)；"
        "机会成本 = 年销售额/360×平均收现期×变动成本率×机会成本率。"
    )
    result.add_step(
        f"现行政策相关收益 = {money(current['net_benefit'])} 元；"
        f"拟议政策相关收益 = {money(proposed['net_benefit'])} 元。"
    )
    result.add_step(
        f"增量相关收益 = {money(proposed['net_benefit'])} - {money(current['net_benefit'])} "
        f"= {money(incremental)} 元。"
    )
    result.add_step(
        "增量相关收益大于 0，应采纳拟议信用政策。"
        if accept
        else "增量相关收益不大于 0，应维持现行信用政策。"
    )
    table = pd.DataFrame(
        [
            {"项目": "年销售额", "现行政策": round(current["sales"], 2),
             "拟议政策": round(proposed["sales"], 2),
             "差异": round(proposed["sales"] - current["sales"], 2)},
            {"项目": "边际贡献", "现行政策": round(current["contribution"], 2),
             "拟议政策": round(proposed["contribution"], 2),
             "差异": round(proposed["contribution"] - current["contribution"], 2)},
            {"项目": "机会成本", "现行政策": round(current["opportunity_cost"], 2),
             "拟议政策": round(proposed["opportunity_cost"], 2),
             "差异": round(proposed["opportunity_cost"] - current["opportunity_cost"], 2)},
            {"项目": "坏账损失", "现行政策": round(current["bad_debt_loss"], 2),
             "拟议政策": round(proposed["bad_debt_loss"], 2),
             "差异": round(proposed["bad_debt_loss"] - current["bad_debt_loss"], 2)},
            {"项目": "收账费用", "现行政策": round(current["collection_cost"], 2),
             "拟议政策": round(proposed["collection_cost"], 2),
             "差异": round(proposed["collection_cost"] - current["collection_cost"], 2)},
            {"项目": "现金折扣成本", "现行政策": round(current["discount_cost"], 2),
             "拟议政策": round(proposed["discount_cost"], 2),
             "差异": round(proposed["discount_cost"] - current["discount_cost"], 2)},
            {"项目": "相关收益", "现行政策": round(current["net_benefit"], 2),
             "拟议政策": round(proposed["net_benefit"], 2),
             "差异": round(incremental, 2)},
        ]
    )
    result.add_table("信用政策相关收益比较表（元）", table)
    result.put("现行政策相关收益", f"{money(current['net_benefit'])} 元")
    result.put("拟议政策相关收益", f"{money(proposed['net_benefit'])} 元")
    result.put("增量相关收益", f"{money(incremental)} 元")
    result.put("决策建议", "采纳拟议信用政策" if accept else "维持现行信用政策")
    result.add_note("信用政策决策属于增量分析，只考虑因政策变化而改变的收入和成本。")
    return result


# ---------------------------------------------------------------------------
# 存货管理
# ---------------------------------------------------------------------------
def eoq_basic(
    annual_demand: float, order_cost: float, holding_cost_per_unit: float
) -> tuple[float, float, int]:
    """经济订货批量 EOQ，返回（Q*，最低相关总成本，每年订货次数）。"""
    demand = require_positive(annual_demand, "全年需求量 D")
    cost = require_positive(order_cost, "每次订货成本 K")
    holding = require_positive(holding_cost_per_unit, "单位年储存成本 Kc")
    optimal = math.sqrt(2.0 * demand * cost / holding)
    total = demand / optimal * cost + optimal / 2.0 * holding
    orders = int(math.ceil(demand / optimal))
    return optimal, total, orders


def eoq_result(
    annual_demand: float, order_cost: float, holding_cost_per_unit: float
) -> CalcResult:
    """构建 EOQ 结果。"""
    demand = require_positive(annual_demand, "全年需求量 D")
    cost = require_positive(order_cost, "每次订货成本 K")
    holding = require_positive(holding_cost_per_unit, "单位年储存成本 Kc")
    optimal, total, orders = eoq_basic(demand, cost, holding)
    order_total = demand / optimal * cost
    holding_total = optimal / 2.0 * holding
    result = CalcResult(
        MODULE,
        "存货管理——经济订货批量 EOQ",
        {
            "全年需求量 D": f"{demand:,.0f} 件",
            "每次订货成本 K": f"{money(cost)} 元",
            "单位年储存成本 Kc": f"{money(holding)} 元",
        },
    )
    result.add_step("经济订货批量公式：Q* = √(2×D×K/Kc)。")
    result.add_step(
        f"Q* = √(2×{demand:,.0f}×{money(cost)}÷{money(holding)}) = {optimal:,.2f} 件。"
    )
    result.add_step(
        f"最低相关总成本 = D/Q*×K + Q*/2×Kc = {money(order_total)} + {money(holding_total)} "
        f"= {money(total)} 元。"
    )
    result.add_step(f"每年最佳订货次数约为 {orders} 次。")
    result.put("经济订货批量 Q*", f"{optimal:,.2f} 件")
    result.put("最低相关总成本", f"{money(total)} 元")
    result.put("其中：年订货成本", f"{money(order_total)} 元")
    result.put("其中：年储存成本", f"{money(holding_total)} 元")
    result.put("每年订货次数", f"{orders} 次")
    cycle = 360.0 / (demand / optimal)
    result.put("订货周期", f"{cycle:.2f} 天")
    result.add_note("在 EOQ 点，年订货成本与年储存成本相等；该模型假设需求均匀、瞬时到货、无缺货。")
    return result


def eoq_gradual(
    annual_demand: float,
    order_cost: float,
    holding_cost_per_unit: float,
    daily_supply: float,
    daily_demand: float,
) -> tuple[float, float]:
    """陆续供货模型 EOQ，返回（Q*，最低相关总成本）。"""
    demand = require_positive(annual_demand, "全年需求量 D")
    cost = require_positive(order_cost, "每次订货成本 K")
    holding = require_positive(holding_cost_per_unit, "单位年储存成本 Kc")
    supply = require_positive(daily_supply, "每日供货量 p")
    daily = require_positive(daily_demand, "每日耗用量 d")
    if supply <= daily:
        raise ValueError("每日供货量 p 必须大于每日耗用量 d。")
    optimal = math.sqrt(2.0 * demand * cost / holding * supply / (supply - daily))
    average_inventory = optimal / 2.0 * (1.0 - daily / supply)
    total = demand / optimal * cost + average_inventory * holding
    return optimal, total


def eoq_gradual_result(
    annual_demand: float,
    order_cost: float,
    holding_cost_per_unit: float,
    daily_supply: float,
    daily_demand: float,
) -> CalcResult:
    """构建陆续供货模型结果。"""
    demand = require_positive(annual_demand, "全年需求量 D")
    cost = require_positive(order_cost, "每次订货成本 K")
    holding = require_positive(holding_cost_per_unit, "单位年储存成本 Kc")
    supply = require_positive(daily_supply, "每日供货量 p")
    daily = require_positive(daily_demand, "每日耗用量 d")
    optimal, total = eoq_gradual(demand, cost, holding, supply, daily)
    average_inventory = optimal / 2.0 * (1.0 - daily / supply)
    order_total = demand / optimal * cost
    holding_total = average_inventory * holding
    result = CalcResult(
        MODULE,
        "存货管理——陆续供货模型",
        {
            "全年需求量 D": f"{demand:,.0f} 件",
            "每次订货成本 K": f"{money(cost)} 元",
            "单位年储存成本 Kc": f"{money(holding)} 元",
            "每日供货量 p": f"{supply:,.2f} 件/天",
            "每日耗用量 d": f"{daily:,.2f} 件/天",
        },
    )
    result.add_step("陆续供货时，平均存货 = Q/2 × (1-d/p)，而不是 Q/2。")
    result.add_step("经济订货批量：Q* = √[2DK/Kc × p/(p-d)]。")
    result.add_step(
        f"Q* = √[2×{demand:,.0f}×{money(cost)}÷{money(holding)}×"
        f"{supply:,.2f}/({supply:,.2f}-{daily:,.2f})] = {optimal:,.2f} 件。"
    )
    result.add_step(
        f"平均存货 = {optimal:,.2f}/2 × (1-{daily:,.2f}/{supply:,.2f}) "
        f"= {average_inventory:,.2f} 件。"
    )
    result.add_step(
        f"相关总成本 = 订货成本 {money(order_total)} + 储存成本 {money(holding_total)} "
        f"= {money(total)} 元。"
    )
    result.put("陆续供货经济批量 Q*", f"{optimal:,.2f} 件")
    result.put("平均存货量", f"{average_inventory:,.2f} 件")
    result.put("最低相关总成本", f"{money(total)} 元")
    result.put("其中：年订货成本", f"{money(order_total)} 元")
    result.put("其中：年储存成本", f"{money(holding_total)} 元")
    result.add_note("陆续供货模型适用于边生产边耗用或分批到货的情形。")
    return result


def safety_stock(
    safety_factor: float, demand_std_dev: float, lead_time_days: float
) -> float:
    """保险储备 = 安全系数 z × 日需求标准差 σd × √提前期。"""
    z = require_nonnegative(safety_factor, "安全系数 z")
    sigma = require_nonnegative(demand_std_dev, "日需求量标准差 σd")
    lead = require_nonnegative(lead_time_days, "提前期 L")
    return z * sigma * math.sqrt(lead)


def safety_stock_result(
    safety_factor: float,
    demand_std_dev: float,
    lead_time_days: float,
    average_daily_demand: float,
) -> CalcResult:
    """构建保险储备与再订货点结果。"""
    z = require_nonnegative(safety_factor, "安全系数 z")
    sigma = require_nonnegative(demand_std_dev, "日需求量标准差 σd")
    lead = require_nonnegative(lead_time_days, "提前期 L")
    daily = require_positive(average_daily_demand, "平均日需求量 d")
    stock = safety_stock(z, sigma, lead)
    reorder_point = daily * lead + stock
    normal_lead_demand = daily * lead
    result = CalcResult(
        MODULE,
        "存货管理——保险储备与再订货点",
        {
            "安全系数 z": f"{z:.4f}",
            "日需求标准差 σd": f"{sigma:,.2f} 件",
            "提前期 L": f"{lead:.2f} 天",
            "平均日需求 d": f"{daily:,.2f} 件/天",
        },
    )
    result.add_step("保险储备 B = z × σd × √L，其中 z 由目标服务水平决定。")
    result.add_step(f"B = {z:.4f} × {sigma:,.2f} × √{lead:.2f} = {stock:,.2f} 件。")
    result.add_step(
        f"正常提前期需求 = d×L = {daily:,.2f}×{lead:.2f} = {normal_lead_demand:,.2f} 件。"
    )
    result.add_step(
        f"再订货点 = 正常提前期需求 + 保险储备 = {normal_lead_demand:,.2f}+{stock:,.2f} "
        f"= {reorder_point:,.2f} 件。"
    )
    result.put("保险储备 B", f"{stock:,.2f} 件")
    result.put("正常提前期需求", f"{normal_lead_demand:,.2f} 件")
    result.put("再订货点 ROP", f"{reorder_point:,.2f} 件")
    result.add_note("z=1.65 约对应 95% 单侧服务水平，z=2.33 约对应 99%；可按课程给定值替换。")
    return result


# ---------------------------------------------------------------------------
# 交互菜单与例题
# ---------------------------------------------------------------------------
def _input_credit_policy(
    label: str,
    defaults: Dict[str, float],
    opportunity_rate: float,
) -> Dict[str, object]:
    """录入一个信用政策方案。"""
    print(f"\n{label}：")
    return {
        "sales": ask_float("  年销售额（元）", defaults["sales"], min_value=0, allow_negative=False),
        "dso": ask_float("  平均收现期（天）", defaults["dso"], min_value=0, allow_negative=False),
        "bad_debt_rate": ask_rate_percent("  坏账损失率", defaults["bad_debt_rate"], max_percent=100),
        "collection_cost": ask_float(
            "  年收账费用（元）", defaults["collection_cost"], min_value=0, allow_negative=False
        ),
        "variable_cost_ratio": ask_rate_percent(
            "  变动成本率", defaults["variable_cost_ratio"], max_percent=100
        ),
        "opportunity_rate": opportunity_rate,
        "discount_rate": ask_rate_percent(
            "  现金折扣率（无则0）", defaults["discount_rate"], max_percent=100
        ),
        "discount_proportion": ask_rate_percent(
            "  享受折扣的销售比例", defaults["discount_proportion"], max_percent=100
        ),
    }


def _credit_policy_interactive() -> CalcResult:
    opportunity = ask_rate_percent("资金机会成本率（两方案共用）", 0.10)
    current = _input_credit_policy(
        "现行信用政策",
        {
            "sales": 10000000,
            "dso": 30,
            "bad_debt_rate": 0.01,
            "collection_cost": 50000,
            "variable_cost_ratio": 0.60,
            "discount_rate": 0.0,
            "discount_proportion": 0.0,
        },
        opportunity,
    )
    proposed = _input_credit_policy(
        "拟议信用政策",
        {
            "sales": 12000000,
            "dso": 45,
            "bad_debt_rate": 0.02,
            "collection_cost": 80000,
            "variable_cost_ratio": 0.60,
            "discount_rate": 0.02,
            "discount_proportion": 0.50,
        },
        opportunity,
    )
    return credit_policy_result(current, proposed)


def _run_demo() -> None:
    """一键演示营运资金管理全部公式。"""
    print_heading("营运资金管理：全套例题一键演示", "★")
    show_result(baumol_result(3600000, 1000, 0.08))
    show_result(miller_orr_result(1000, 2000, 0.0002, 10000))
    show_result(ar_opportunity_result(12000000, 45, 0.60, 0.10))
    show_result(
        credit_policy_result(
            {
                "sales": 10000000,
                "dso": 30,
                "bad_debt_rate": 0.01,
                "collection_cost": 50000,
                "variable_cost_ratio": 0.60,
                "opportunity_rate": 0.10,
                "discount_rate": 0.0,
                "discount_proportion": 0.0,
            },
            {
                "sales": 12000000,
                "dso": 45,
                "bad_debt_rate": 0.02,
                "collection_cost": 80000,
                "variable_cost_ratio": 0.60,
                "opportunity_rate": 0.10,
                "discount_rate": 0.02,
                "discount_proportion": 0.50,
            },
        )
    )
    show_result(eoq_result(36000, 500, 10))
    show_result(eoq_gradual_result(36000, 500, 10, 200, 100))
    show_result(safety_stock_result(1.65, 100, 4, 1000))
    print("\n[演示完成] 已覆盖现金、应收账款和存货管理全部模型。")


def run() -> None:
    """模块 6 控制台菜单。"""
    while True:
        print_heading("模块6 营运资金管理（现金 / 应收账款 / 存货）")
        print("  1. 现金管理——存货模型（Baumol）")
        print("  2. 现金管理——随机模型（Miller-Orr）")
        print("  3. 应收账款机会成本")
        print("  4. 信用政策决策")
        print("  5. 存货管理——经济订货批量 EOQ")
        print("  6. 存货管理——陆续供货模型")
        print("  7. 存货管理——保险储备与再订货点")
        print("  8. 全套例题一键演示")
        print("  0. 返回主菜单")
        try:
            choice = input("请选择功能：").strip()
        except EOFError:
            return
        if choice == "0":
            return
        if choice == "1":
            run_calculation(
                lambda: baumol_result(
                    ask_float("全年现金需求（元）", 3600000, min_value=0, allow_negative=False),
                    ask_float("每次转换成本（元）", 1000, min_value=0, allow_negative=False),
                    ask_rate_percent("有价证券年收益率", 0.08),
                )
            )
            pause()
        elif choice == "2":
            run_calculation(
                lambda: miller_orr_result(
                    ask_float("每次转换成本（元）", 1000, min_value=0, allow_negative=False),
                    ask_float("每日现金流量标准差（元）", 2000, min_value=0, allow_negative=False),
                    ask_rate_percent("日机会成本率", 0.0002, max_percent=10),
                    ask_float("最低控制线（元）", 10000, min_value=0, allow_negative=False),
                )
            )
            pause()
        elif choice == "3":
            run_calculation(
                lambda: ar_opportunity_result(
                    ask_float("年销售额（元）", 12000000, min_value=0, allow_negative=False),
                    ask_float("平均收现期（天）", 45, min_value=0, allow_negative=False),
                    ask_rate_percent("变动成本率", 0.60, max_percent=100),
                    ask_rate_percent("资金机会成本率", 0.10),
                )
            )
            pause()
        elif choice == "4":
            run_calculation(_credit_policy_interactive)
            pause()
        elif choice == "5":
            run_calculation(
                lambda: eoq_result(
                    ask_float("全年需求量（件）", 36000, min_value=0, allow_negative=False),
                    ask_float("每次订货成本（元）", 500, min_value=0, allow_negative=False),
                    ask_float("单位年储存成本（元）", 10, min_value=0, allow_negative=False),
                )
            )
            pause()
        elif choice == "6":
            run_calculation(
                lambda: eoq_gradual_result(
                    ask_float("全年需求量（件）", 36000, min_value=0, allow_negative=False),
                    ask_float("每次订货成本（元）", 500, min_value=0, allow_negative=False),
                    ask_float("单位年储存成本（元）", 10, min_value=0, allow_negative=False),
                    ask_float("每日供货量（件/天）", 200, min_value=0, allow_negative=False),
                    ask_float("每日耗用量（件/天）", 100, min_value=0, allow_negative=False),
                )
            )
            pause()
        elif choice == "7":
            run_calculation(
                lambda: safety_stock_result(
                    ask_float("安全系数 z", 1.65, min_value=0, allow_negative=False),
                    ask_float("日需求量标准差（件）", 100, min_value=0, allow_negative=False),
                    ask_float("提前期（天）", 4, min_value=0, allow_negative=False),
                    ask_float("平均日需求量（件/天）", 1000, min_value=0, allow_negative=False),
                )
            )
            pause()
        elif choice == "8":
            _run_demo()
            pause()
        else:
            print("[提示] 无效选项，请输入 0~8。")
