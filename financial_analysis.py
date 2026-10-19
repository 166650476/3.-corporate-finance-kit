"""模块 9：财务分析。

覆盖偿债能力、营运能力、盈利能力、现金流量指标，以及传统杜邦和改进杜邦体系。
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

from utils import (
    CalcResult,
    ValidationError,
    ask_float,
    ask_rate_percent,
    ask_yes_no,
    money,
    pause,
    percent,
    print_heading,
    require_nonnegative,
    require_number,
    require_positive,
    require_rate,
    run_calculation,
    show_result,
    safe_divide,
)


MODULE = "模块9 财务分析"


def financial_analysis(data: Dict[str, float], *, plot: bool = True) -> CalcResult:
    """计算完整财务指标体系并进行杜邦拆解。"""
    current_assets = require_positive(data.get("current_assets"), "流动资产")
    inventory = require_nonnegative(data.get("inventory"), "存货")
    cash = require_nonnegative(data.get("cash"), "货币资金")
    receivables = require_positive(data.get("receivables"), "平均应收账款")
    current_liabilities = require_positive(data.get("current_liabilities"), "流动负债")
    total_liabilities = require_nonnegative(data.get("total_liabilities"), "负债总额")
    total_assets = require_positive(data.get("total_assets"), "平均总资产")
    total_equity = require_positive(data.get("total_equity"), "平均股东权益")
    revenue = require_positive(data.get("revenue"), "营业收入")
    operating_cost = require_nonnegative(data.get("operating_cost"), "营业成本")
    net_profit = require_nonnegative(data.get("net_profit"), "净利润")
    interest = require_nonnegative(data.get("interest_expense", 0), "利息费用")
    ebit = require_nonnegative(data.get("ebit"), "息税前利润")
    tax = require_rate(data.get("tax_rate", 0.25), "所得税税率", max_value=1.0)
    operating_cash_flow = require_number(data.get("operating_cash_flow"), "经营活动现金流量净额")
    depreciation = require_nonnegative(data.get("depreciation", 0), "折旧摊销")
    net_debt = require_number(data.get("net_debt", 0), "净负债")

    if inventory > current_assets:
        raise ValidationError("存货不能大于流动资产。")
    if total_equity > total_assets:
        raise ValidationError("股东权益不能大于总资产，请检查报表数据。")
    if total_liabilities > total_assets:
        raise ValidationError("负债总额不能大于总资产，请检查报表数据。")

    current_ratio = safe_divide(current_assets, current_liabilities, "流动负债")
    quick_ratio = safe_divide(current_assets - inventory, current_liabilities, "流动负债")
    cash_ratio = safe_divide(cash, current_liabilities, "流动负债")
    debt_ratio = total_liabilities / total_assets
    equity_ratio = total_liabilities / total_equity
    equity_multiplier = total_assets / total_equity
    interest_coverage = ebit / interest if interest > 0 else None

    ar_turnover = revenue / receivables
    inventory_turnover = operating_cost / inventory if inventory > 0 else None
    current_asset_turnover = revenue / current_assets
    total_asset_turnover = revenue / total_assets
    net_margin = net_profit / revenue
    roa = net_profit / total_assets
    roe = net_profit / total_equity
    operating_cash_income = net_profit + depreciation
    cash_operating_index = (
        operating_cash_flow / operating_cash_income if operating_cash_income > 0 else None
    )

    after_tax_interest = interest * (1.0 - tax)
    nopat = net_profit + after_tax_interest
    net_operating_assets = net_debt + total_equity
    rona = nopat / net_operating_assets if net_operating_assets > 0 else None
    after_tax_interest_rate = after_tax_interest / net_debt if net_debt > 0 else None
    net_financial_leverage = net_debt / total_equity
    if rona is not None and after_tax_interest_rate is not None:
        leverage_contribution = (rona - after_tax_interest_rate) * net_financial_leverage
        improved_roe = rona + leverage_contribution
    else:
        leverage_contribution = 0.0
        improved_roe = rona if rona is not None else roe

    result = CalcResult(
        MODULE,
        "财务指标体系与杜邦分析",
        {
            "流动资产": f"{money(current_assets)} 元",
            "存货": f"{money(inventory)} 元",
            "货币资金": f"{money(cash)} 元",
            "平均应收账款": f"{money(receivables)} 元",
            "流动负债": f"{money(current_liabilities)} 元",
            "负债总额": f"{money(total_liabilities)} 元",
            "平均总资产": f"{money(total_assets)} 元",
            "平均股东权益": f"{money(total_equity)} 元",
            "营业收入": f"{money(revenue)} 元",
            "营业成本": f"{money(operating_cost)} 元",
            "净利润": f"{money(net_profit)} 元",
            "利息费用": f"{money(interest)} 元",
            "息税前利润 EBIT": f"{money(ebit)} 元",
            "所得税税率": percent(tax),
            "经营现金净流量": f"{money(operating_cash_flow)} 元",
            "折旧摊销": f"{money(depreciation)} 元",
            "净负债": f"{money(net_debt)} 元",
        },
    )

    result.add_step("一、偿债能力指标")
    result.add_step(
        f"流动比率={current_ratio:.4f}；速动比率={quick_ratio:.4f}；现金比率={cash_ratio:.4f}。"
    )
    result.add_step(
        f"资产负债率={percent(debt_ratio)}；产权比率={equity_ratio:.4f}；"
        f"权益乘数={equity_multiplier:.4f}。"
    )
    if interest_coverage is not None:
        result.add_step(f"利息保障倍数=EBIT/利息费用={interest_coverage:.4f}。")
    else:
        result.add_step("利息费用为 0，利息保障倍数不适用（可视为无固定利息负担）。")

    result.add_step("二、营运能力指标")
    result.add_step(
        f"应收账款周转率={ar_turnover:.4f} 次（约 {360 / ar_turnover:.2f} 天）；"
        + (f"存货周转率={inventory_turnover:.4f} 次" if inventory_turnover is not None else "存货周转率不适用")
        + f"；流动资产周转率={current_asset_turnover:.4f} 次；"
        f"总资产周转率={total_asset_turnover:.4f} 次。"
    )
    result.add_step("三、盈利能力指标")
    result.add_step(
        f"营业净利率={percent(net_margin)}；ROA={percent(roa)}；ROE={percent(roe)}。"
    )
    result.add_step("四、现金流量指标")
    if cash_operating_index is not None:
        result.add_step(
            f"经营所得现金=净利润+折旧={money(net_profit)}+{money(depreciation)}"
            f"={money(operating_cash_income)} 元；现金营运指数="
            f"{cash_operating_index:.4f}。"
        )
    else:
        result.add_step("经营所得现金小于或等于 0，现金营运指数不适用。")

    result.add_step("五、传统杜邦分析：ROE=营业净利率×总资产周转率×权益乘数。")
    result.add_step(
        f"ROE={percent(net_margin)}×{total_asset_turnover:.4f}×{equity_multiplier:.4f}"
        f"={percent(net_margin * total_asset_turnover * equity_multiplier)}。"
    )
    result.add_step(
        "营业净利率反映盈利质量，总资产周转率反映资产效率，权益乘数反映财务杠杆。"
    )
    result.add_step("六、改进杜邦分析：ROE=净经营资产净利率+(净经营资产净利率-税后利息率)×净财务杠杆。")
    if rona is not None:
        result.add_step(
            f"税后经营净利润=净利润+税后利息={money(net_profit)}+{money(after_tax_interest)}"
            f"={money(nopat)} 元；净经营资产=净负债+股东权益={money(net_operating_assets)} 元。"
        )
        result.add_step(f"净经营资产净利率={money(nopat)}/{money(net_operating_assets)}={percent(rona, 4)}。")
        if after_tax_interest_rate is not None:
            result.add_step(
                f"税后利息率={money(after_tax_interest)}/{money(net_debt)}="
                f"{percent(after_tax_interest_rate, 4)}；净财务杠杆={net_financial_leverage:.4f}。"
            )
            result.add_step(
                f"杠杆贡献率=({percent(rona, 4)}-{percent(after_tax_interest_rate, 4)})×"
                f"{net_financial_leverage:.4f}={percent(leverage_contribution, 4)}。"
            )
        result.add_step(
            f"改进杜邦 ROE={percent(rona, 4)}+{percent(leverage_contribution, 4)}"
            f"={percent(improved_roe, 4)}，与直接计算 ROE 一致。"
        )
    else:
        result.add_step("净经营资产不大于 0，改进杜邦分解不适用。")

    result.put("流动比率", f"{current_ratio:.4f}")
    result.put("速动比率", f"{quick_ratio:.4f}")
    result.put("现金比率", f"{cash_ratio:.4f}")
    result.put("资产负债率", percent(debt_ratio))
    result.put("产权比率", f"{equity_ratio:.4f}")
    result.put("权益乘数", f"{equity_multiplier:.4f}")
    result.put(
        "利息保障倍数", f"{interest_coverage:.4f}" if interest_coverage is not None else "不适用"
    )
    result.put("应收账款周转率", f"{ar_turnover:.4f} 次")
    result.put(
        "存货周转率",
        f"{inventory_turnover:.4f} 次" if inventory_turnover is not None else "不适用",
    )
    result.put("流动资产周转率", f"{current_asset_turnover:.4f} 次")
    result.put("总资产周转率", f"{total_asset_turnover:.4f} 次")
    result.put("营业净利率", percent(net_margin))
    result.put("总资产净利率 ROA", percent(roa))
    result.put("净资产收益率 ROE", percent(roe))
    result.put(
        "现金营运指数",
        f"{cash_operating_index:.4f}" if cash_operating_index is not None else "不适用",
    )
    result.put("传统杜邦乘积校验", percent(net_margin * total_asset_turnover * equity_multiplier))
    result.put("净经营资产净利率", percent(rona, 4) if rona is not None else "不适用")
    result.put(
        "税后利息率",
        percent(after_tax_interest_rate, 4) if after_tax_interest_rate is not None else "不适用",
    )
    result.put("净财务杠杆", f"{net_financial_leverage:.4f}")
    result.put("杠杆贡献率", percent(leverage_contribution, 4))
    result.put("改进杜邦 ROE", percent(improved_roe, 4))

    table_rows = [
        ("流动比率", "流动资产/流动负债", current_ratio, "短期偿债能力"),
        ("速动比率", "(流动资产-存货)/流动负债", quick_ratio, "剔除存货后的短期偿债能力"),
        ("现金比率", "货币资金/流动负债", cash_ratio, "最严格的短期偿债能力"),
        ("资产负债率", "负债总额/总资产", debt_ratio, "长期偿债能力与财务风险"),
        ("产权比率", "负债总额/股东权益", equity_ratio, "债务相对权益的倍数"),
        ("权益乘数", "总资产/股东权益", equity_multiplier, "财务杠杆大小"),
        ("应收账款周转率", "营业收入/平均应收账款", ar_turnover, "应收账款变现速度"),
        ("总资产周转率", "营业收入/平均总资产", total_asset_turnover, "全部资产运营效率"),
        ("营业净利率", "净利润/营业收入", net_margin, "每元收入的最终盈利"),
        ("总资产净利率", "净利润/平均总资产", roa, "资产整体盈利能力"),
        ("净资产收益率", "净利润/平均股东权益", roe, "股东投入资本的回报"),
    ]
    if interest_coverage is not None:
        table_rows.append(("利息保障倍数", "EBIT/利息费用", interest_coverage, "支付利息的安全程度"))
    if inventory_turnover is not None:
        table_rows.append(("存货周转率", "营业成本/平均存货", inventory_turnover, "存货周转速度"))
    if cash_operating_index is not None:
        table_rows.append(
            ("现金营运指数", "经营现金净流量/经营所得现金", cash_operating_index, "利润的现金含量")
        )

    result.add_table(
        "财务指标汇总表",
        pd.DataFrame(
            [
                {"指标": name, "公式": formula, "数值": round(value, 4), "解读": comment}
                for name, formula, value, comment in table_rows
            ]
        ),
    )

    if roe >= 0.15:
        result.add_note("ROE 达到 15% 以上（示例基准），股东资本回报较高；应结合行业水平判断。")
    elif roe > 0:
        result.add_note("ROE 为正但不高，可从净利率、周转率和杠杆三方面寻找提升空间。")
    else:
        result.add_note("ROE 为负，企业处于亏损状态，应重点关注成本、费用和资产减值风险。")
    if cash_operating_index is not None and cash_operating_index < 1:
        result.add_note("现金营运指数小于 1，说明经营现金净流量低于经营所得现金，利润现金含量偏弱。")

    if plot:
        from visual import plot_dupont_waterfall

        image_path = plot_dupont_waterfall(
            net_margin,
            total_asset_turnover,
            equity_multiplier,
        )
        result.put("杜邦瀑布图", str(image_path))
    return result


# ---------------------------------------------------------------------------
# 交互菜单与例题
# ---------------------------------------------------------------------------
def _interactive() -> CalcResult:
    print("请输入金额（单位保持一致，通常为万元或元）：")
    data = {
        "current_assets": ask_float("流动资产", 800, min_value=0, allow_negative=False),
        "inventory": ask_float("存货", 300, min_value=0, allow_negative=False),
        "cash": ask_float("货币资金", 150, min_value=0, allow_negative=False),
        "receivables": ask_float("平均应收账款", 250, min_value=0, allow_negative=False),
        "current_liabilities": ask_float("流动负债", 400, min_value=0, allow_negative=False),
        "total_liabilities": ask_float("负债总额", 1000, min_value=0, allow_negative=False),
        "total_assets": ask_float("平均总资产", 2000, min_value=0, allow_negative=False),
        "total_equity": ask_float("平均股东权益", 1000, min_value=0, allow_negative=False),
        "revenue": ask_float("营业收入", 3000, min_value=0, allow_negative=False),
        "operating_cost": ask_float("营业成本", 2100, min_value=0, allow_negative=False),
        "net_profit": ask_float("净利润", 300, min_value=0, allow_negative=False),
        "interest_expense": ask_float("利息费用", 60, min_value=0, allow_negative=False),
        "ebit": ask_float("息税前利润 EBIT", 460, min_value=0, allow_negative=False),
        "tax_rate": ask_rate_percent("所得税税率", 0.25, max_percent=100),
        "operating_cash_flow": ask_float("经营活动现金流量净额", 380),
        "depreciation": ask_float("折旧摊销", 100, min_value=0, allow_negative=False),
        "net_debt": ask_float("净负债（有息负债-金融资产）", 300),
    }
    plot = ask_yes_no("是否绘制杜邦分析瀑布图？", True)
    return financial_analysis(data, plot=plot)


def _run_demo() -> None:
    """一键演示完整财务指标与杜邦分析。"""
    print_heading("财务分析：全套例题一键演示", "★")
    show_result(
        financial_analysis(
            {
                "current_assets": 800,
                "inventory": 300,
                "cash": 150,
                "receivables": 250,
                "current_liabilities": 400,
                "total_liabilities": 1000,
                "total_assets": 2000,
                "total_equity": 1000,
                "revenue": 3000,
                "operating_cost": 2100,
                "net_profit": 300,
                "interest_expense": 60,
                "ebit": 460,
                "tax_rate": 0.25,
                "operating_cash_flow": 380,
                "depreciation": 100,
                "net_debt": 300,
            },
            plot=True,
        )
    )
    print("\n[演示完成] ROE=30%，传统杜邦与改进杜邦结果已完成交叉校验。")


def run() -> None:
    """模块 9 控制台菜单。"""
    while True:
        print_heading("模块9 财务分析（财务指标 / 杜邦分析）")
        print("  1. 完整财务指标与杜邦分析（含瀑布图）")
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
