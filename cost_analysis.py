"""模块 7：成本管理。

覆盖本量利分析、标准成本差异分析（直接材料、直接人工、变动制造费用、
固定制造费用二差异/三差异）和作业成本简易计算。
"""

from __future__ import annotations

from typing import Dict, List, Sequence

import pandas as pd

from utils import (
    CalcResult,
    ValidationError,
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
)


MODULE = "模块7 成本管理"


# ---------------------------------------------------------------------------
# 本量利分析
# ---------------------------------------------------------------------------
def cvp_analysis(
    unit_price: float,
    unit_variable_cost: float,
    fixed_cost: float,
    actual_quantity: float,
    *,
    plot: bool = False,
) -> CalcResult:
    """本量利分析：边际贡献、EBIT、保本点、安全边际和敏感系数。"""
    price = require_positive(unit_price, "单价 P")
    variable = require_nonnegative(unit_variable_cost, "单位变动成本 V")
    fixed = require_nonnegative(fixed_cost, "固定成本 F")
    quantity = require_positive(actual_quantity, "实际销售量 Q")
    if price <= variable:
        raise ValidationError("单价必须大于单位变动成本，否则不存在边际贡献和保本点。")
    contribution_per_unit = price - variable
    contribution_ratio = contribution_per_unit / price
    contribution = quantity * contribution_per_unit
    ebit = contribution - fixed
    break_even_quantity = fixed / contribution_per_unit
    break_even_sales = break_even_quantity * price
    actual_sales = quantity * price
    safety_margin = actual_sales - break_even_sales
    safety_margin_ratio = safety_margin / actual_sales
    result = CalcResult(
        MODULE,
        "本量利分析",
        {
            "单价 P": f"{money(price)} 元",
            "单位变动成本 V": f"{money(variable)} 元",
            "固定成本 F": f"{money(fixed)} 元",
            "实际销售量 Q": f"{quantity:,.2f} 件",
        },
    )
    result.add_step(f"单位边际贡献 = P-V = {money(price)}-{money(variable)} = {money(contribution_per_unit)} 元。")
    result.add_step(f"边际贡献率 = (P-V)/P = {money(contribution_per_unit)}/{money(price)} = {percent(contribution_ratio)}。")
    result.add_step(f"边际贡献总额 = Q×(P-V) = {quantity:,.2f}×{money(contribution_per_unit)} = {money(contribution)} 元。")
    result.add_step(f"息税前利润 EBIT = 边际贡献-F = {money(contribution)}-{money(fixed)} = {money(ebit)} 元。")
    result.add_step(f"盈亏临界点销售量 = F/(P-V) = {money(fixed)}/{money(contribution_per_unit)} = {break_even_quantity:,.2f} 件。")
    result.add_step(f"盈亏临界点销售额 = F/边际贡献率 = {money(fixed)}/{percent(contribution_ratio)} = {money(break_even_sales)} 元。")
    result.add_step(f"安全边际额 = 实际销售额-保本销售额 = {money(actual_sales)}-{money(break_even_sales)} = {money(safety_margin)} 元。")
    result.add_step(f"安全边际率 = 安全边际额/实际销售额 = {percent(safety_margin_ratio)}。")
    result.put("单位边际贡献", f"{money(contribution_per_unit)} 元")
    result.put("边际贡献率", percent(contribution_ratio))
    result.put("边际贡献总额", f"{money(contribution)} 元")
    result.put("息税前利润 EBIT", f"{money(ebit)} 元")
    result.put("盈亏临界点销售量", f"{break_even_quantity:,.2f} 件")
    result.put("盈亏临界点销售额", f"{money(break_even_sales)} 元")
    result.put("安全边际额", f"{money(safety_margin)} 元")
    result.put("安全边际率", percent(safety_margin_ratio))

    if abs(ebit) > 1e-12:
        sensitivities = {
            "销售量敏感系数": contribution / ebit,
            "单价敏感系数": actual_sales / ebit,
            "单位变动成本敏感系数": -quantity * variable / ebit,
            "固定成本敏感系数": -fixed / ebit,
        }
        for name, value in sensitivities.items():
            result.put(name, f"{value:.4f}")
        result.add_step(
            "敏感系数 = 利润变动百分比 ÷ 因素变动百分比。本量利模型下："
            "销量敏感系数=边际贡献/EBIT；单价敏感系数=销售收入/EBIT；"
            "单位变动成本敏感系数=-变动成本总额/EBIT；固定成本敏感系数=-F/EBIT。"
        )
        result.add_step(
            "各因素敏感系数："
            + "；".join(f"{name.replace('敏感系数', '')}={value:.4f}" for name, value in sensitivities.items())
            + "。"
        )
        result.add_note(
            "敏感系数绝对值越大，该因素变动对利润影响越强；正号表示同向，负号表示反向。"
        )
    else:
        result.add_note("EBIT=0 时敏感系数无定义，企业正处于盈亏临界点。")

    if ebit > 0:
        result.add_note("企业当前盈利，实际销售量高于盈亏临界点，安全边际为正。")
    else:
        result.add_note("企业当前处于保本点或亏损状态，应提高售价、降低变动成本或扩大销量。")
    if plot:
        from visual import plot_cvp

        image_path = plot_cvp(price, variable, fixed, quantity)
        result.put("本量利图", str(image_path))
    return result


