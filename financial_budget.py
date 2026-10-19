"""模块 12：财务预算。

按季度编制销售预算、生产预算、直接材料预算、直接人工预算、
制造费用预算、产品成本预算和现金预算，并支持全套联动生成。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import pandas as pd

from utils import (
    CalcResult,
    ValidationError,
    ask_float,
    ask_int,
    ask_rate_percent,
    ask_series,
    money,
    pause,
    percent,
    print_heading,
    require_nonnegative,
    require_positive,
    require_rate,
    require_same_length,
    run_calculation,
    show_result,
)


MODULE = "模块12 财务预算"


def _period_names(count: int) -> List[str]:
    """生成季度名称，超过 4 个季度时使用 P1~Pn。"""
    if count <= 4:
        return [f"Q{i + 1}" for i in range(count)]
    return [f"P{i + 1}" for i in range(count)]


def _validate_quarters(values: Sequence[float], name: str) -> List[float]:
    items = list(values)
    if not items:
        raise ValidationError(f"{name}不能为空。")
    return [require_nonnegative(value, f"{name}第{i + 1}期") for i, value in enumerate(items)]


def sales_schedule(volumes: Sequence[float], unit_price: float) -> pd.DataFrame:
    """销售预算：销售量×单价=销售收入。"""
    volume_values = _validate_quarters(volumes, "销售量")
    price = require_positive(unit_price, "单价")
    periods = _period_names(len(volume_values))
    revenues = [volume * price for volume in volume_values]
    table = pd.DataFrame(
        {
            "项目": ["预计销售量", "单价", "预计销售收入"],
            **{
                period: [round(volume, 2), round(price, 2), round(revenue, 2)]
                for period, volume, revenue in zip(periods, volume_values, revenues)
            },
            "全年": [round(sum(volume_values), 2), round(price, 2), round(sum(revenues), 2)],
        }
    )
    return table


def production_schedule(
    sales_volumes: Sequence[float],
    beginning_finished_goods: float,
    ending_inventory_ratio: float,
    ending_inventory_last: float,
) -> pd.DataFrame:
    """生产预算：生产量=销售量+期末产成品-期初产成品。"""
    sales_values = _validate_quarters(sales_volumes, "销售量")
    beginning = require_nonnegative(beginning_finished_goods, "期初产成品")
    ratio = require_rate(ending_inventory_ratio, "期末产成品占下期销售比例", max_value=1.0)
    last_ending = require_nonnegative(ending_inventory_last, "最后一期期末产成品")
    n = len(sales_values)
    ending = [sales_values[i + 1] * ratio if i < n - 1 else last_ending for i in range(n)]
    beginnings = [beginning] + ending[:-1]
    production = [
        sales + end - start for sales, end, start in zip(sales_values, ending, beginnings)
    ]
    if any(value < 0 for value in production):
        raise ValidationError("某期生产量为负数，请检查期初、期末存货假设。")
    periods = _period_names(n)
    return pd.DataFrame(
        {
            "项目": ["预计销售量", "加：期末产成品", "减：期初产成品", "预计生产量"],
            **{
                period: [round(sales, 2), round(end, 2), round(start, 2), round(prod, 2)]
                for period, sales, end, start, prod in zip(
                    periods, sales_values, ending, beginnings, production
                )
            },
            "全年": [
                round(sum(sales_values), 2),
                round(ending[-1], 2),
                round(beginning, 2),
                round(sum(production), 2),
            ],
        }
    )


def materials_schedule(
    production_volumes: Sequence[float],
    material_per_unit: float,
    material_unit_price: float,
    beginning_material: float,
    ending_material_ratio: float,
    ending_material_last: float,
) -> pd.DataFrame:
    """直接材料预算：采购量=生产耗用+期末材料-期初材料。"""
    production_values = _validate_quarters(production_volumes, "生产量")
    usage_per_unit = require_positive(material_per_unit, "单位产品材料用量")
    price = require_positive(material_unit_price, "材料单价")
    beginning = require_nonnegative(beginning_material, "期初材料")
    ratio = require_rate(ending_material_ratio, "期末材料占下期耗用比例", max_value=2.0)
    last_ending = require_nonnegative(ending_material_last, "最后一期期末材料")
    usage = [volume * usage_per_unit for volume in production_values]
    n = len(usage)
    ending = [usage[i + 1] * ratio if i < n - 1 else last_ending for i in range(n)]
    beginnings = [beginning] + ending[:-1]
    purchases = [use + end - start for use, end, start in zip(usage, ending, beginnings)]
    if any(value < 0 for value in purchases):
        raise ValidationError("某期材料采购量为负数，请检查材料存货假设。")
    costs = [purchase * price for purchase in purchases]
    periods = _period_names(n)
    return pd.DataFrame(
        {
            "项目": [
                "预计生产量", "单位材料用量", "生产耗用量", "加：期末材料",
                "减：期初材料", "预计采购量", "材料单价", "预计采购金额",
            ],
            **{
                period: [
                    round(prod, 2), round(usage_per_unit, 2), round(use, 2),
                    round(end, 2), round(start, 2), round(purchase, 2),
                    round(price, 2), round(cost, 2),
                ]
                for period, prod, use, end, start, purchase, cost in zip(
                    periods, production_values, usage, ending, beginnings, purchases, costs
                )
            },
            "全年": [
                round(sum(production_values), 2), round(usage_per_unit, 2),
                round(sum(usage), 2), round(ending[-1], 2), round(beginning, 2),
                round(sum(purchases), 2), round(price, 2), round(sum(costs), 2),
            ],
        }
    )


def labor_schedule(
    production_volumes: Sequence[float], hours_per_unit: float, wage_rate: float
) -> pd.DataFrame:
    """直接人工预算：工时=产量×单位工时，人工成本=工时×工资率。"""
    production_values = _validate_quarters(production_volumes, "生产量")
    hours = require_nonnegative(hours_per_unit, "单位产品工时")
    wage = require_positive(wage_rate, "小时工资率")
    total_hours = [volume * hours for volume in production_values]
    cost = [hour * wage for hour in total_hours]
    periods = _period_names(len(production_values))
    return pd.DataFrame(
        {
            "项目": ["预计生产量", "单位产品工时", "直接人工工时", "小时工资率", "直接人工成本"],
            **{
                period: [
                    round(prod, 2), round(hours, 2), round(hour, 2),
                    round(wage, 2), round(cost_value, 2),
                ]
                for period, prod, hour, cost_value in zip(
                    periods, production_values, total_hours, cost
                )
            },
            "全年": [
                round(sum(production_values), 2), round(hours, 2),
                round(sum(total_hours), 2), round(wage, 2), round(sum(cost), 2),
            ],
        }
    )


def overhead_schedule(
    labor_hours: Sequence[float],
    variable_rate: float,
    fixed_costs: Sequence[float],
    depreciation: Sequence[float],
) -> pd.DataFrame:
    """制造费用预算：变动费用按工时分配，固定费用按期发生，扣除折旧得到付现额。"""
    hours = _validate_quarters(labor_hours, "直接人工工时")
    rate = require_nonnegative(variable_rate, "变动制造费用分配率")
    fixed = _validate_quarters(fixed_costs, "固定制造费用")
    dep = _validate_quarters(depreciation, "折旧")
    require_same_length(hours, fixed, dep, names=["工时", "固定制造费用", "折旧"])
    variable_costs = [hour * rate for hour in hours]
    totals = [variable + fixed_value for variable, fixed_value in zip(variable_costs, fixed)]
    cash_costs = [total - dep_value for total, dep_value in zip(totals, dep)]
    periods = _period_names(len(hours))
    return pd.DataFrame(
        {
            "项目": ["直接人工工时", "变动制造费用分配率", "变动制造费用", "固定制造费用", "制造费用合计", "减：折旧", "制造费用付现额"],
            **{
                period: [
                    round(hour, 2), round(rate, 4), round(variable, 2),
                    round(fixed_value, 2), round(total, 2), round(dep_value, 2),
                    round(cash_value, 2),
                ]
                for period, hour, variable, fixed_value, total, dep_value, cash_value in zip(
                    periods, hours, variable_costs, fixed, totals, dep, cash_costs
                )
            },
            "全年": [
                round(sum(hours), 2), round(rate, 4), round(sum(variable_costs), 2),
                round(sum(fixed), 2), round(sum(totals), 2), round(sum(dep), 2),
                round(sum(cash_costs), 2),
            ],
        }
    )


def product_cost_schedule(
    total_output: float,
    material_per_unit: float,
    material_unit_price: float,
    hours_per_unit: float,
    wage_rate: float,
    variable_overhead_rate: float,
    fixed_overhead_total: float,
) -> pd.DataFrame:
    """产品成本预算：单位成本与总成本。"""
    output = require_positive(total_output, "全年生产量")
    material = require_positive(material_per_unit, "单位材料用量")
    material_price = require_positive(material_unit_price, "材料单价")
    hours = require_nonnegative(hours_per_unit, "单位工时")
    wage = require_positive(wage_rate, "小时工资率")
    variable_rate = require_nonnegative(variable_overhead_rate, "变动制造费用分配率")
    fixed_total = require_nonnegative(fixed_overhead_total, "固定制造费用总额")
    unit_material = material * material_price
    unit_labor = hours * wage
    unit_variable = hours * variable_rate
    unit_fixed = fixed_total / output
    total_unit = unit_material + unit_labor + unit_variable + unit_fixed
    return pd.DataFrame(
        {
            "成本项目": ["直接材料", "直接人工", "变动制造费用", "固定制造费用", "单位产品成本"],
            "单位成本（元/件）": [
                round(unit_material, 4),
                round(unit_labor, 4),
                round(unit_variable, 4),
                round(unit_fixed, 4),
                round(total_unit, 4),
            ],
            "总成本（元）": [
                round(unit_material * output, 2),
                round(unit_labor * output, 2),
                round(unit_variable * output, 2),
                round(unit_fixed * output, 2),
                round(total_unit * output, 2),
            ],
        }
    )


def cash_schedule(
    sales: Sequence[float],
    collection_rates: Sequence[float],
    beginning_receivables: float,
    purchases: Sequence[float],
    payment_rates: Sequence[float],
    beginning_payables: float,
    labor_costs: Sequence[float],
    overhead_cash_costs: Sequence[float],
    selling_admin_costs: Sequence[float],
    equipment_purchases: Sequence[float],
    income_taxes: Sequence[float],
    dividends: Sequence[float],
    initial_cash: float,
    minimum_cash: float,
    borrowing_rate: float,
) -> pd.DataFrame:
    """现金预算：销售回款、采购付款、经营支出、投资/筹资及借款安排。"""
    sales_values = _validate_quarters(sales, "销售额")
    purchase_values = _validate_quarters(purchases, "材料采购额")
    labor_values = _validate_quarters(labor_costs, "直接人工")
    overhead_values = _validate_quarters(overhead_cash_costs, "制造费用付现额")
    selling_values = _validate_quarters(selling_admin_costs, "销售管理费用")
    equipment_values = _validate_quarters(equipment_purchases, "设备购置")
    tax_values = _validate_quarters(income_taxes, "所得税")
    dividend_values = _validate_quarters(dividends, "股利")
    require_same_length(
        sales_values, purchase_values, labor_values, overhead_values,
        selling_values, equipment_values, tax_values, dividend_values,
        names=["销售额", "采购额", "人工", "制造费用", "销售管理", "设备", "所得税", "股利"],
    )
    collection = [require_rate(rate, "销售回款比例", max_value=1.0) for rate in collection_rates]
    payment = [require_rate(rate, "采购付款比例", max_value=1.0) for rate in payment_rates]
    if sum(collection) > 1.0 + 1e-9:
        raise ValidationError("销售回款比例之和不能超过 100%。")
    if sum(payment) > 1.0 + 1e-9:
        raise ValidationError("采购付款比例之和不能超过 100%。")
    receivables = require_nonnegative(beginning_receivables, "期初应收账款")
    payables = require_nonnegative(beginning_payables, "期初应付账款")
    initial = require_nonnegative(initial_cash, "期初现金余额")
    minimum = require_nonnegative(minimum_cash, "最低现金余额")
    loan_rate = require_rate(borrowing_rate, "季度借款利率")

    n = len(sales_values)
    receipts: List[float] = []
    for t in range(n):
        amount = 0.0
        for lag, rate in enumerate(collection):
            if t - lag >= 0:
                amount += rate * sales_values[t - lag]
        if t == 0:
            amount += receivables
        receipts.append(amount)

    material_payments: List[float] = []
    for t in range(n):
        amount = 0.0
        for lag, rate in enumerate(payment):
            if t - lag >= 0:
                amount += rate * purchase_values[t - lag]
        if t == 0:
            amount += payables
        material_payments.append(amount)

    records = []
    cash_begin = initial
    loan_begin = 0.0
    periods = _period_names(n)
    for t in range(n):
        interest = loan_begin * loan_rate
        disbursements = (
            material_payments[t] + labor_values[t] + overhead_values[t]
            + selling_values[t] + equipment_values[t] + tax_values[t] + dividend_values[t]
        )
        before_financing = cash_begin + receipts[t] - disbursements - interest
        if before_financing < minimum:
            borrowing = minimum - before_financing
            repayment = 0.0
            cash_end = minimum
            loan_end = loan_begin + borrowing
        else:
            borrowing = 0.0
            repayment = min(loan_begin, before_financing - minimum)
            cash_end = before_financing - repayment
            loan_end = loan_begin - repayment
        records.append(
            {
                "期间": periods[t],
                "期初现金": round(cash_begin, 2),
                "销售回款": round(receipts[t], 2),
                "材料采购付款": round(material_payments[t], 2),
                "直接人工": round(labor_values[t], 2),
                "制造费用付现": round(overhead_values[t], 2),
                "销售管理费用": round(selling_values[t], 2),
                "设备购置": round(equipment_values[t], 2),
                "所得税": round(tax_values[t], 2),
                "股利": round(dividend_values[t], 2),
                "借款利息": round(interest, 2),
                "融资前现金余缺": round(before_financing, 2),
                "借款": round(borrowing, 2),
                "还款": round(repayment, 2),
                "期末现金": round(cash_end, 2),
                "期末借款余额": round(loan_end, 2),
            }
        )
        cash_begin = cash_end
        loan_begin = loan_end
    return pd.DataFrame(records)


def integrated_budget_result(data: Dict[str, object]) -> CalcResult:
    """编制七张相互联动的季度预算表。"""
    volumes = _validate_quarters(data.get("sales_volumes"), "销售量")
    price = require_positive(data.get("price"), "销售单价")
    n = len(volumes)
    periods = _period_names(n)
    sales_table = sales_schedule(volumes, price)
    production_table = production_schedule(
        volumes,
        data.get("beginning_fg"),
        data.get("ending_fg_ratio"),
        data.get("ending_fg_last"),
    )
    production_values = [
        float(production_table.loc[production_table["项目"] == "预计生产量", period].iloc[0])
        for period in periods
    ]
    materials_table = materials_schedule(
        production_values,
        data.get("material_per_unit"),
        data.get("material_price"),
        data.get("beginning_material"),
        data.get("ending_material_ratio"),
        data.get("ending_material_last"),
    )
    purchases = [
        float(materials_table.loc[materials_table["项目"] == "预计采购金额", period].iloc[0])
        for period in periods
    ]
    labor_table = labor_schedule(
        production_values, data.get("hours_per_unit"), data.get("wage_rate")
    )
    labor_costs = [
        float(labor_table.loc[labor_table["项目"] == "直接人工成本", period].iloc[0])
        for period in periods
    ]
    labor_hours = [
        float(labor_table.loc[labor_table["项目"] == "直接人工工时", period].iloc[0])
        for period in periods
    ]
    fixed_raw = data.get("fixed_overhead")
    dep_raw = data.get("depreciation")
    fixed_costs = (
        [require_nonnegative(fixed_raw, "固定制造费用")] * n
        if isinstance(fixed_raw, (int, float))
        else _validate_quarters(fixed_raw, "固定制造费用")
    )
    depreciation_costs = (
        [require_nonnegative(dep_raw, "折旧")] * n
        if isinstance(dep_raw, (int, float))
        else _validate_quarters(dep_raw, "折旧")
    )
    overhead_table = overhead_schedule(
        labor_hours,
        data.get("variable_overhead_rate"),
        fixed_costs,
        depreciation_costs,
    )
    overhead_cash = [
        float(overhead_table.loc[overhead_table["项目"] == "制造费用付现额", period].iloc[0])
        for period in periods
    ]
    product_table = product_cost_schedule(
        sum(production_values),
        data.get("material_per_unit"),
        data.get("material_price"),
        data.get("hours_per_unit"),
        data.get("wage_rate"),
        data.get("variable_overhead_rate"),
        sum(fixed_costs),
    )
    sales_amounts = [volume * price for volume in volumes]
    cash_table = cash_schedule(
        sales_amounts,
        data.get("collection_rates", [1.0]),
        data.get("beginning_receivables", 0),
        purchases,
        data.get("payment_rates", [1.0]),
        data.get("beginning_payables", 0),
        labor_costs,
        overhead_cash,
        data.get("selling_admin"),
        data.get("equipment_purchases"),
        data.get("income_taxes"),
        data.get("dividends"),
        data.get("initial_cash"),
        data.get("minimum_cash"),
        data.get("borrowing_rate"),
    )

    annual_sales = sum(sales_amounts)
    annual_production = sum(production_values)
    annual_purchase = sum(purchases)
    annual_labor = sum(labor_costs)
    annual_overhead_cash = sum(overhead_cash)
    unit_product_cost = float(
        product_table.loc[product_table["成本项目"] == "单位产品成本", "单位成本（元/件）"].iloc[0]
    )
    ending_cash = float(cash_table["期末现金"].iloc[-1])
    max_loan = float(cash_table["期末借款余额"].max())

    result = CalcResult(
        MODULE,
        "七表联动财务预算",
        {
            "预算期数": f"{n} 个季度",
            "销售单价": f"{money(price)} 元",
            "销售数量": [f"{v:,.2f}" for v in volumes],
            "期初产成品": f"{data.get('beginning_fg')} 件",
            "期初材料": f"{data.get('beginning_material')} 千克",
            "单位材料用量": f"{data.get('material_per_unit')} 千克/件",
            "单位工时": f"{data.get('hours_per_unit')} 小时/件",
            "小时工资率": f"{money(data.get('wage_rate'))} 元/小时",
            "变动制造费用率": f"{money(data.get('variable_overhead_rate'))} 元/小时",
            "期初现金": f"{money(data.get('initial_cash'))} 元",
            "最低现金": f"{money(data.get('minimum_cash'))} 元",
        },
    )
    result.add_step("1. 销售预算：预计销售收入=预计销售量×单价。")
    result.add_step("2. 生产预算：预计生产量=预计销售量+期末产成品-期初产成品。")
    result.add_step(
        "3. 直接材料预算：耗用量=生产量×单位用量；"
        "采购量=耗用量+期末材料-期初材料；采购金额=采购量×材料单价。"
    )
    result.add_step("4. 直接人工预算：人工工时=生产量×单位工时；人工成本=工时×工资率。")
    result.add_step(
        "5. 制造费用预算：变动制造费用=人工工时×分配率；"
        "制造费用付现额=制造费用合计-折旧。"
    )
    result.add_step(
        "6. 产品成本预算：单位成本=单位材料+单位人工+单位变动制造费用+单位固定制造费用。"
    )
    result.add_step(
        "7. 现金预算：期初现金+销售回款-各项支出-利息±借款/还款=期末现金；"
        "期末现金不足最低余额时借款，超过最低余额时优先还款。"
    )
    result.add_step(
        f"全年销售收入={money(annual_sales)} 元；全年生产量={annual_production:,.2f} 件；"
        f"全年材料采购={money(annual_purchase)} 元；全年人工成本={money(annual_labor)} 元。"
    )
    result.add_step(
        f"制造费用全年付现额={money(annual_overhead_cash)} 元；"
        f"单位产品成本={money(unit_product_cost)} 元/件。"
    )
    result.add_step(f"预算期末现金={money(ending_cash)} 元；预算期内最高借款余额={money(max_loan)} 元。")

    result.add_table("1. 销售预算", sales_table)
    result.add_table("2. 生产预算", production_table)
    result.add_table("3. 直接材料预算", materials_table)
    result.add_table("4. 直接人工预算", labor_table)
    result.add_table("5. 制造费用预算", overhead_table)
    result.add_table("6. 产品成本预算", product_table)
    result.add_table("7. 现金预算", cash_table)

    result.put("全年销售收入", f"{money(annual_sales)} 元")
    result.put("全年生产量", f"{annual_production:,.2f} 件")
    result.put("全年材料采购金额", f"{money(annual_purchase)} 元")
    result.put("全年直接人工成本", f"{money(annual_labor)} 元")
    result.put("全年制造费用付现额", f"{money(annual_overhead_cash)} 元")
    result.put("单位产品成本", f"{money(unit_product_cost)} 元/件")
    result.put("期末现金余额", f"{money(ending_cash)} 元")
    result.put("最高借款余额", f"{money(max_loan)} 元")
    result.add_note("现金预算假设期初应收账款和期初应付账款均在第一季度收回/支付。")
    result.add_note("借款按季度期初余额计息，借款发生在季末，当季不重复计息。")
    result.add_note("若回款/付款比例之和小于 100%，差额形成期末应收/应付账款余额。")
    return result


# ---------------------------------------------------------------------------
# 交互菜单与例题
# ---------------------------------------------------------------------------
def _default_budget_data() -> Dict[str, object]:
    """一套可直接运行的季度预算数据。"""
    volumes = [1000.0, 1200.0, 1500.0, 1300.0]
    n = len(volumes)
    return {
        "sales_volumes": volumes,
        "price": 100.0,
        "beginning_fg": 100.0,
        "ending_fg_ratio": 0.10,
        "ending_fg_last": 150.0,
        "material_per_unit": 2.0,
        "material_price": 5.0,
        "beginning_material": 200.0,
        "ending_material_ratio": 0.20,
        "ending_material_last": 300.0,
        "hours_per_unit": 1.5,
        "wage_rate": 20.0,
        "variable_overhead_rate": 5.0,
        "fixed_overhead": 20000.0,
        "depreciation": 8000.0,
        "collection_rates": [0.60, 0.40],
        "beginning_receivables": 80000.0,
        "payment_rates": [0.70, 0.30],
        "beginning_payables": 30000.0,
        "selling_admin": [30000.0] * n,
        "equipment_purchases": [100000.0, 0.0, 0.0, 0.0],
        "income_taxes": [10000.0] * n,
        "dividends": [0.0, 50000.0, 0.0, 0.0],
        "initial_cash": 50000.0,
        "minimum_cash": 40000.0,
        "borrowing_rate": 0.02,
    }


def _interactive() -> CalcResult:
    data = _default_budget_data()
    print("【销售预算】")
    volumes = ask_series("四个季度销售量（件）", data["sales_volumes"], min_length=1)
    if len(volumes) > 12:
        raise ValidationError("预算最多支持 12 个季度。")
    n = len(volumes)
    data["sales_volumes"] = volumes
    data["price"] = ask_float("销售单价（元）", data["price"], min_value=0, allow_negative=False)
    print("\n【生产预算】")
    data["beginning_fg"] = ask_float("期初产成品（件）", data["beginning_fg"], min_value=0, allow_negative=False)
    data["ending_fg_ratio"] = ask_rate_percent("期末产成品占下期销售比例", data["ending_fg_ratio"], max_percent=100)
    data["ending_fg_last"] = ask_float("最后一期期末产成品（件）", data["ending_fg_last"], min_value=0, allow_negative=False)
    print("\n【直接材料预算】")
    data["material_per_unit"] = ask_float("单位产品材料用量（千克/件）", data["material_per_unit"], min_value=0, allow_negative=False)
    data["material_price"] = ask_float("材料单价（元/千克）", data["material_price"], min_value=0, allow_negative=False)
    data["beginning_material"] = ask_float("期初材料（千克）", data["beginning_material"], min_value=0, allow_negative=False)
    data["ending_material_ratio"] = ask_rate_percent("期末材料占下期耗用比例", data["ending_material_ratio"], max_percent=200)
    data["ending_material_last"] = ask_float("最后一期期末材料（千克）", data["ending_material_last"], min_value=0, allow_negative=False)
    print("\n【直接人工与制造费用预算】")
    data["hours_per_unit"] = ask_float("单位产品工时（小时/件）", data["hours_per_unit"], min_value=0, allow_negative=False)
    data["wage_rate"] = ask_float("小时工资率（元/小时）", data["wage_rate"], min_value=0, allow_negative=False)
    data["variable_overhead_rate"] = ask_float("变动制造费用分配率（元/小时）", data["variable_overhead_rate"], min_value=0, allow_negative=False)
    data["fixed_overhead"] = ask_float("每季度固定制造费用（元）", data["fixed_overhead"], min_value=0, allow_negative=False)
    data["depreciation"] = ask_float("每季度折旧（元）", data["depreciation"], min_value=0, allow_negative=False)
    print("\n【现金预算】")
    data["collection_rates"] = ask_series("销售回款比例（当期、下期…，小数）", data["collection_rates"], min_length=1)
    data["beginning_receivables"] = ask_float("期初应收账款（元）", data["beginning_receivables"], min_value=0, allow_negative=False)
    data["payment_rates"] = ask_series("采购付款比例（当期、下期…，小数）", data["payment_rates"], min_length=1)
    data["beginning_payables"] = ask_float("期初应付账款（元）", data["beginning_payables"], min_value=0, allow_negative=False)
    data["selling_admin"] = ask_series("各期销售管理费用（元）", [30000.0] * n, min_length=n, allow_negative=False)
    data["equipment_purchases"] = ask_series("各期设备购置支出（元）", [100000.0] + [0.0] * (n - 1), min_length=n, allow_negative=False)
    data["income_taxes"] = ask_series("各期所得税（元）", [10000.0] * n, min_length=n, allow_negative=False)
    data["dividends"] = ask_series("各期股利支出（元）", [0.0] * n, min_length=n, allow_negative=False)
    data["initial_cash"] = ask_float("期初现金余额（元）", data["initial_cash"], min_value=0, allow_negative=False)
    data["minimum_cash"] = ask_float("最低现金余额（元）", data["minimum_cash"], min_value=0, allow_negative=False)
    data["borrowing_rate"] = ask_rate_percent("季度借款利率", data["borrowing_rate"])
    if len(data["selling_admin"]) != n or len(data["equipment_purchases"]) != n:
        raise ValidationError("现金预算各项支出期数必须与销售预算期数一致。")
    return integrated_budget_result(data)


def _run_demo() -> None:
    """一键演示七表联动预算。"""
    print_heading("财务预算：七表联动例题演示", "★")
    show_result(integrated_budget_result(_default_budget_data()))
    print("\n[演示完成] 已生成销售、生产、材料、人工、制造费用、产品成本和现金预算。")


def run() -> None:
    """模块 12 控制台菜单。"""
    while True:
        print_heading("模块12 财务预算（七表联动）")
        print("  1. 编制全套财务预算（销售→生产→材料→人工→制造费用→产品成本→现金）")
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