# ---------------------------------------------------------------------------
# 标准成本差异分析
# ---------------------------------------------------------------------------
def _variance_nature(value: float) -> str:
    """判断成本差异性质：负数为节约（有利），正数为超支（不利）。"""
    if abs(value) < 1e-9:
        return "无差异"
    return "有利差异（节约）" if value < 0 else "不利差异（超支）"


def _variance_text(value: float) -> str:
    return f"{money(value)} 元（{_variance_nature(value)}）"


def direct_material_variances(
    actual_output: float,
    standard_quantity_per_unit: float,
    actual_quantity: float,
    standard_price: float,
    actual_price: float,
) -> Dict[str, float]:
    """直接材料价格差异与用量差异。"""
    output = require_positive(actual_output, "实际产量")
    std_per_unit = require_nonnegative(standard_quantity_per_unit, "单位标准用量")
    actual_qty = require_nonnegative(actual_quantity, "实际用量")
    std_price = require_positive(standard_price, "标准单价")
    act_price = require_positive(actual_price, "实际单价")
    standard_quantity = output * std_per_unit
    price_variance = actual_qty * (act_price - std_price)
    quantity_variance = (actual_qty - standard_quantity) * std_price
    total = actual_qty * act_price - standard_quantity * std_price
    return {
        "standard_quantity": standard_quantity,
        "actual_cost": actual_qty * act_price,
        "standard_cost": standard_quantity * std_price,
        "price_variance": price_variance,
        "quantity_variance": quantity_variance,
        "total_variance": total,
    }


def direct_material_result(
    actual_output: float,
    standard_quantity_per_unit: float,
    actual_quantity: float,
    standard_price: float,
    actual_price: float,
) -> CalcResult:
    """构建直接材料差异分析结果。"""
    values = direct_material_variances(
        actual_output, standard_quantity_per_unit, actual_quantity, standard_price, actual_price
    )
    result = CalcResult(
        MODULE,
        "标准成本差异——直接材料",
        {
            "实际产量": f"{actual_output:,.2f} 件",
            "单位标准用量": f"{standard_quantity_per_unit:,.2f} 千克/件",
            "实际用量": f"{actual_quantity:,.2f} 千克",
            "标准单价": f"{money(standard_price)} 元/千克",
            "实际单价": f"{money(actual_price)} 元/千克",
        },
    )
    result.add_step(
        f"标准用量 = 实际产量×单位标准用量 = {actual_output:,.2f}×{standard_quantity_per_unit:,.2f} "
        f"= {values['standard_quantity']:,.2f} 千克。"
    )
    result.add_step(
        f"实际材料成本 = 实际用量×实际单价 = {money(values['actual_cost'])} 元；"
        f"标准材料成本 = 标准用量×标准单价 = {money(values['standard_cost'])} 元。"
    )
    result.add_step(
        f"材料价格差异 = 实际用量×(实际单价-标准单价) = "
        f"{_variance_text(values['price_variance'])}。"
    )
    result.add_step(
        f"材料用量差异 = (实际用量-标准用量)×标准单价 = "
        f"{_variance_text(values['quantity_variance'])}。"
    )
    result.add_step(
        f"材料成本总差异 = 实际成本-标准成本 = {_variance_text(values['total_variance'])}；"
        "价格差异+用量差异应等于总差异。"
    )
    result.put("材料价格差异", _variance_text(values["price_variance"]))
    result.put("材料用量差异", _variance_text(values["quantity_variance"]))
    result.put("材料成本总差异", _variance_text(values["total_variance"]))
    result.add_note("价格差异通常由采购部门负责，用量差异通常由生产部门负责，但应结合责任归属具体分析。")
    return result


def direct_labor_variances(
    actual_output: float,
    standard_hours_per_unit: float,
    actual_hours: float,
    standard_rate: float,
    actual_rate: float,
) -> Dict[str, float]:
    """直接人工工资率差异与效率差异。"""
    output = require_positive(actual_output, "实际产量")
    std_hours_per_unit = require_nonnegative(standard_hours_per_unit, "单位标准工时")
    actual_h = require_nonnegative(actual_hours, "实际工时")
    std_rate = require_positive(standard_rate, "标准工资率")
    act_rate = require_positive(actual_rate, "实际工资率")
    standard_hours = output * std_hours_per_unit
    rate_variance = actual_h * (act_rate - std_rate)
    efficiency_variance = (actual_h - standard_hours) * std_rate
    total = actual_h * act_rate - standard_hours * std_rate
    return {
        "standard_hours": standard_hours,
        "actual_cost": actual_h * act_rate,
        "standard_cost": standard_hours * std_rate,
        "rate_variance": rate_variance,
        "efficiency_variance": efficiency_variance,
        "total_variance": total,
    }


def direct_labor_result(
    actual_output: float,
    standard_hours_per_unit: float,
    actual_hours: float,
    standard_rate: float,
    actual_rate: float,
) -> CalcResult:
    """构建直接人工差异分析结果。"""
    values = direct_labor_variances(
        actual_output, standard_hours_per_unit, actual_hours, standard_rate, actual_rate
    )
    result = CalcResult(
        MODULE,
        "标准成本差异——直接人工",
        {
            "实际产量": f"{actual_output:,.2f} 件",
            "单位标准工时": f"{standard_hours_per_unit:,.2f} 小时/件",
            "实际工时": f"{actual_hours:,.2f} 小时",
            "标准工资率": f"{money(standard_rate)} 元/小时",
            "实际工资率": f"{money(actual_rate)} 元/小时",
        },
    )
    result.add_step(
        f"标准工时 = 实际产量×单位标准工时 = {values['standard_hours']:,.2f} 小时。"
    )
    result.add_step(
        f"实际人工成本 = 实际工时×实际工资率 = {money(values['actual_cost'])} 元；"
        f"标准人工成本 = {money(values['standard_cost'])} 元。"
    )
    result.add_step(
        f"工资率差异 = 实际工时×(实际工资率-标准工资率) = "
        f"{_variance_text(values['rate_variance'])}。"
    )
    result.add_step(
        f"人工效率差异 = (实际工时-标准工时)×标准工资率 = "
        f"{_variance_text(values['efficiency_variance'])}。"
    )
    result.add_step(f"人工成本总差异 = {_variance_text(values['total_variance'])}。")
    result.put("工资率差异", _variance_text(values["rate_variance"]))
    result.put("人工效率差异", _variance_text(values["efficiency_variance"]))
    result.put("人工成本总差异", _variance_text(values["total_variance"]))
    return result


def variable_overhead_result(
    actual_output: float,
    standard_hours_per_unit: float,
    actual_hours: float,
    standard_rate: float,
    actual_rate: float,
) -> CalcResult:
    """变动制造费用耗费差异与效率差异。"""
    output = require_positive(actual_output, "实际产量")
    std_hours_per_unit = require_nonnegative(standard_hours_per_unit, "单位标准工时")
    actual_h = require_nonnegative(actual_hours, "实际工时")
    std_rate = require_positive(standard_rate, "标准分配率")
    act_rate = require_positive(actual_rate, "实际分配率")
    standard_hours = output * std_hours_per_unit
    actual_cost = actual_h * act_rate
    standard_cost = standard_hours * std_rate
    spending = actual_h * (act_rate - std_rate)
    efficiency = (actual_h - standard_hours) * std_rate
    total = actual_cost - standard_cost
    result = CalcResult(
        MODULE,
        "标准成本差异——变动制造费用",
        {
            "实际产量": f"{output:,.2f} 件",
            "单位标准工时": f"{std_hours_per_unit:,.2f} 小时/件",
            "实际工时": f"{actual_h:,.2f} 小时",
            "标准分配率": f"{money(std_rate)} 元/小时",
            "实际分配率": f"{money(act_rate)} 元/小时",
        },
    )
    result.add_step(f"标准工时 = {output:,.2f}×{std_hours_per_unit:,.2f} = {standard_hours:,.2f} 小时。")
    result.add_step(
        f"变动制造费用耗费差异 = 实际工时×(实际分配率-标准分配率) = {_variance_text(spending)}。"
    )
    result.add_step(
        f"变动制造费用效率差异 = (实际工时-标准工时)×标准分配率 = {_variance_text(efficiency)}。"
    )
    result.add_step(
        f"实际费用 {money(actual_cost)} 元，标准费用 {money(standard_cost)} 元，"
        f"总差异 = {_variance_text(total)}。"
    )
    result.put("耗费差异", _variance_text(spending))
    result.put("效率差异", _variance_text(efficiency))
    result.put("变动制造费用总差异", _variance_text(total))
    return result


def fixed_overhead_two_variance(
    actual_fixed_overhead: float,
    budgeted_fixed_overhead: float,
    denominator_hours: float,
    standard_hours_allowed: float,
) -> Dict[str, float]:
    """固定制造费用二差异法：耗费差异 + 产量（能量）差异。"""
    actual = require_nonnegative(actual_fixed_overhead, "实际固定制造费用")
    budget = require_nonnegative(budgeted_fixed_overhead, "预算固定制造费用")
    denom = require_positive(denominator_hours, "预算产量标准工时")
    allowed = require_nonnegative(standard_hours_allowed, "实际产量标准工时")
    rate = budget / denom
    applied = allowed * rate
    spending = actual - budget
    volume = budget - applied
    total = actual - applied
    return {
        "rate": rate,
        "applied": applied,
        "spending": spending,
        "volume": volume,
        "total": total,
    }


def fixed_overhead_two_variance_result(
    actual_fixed_overhead: float,
    budgeted_fixed_overhead: float,
    denominator_hours: float,
    standard_hours_allowed: float,
) -> CalcResult:
    """构建固定制造费用二差异分析结果。"""
    values = fixed_overhead_two_variance(
        actual_fixed_overhead, budgeted_fixed_overhead, denominator_hours, standard_hours_allowed
    )
    result = CalcResult(
        MODULE,
        "标准成本差异——固定制造费用（二差异法）",
        {
            "实际固定制造费用": f"{money(actual_fixed_overhead)} 元",
            "预算固定制造费用": f"{money(budgeted_fixed_overhead)} 元",
            "预算产量标准工时": f"{denominator_hours:,.2f} 小时",
            "实际产量标准工时": f"{standard_hours_allowed:,.2f} 小时",
        },
    )
    result.add_step(f"固定制造费用标准分配率 = 预算固定制造费用/预算工时 = {money(values['rate'])} 元/小时。")
    result.add_step(f"实际产量应负担固定制造费用 = 实际产量标准工时×分配率 = {money(values['applied'])} 元。")
    result.add_step(f"耗费差异 = 实际固定制造费用-预算固定制造费用 = {_variance_text(values['spending'])}。")
    result.add_step(
        f"产量差异（能量差异）= 预算固定制造费用-实际产量应负担额 = "
        f"{_variance_text(values['volume'])}。"
    )
    result.add_step(f"固定制造费用总差异 = {_variance_text(values['total'])}。")
    result.put("固定制造费用分配率", f"{money(values['rate'])} 元/小时")
    result.put("实际产量应负担额", f"{money(values['applied'])} 元")
    result.put("耗费差异", _variance_text(values["spending"]))
    result.put("产量差异", _variance_text(values["volume"]))
    result.put("固定制造费用总差异", _variance_text(values["total"]))
    return result


def fixed_overhead_three_variance(
    actual_fixed_overhead: float,
    budgeted_fixed_overhead: float,
    denominator_hours: float,
    actual_hours: float,
    standard_hours_allowed: float,
) -> Dict[str, float]:
    """固定制造费用三差异法：耗费差异 + 闲置能量差异 + 效率差异。"""
    actual = require_nonnegative(actual_fixed_overhead, "实际固定制造费用")
    budget = require_nonnegative(budgeted_fixed_overhead, "预算固定制造费用")
    denom = require_positive(denominator_hours, "预算产量标准工时")
    actual_h = require_nonnegative(actual_hours, "实际工时")
    allowed = require_nonnegative(standard_hours_allowed, "实际产量标准工时")
    rate = budget / denom
    applied = allowed * rate
    spending = actual - budget
    idle = (denom - actual_h) * rate
    efficiency = (actual_h - allowed) * rate
    total = actual - applied
    return {
        "rate": rate,
        "applied": applied,
        "spending": spending,
        "idle": idle,
        "efficiency": efficiency,
        "total": total,
    }


def fixed_overhead_three_variance_result(
    actual_fixed_overhead: float,
    budgeted_fixed_overhead: float,
    denominator_hours: float,
    actual_hours: float,
    standard_hours_allowed: float,
) -> CalcResult:
    """构建固定制造费用三差异分析结果。"""
    values = fixed_overhead_three_variance(
        actual_fixed_overhead,
        budgeted_fixed_overhead,
        denominator_hours,
        actual_hours,
        standard_hours_allowed,
    )
    result = CalcResult(
        MODULE,
        "标准成本差异——固定制造费用（三差异法）",
        {
            "实际固定制造费用": f"{money(actual_fixed_overhead)} 元",
            "预算固定制造费用": f"{money(budgeted_fixed_overhead)} 元",
            "预算产量标准工时": f"{denominator_hours:,.2f} 小时",
            "实际工时": f"{actual_hours:,.2f} 小时",
            "实际产量标准工时": f"{standard_hours_allowed:,.2f} 小时",
        },
    )
    result.add_step(f"标准分配率 = 预算固定制造费用/预算产量标准工时 = {money(values['rate'])} 元/小时。")
    result.add_step(f"耗费差异 = 实际数-预算数 = {_variance_text(values['spending'])}。")
    result.add_step(
        f"闲置能量差异 = (预算产量标准工时-实际工时)×标准分配率 = "
        f"{_variance_text(values['idle'])}。"
    )
    result.add_step(
        f"效率差异 = (实际工时-实际产量标准工时)×标准分配率 = "
        f"{_variance_text(values['efficiency'])}。"
    )
    result.add_step(
        f"三差异合计 = {_variance_text(values['spending'] + values['idle'] + values['efficiency'])}，"
        f"等于实际数减实际产量应负担额 {money(values['applied'])} 元的总差异。"
    )
    result.put("固定制造费用分配率", f"{money(values['rate'])} 元/小时")
    result.put("耗费差异", _variance_text(values["spending"]))
    result.put("闲置能量差异", _variance_text(values["idle"]))
    result.put("效率差异", _variance_text(values["efficiency"]))
    result.put("固定制造费用总差异", _variance_text(values["total"]))
    result.add_note("二差异法将闲置能量差异与效率差异合并为产量差异，三差异法将其进一步拆分。")
    return result


# ---------------------------------------------------------------------------
# 作业成本简易计算
# ---------------------------------------------------------------------------
def abc_cost(
    activities: Sequence[Dict[str, object]], products: Sequence[Dict[str, object]]
) -> CalcResult:
    """作业成本法简易分配。

    activities: [{"name":"设备调试","cost":60000,"driver_total":600}, ...]
    products: [{"name":"甲产品","output":5000,"usage":{"设备调试":200,...}}, ...]
    """
    if not activities:
        raise ValidationError("至少需要一个作业成本库。")
    if not products:
        raise ValidationError("至少需要一个产品。")
    activity_names: List[str] = []
    rates: Dict[str, float] = {}
    activity_rows = []
    for raw in activities:
        name = str(raw.get("name", "作业"))
        pool = require_nonnegative(raw.get("cost"), f"{name}成本库")
        driver_total = require_positive(raw.get("driver_total"), f"{name}成本动因总量")
        rate = pool / driver_total
        activity_names.append(name)
        rates[name] = rate
        activity_rows.append(
            {
                "作业成本库": name,
                "作业成本（元）": round(pool, 2),
                "成本动因总量": round(driver_total, 2),
                "作业分配率": round(rate, 4),
            }
        )

    product_rows = []
    detail_rows = []
    total_assigned_all = 0.0
    for raw in products:
        name = str(raw.get("name", "产品"))
        output = require_positive(raw.get("output"), f"{name}产量")
        usage_raw = raw.get("usage", {})
        if not isinstance(usage_raw, dict):
            raise ValidationError(f"{name}的作业耗用数据必须是字典。")
        assigned_total = 0.0
        row = {"产品": name, "产量": round(output, 2)}
        for activity in activity_names:
            usage = require_nonnegative(usage_raw.get(activity, 0), f"{name}-{activity}耗用量")
            assigned = rates[activity] * usage
            assigned_total += assigned
            row[activity] = round(assigned, 2)
            if assigned:
                detail_rows.append(
                    {
                        "产品": name,
                        "作业": activity,
                        "耗用量": round(usage, 2),
                        "分配率": round(rates[activity], 4),
                        "分配成本": round(assigned, 2),
                    }
                )
        total_assigned_all += assigned_total
        row["作业成本合计"] = round(assigned_total, 2)
        row["单位作业成本"] = round(assigned_total / output, 4)
        product_rows.append(row)

    result = CalcResult(
        MODULE,
        "作业成本法简易计算",
        {"作业中心数量": len(activity_names), "产品数量": len(products)},
    )
    result.add_step("对每个作业中心：作业分配率 = 作业成本库金额 ÷ 成本动因总量。")
    result.add_step("某产品某作业分配成本 = 该产品耗用成本动因量 × 作业分配率。")
    for row in activity_rows:
        result.add_step(
            f"{row['作业成本库']}分配率 = {row['作业成本（元）']:,.2f} ÷ "
            f"{row['成本动因总量']:,.2f} = {row['作业分配率']:.4f}。"
        )
    result.add_step(
        "各产品分别汇总作业成本，并除以产量得到单位作业成本。"
    )
    result.add_table("作业成本库及分配率", pd.DataFrame(activity_rows))
    result.add_table("产品作业成本汇总", pd.DataFrame(product_rows))
    result.add_table("产品作业耗用明细", pd.DataFrame(detail_rows))
    result.put("作业成本合计（已分配）", f"{money(total_assigned_all)} 元")
    result.add_note("作业成本法按成本动因分配间接费用，通常比单一人工工时分配更准确。")
    result.add_note("若各产品耗用动因合计小于成本库动因总量，未分配部分代表闲置作业能力。")
    return result


# ---------------------------------------------------------------------------
# 交互菜单与例题
# ---------------------------------------------------------------------------
def _interactive_cvp() -> CalcResult:
    price = ask_float("单价 P（元）", 100, min_value=0, allow_negative=False)
    variable = ask_float("单位变动成本 V（元）", 60, min_value=0, allow_negative=False)
    fixed = ask_float("固定成本 F（元）", 200000, min_value=0, allow_negative=False)
    quantity = ask_float("实际销售量 Q（件）", 10000, min_value=0, allow_negative=False)
    plot = ask_yes_no("是否绘制本量利图？", True)
    return cvp_analysis(price, variable, fixed, quantity, plot=plot)


def _interactive_material() -> CalcResult:
    return direct_material_result(
        ask_float("实际产量（件）", 1000, min_value=0, allow_negative=False),
        ask_float("单位标准材料用量（千克/件）", 2, min_value=0, allow_negative=False),
        ask_float("实际材料用量（千克）", 2100, min_value=0, allow_negative=False),
        ask_float("材料标准单价（元/千克）", 10, min_value=0, allow_negative=False),
        ask_float("材料实际单价（元/千克）", 9.8, min_value=0, allow_negative=False),
    )


def _interactive_labor() -> CalcResult:
    return direct_labor_result(
        ask_float("实际产量（件）", 1000, min_value=0, allow_negative=False),
        ask_float("单位标准工时（小时/件）", 2, min_value=0, allow_negative=False),
        ask_float("实际工时（小时）", 1950, min_value=0, allow_negative=False),
        ask_float("标准工资率（元/小时）", 20, min_value=0, allow_negative=False),
        ask_float("实际工资率（元/小时）", 21, min_value=0, allow_negative=False),
    )


def _interactive_variable_overhead() -> CalcResult:
    return variable_overhead_result(
        ask_float("实际产量（件）", 1000, min_value=0, allow_negative=False),
        ask_float("单位标准工时（小时/件）", 2, min_value=0, allow_negative=False),
        ask_float("实际工时（小时）", 1950, min_value=0, allow_negative=False),
        ask_float("标准分配率（元/小时）", 5, min_value=0, allow_negative=False),
        ask_float("实际分配率（元/小时）", 5.2, min_value=0, allow_negative=False),
    )


def _interactive_fixed_two() -> CalcResult:
    return fixed_overhead_two_variance_result(
        ask_float("实际固定制造费用（元）", 310000, min_value=0, allow_negative=False),
        ask_float("预算固定制造费用（元）", 300000, min_value=0, allow_negative=False),
        ask_float("预算产量标准工时（小时）", 5000, min_value=0, allow_negative=False),
        ask_float("实际产量标准工时（小时）", 4000, min_value=0, allow_negative=False),
    )


def _interactive_fixed_three() -> CalcResult:
    return fixed_overhead_three_variance_result(
        ask_float("实际固定制造费用（元）", 310000, min_value=0, allow_negative=False),
        ask_float("预算固定制造费用（元）", 300000, min_value=0, allow_negative=False),
        ask_float("预算产量标准工时（小时）", 5000, min_value=0, allow_negative=False),
        ask_float("实际工时（小时）", 4200, min_value=0, allow_negative=False),
        ask_float("实际产量标准工时（小时）", 4000, min_value=0, allow_negative=False),
    )


def _interactive_abc() -> CalcResult:
    count = ask_int("作业中心数量", 3, min_value=1, max_value=10)
    activity_defaults = [
        ("设备调试", 50000.0, 500.0, 100.0),
        ("质量检验", 30000.0, 1000.0, 200.0),
        ("材料搬运", 20000.0, 2000.0, 500.0),
    ]
    activities: List[Dict[str, object]] = []
    usages: Dict[str, float] = {}
    for index in range(count):
        default_name, default_cost, default_driver, default_usage = activity_defaults[
            min(index, len(activity_defaults) - 1)
        ]
        print(f"\n第 {index + 1} 个作业中心：")
        name = input(f"  作业名称 [{default_name}]：").strip() or default_name
        cost = ask_float("  作业成本库金额（元）", default_cost, min_value=0, allow_negative=False)
        driver = ask_float("  成本动因总量", default_driver, min_value=0, allow_negative=False)
        usage = ask_float("  本产品耗用成本动因量", default_usage, min_value=0, allow_negative=False)
        activities.append({"name": name, "cost": cost, "driver_total": driver})
        usages[name] = usage
    product_name = input("产品名称 [甲产品]：").strip() or "甲产品"
    output = ask_float("产品产量（件）", 10000, min_value=0, allow_negative=False)
    return abc_cost(
        activities,
        [{"name": product_name, "output": output, "usage": usages}],
    )


def _run_demo() -> None:
    """一键演示成本管理全部模型。"""
    print_heading("成本管理：全套例题一键演示", "★")
    show_result(cvp_analysis(100, 60, 200000, 10000, plot=True))
    show_result(direct_material_result(1000, 2, 2100, 10, 9.8))
    show_result(direct_labor_result(1000, 2, 1950, 20, 21))
    show_result(variable_overhead_result(1000, 2, 1950, 5, 5.2))
    show_result(fixed_overhead_two_variance_result(310000, 300000, 5000, 4000))
    show_result(fixed_overhead_three_variance_result(310000, 300000, 5000, 4200, 4000))
    show_result(
        abc_cost(
            [
                {"name": "设备调试", "cost": 60000, "driver_total": 600},
                {"name": "质量检验", "cost": 40000, "driver_total": 1000},
                {"name": "材料搬运", "cost": 30000, "driver_total": 3000},
            ],
            [
                {"name": "甲产品", "output": 5000, "usage": {"设备调试": 200, "质量检验": 300, "材料搬运": 1000}},
                {"name": "乙产品", "output": 8000, "usage": {"设备调试": 400, "质量检验": 700, "材料搬运": 2000}},
            ],
        )
    )
    print("\n[演示完成] 已覆盖本量利、四类标准成本差异和作业成本法。")


def run() -> None:
    """模块 7 控制台菜单。"""
    while True:
        print_heading("模块7 成本管理（本量利 / 标准成本 / 作业成本）")
        print("  1. 本量利分析（含敏感系数与本量利图）")
        print("  2. 标准成本差异——直接材料")
        print("  3. 标准成本差异——直接人工")
        print("  4. 标准成本差异——变动制造费用")
        print("  5. 固定制造费用二差异分析")
        print("  6. 固定制造费用三差异分析")
        print("  7. 作业成本法简易计算")
        print("  8. 全套例题一键演示")
        print("  0. 返回主菜单")
        try:
            choice = input("请选择功能：").strip()
        except EOFError:
            return
        if choice == "0":
            return
        actions = {
            "1": _interactive_cvp,
            "2": _interactive_material,
            "3": _interactive_labor,
            "4": _interactive_variable_overhead,
            "5": _interactive_fixed_two,
            "6": _interactive_fixed_three,
            "7": _interactive_abc,
        }
        if choice == "8":
            _run_demo()
            pause()
        elif choice in actions:
            run_calculation(actions[choice])
            pause()
        else:
            print("[提示] 无效选项，请输入 0~8。")
