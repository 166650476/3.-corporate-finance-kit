"""项目自动自检脚本。

运行：python selftest.py
不进入交互菜单，直接调用 12 个模块的核心函数进行数值校验，
并验证 CSV 导出和 matplotlib 中文绘图是否正常。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")


PASSED = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    """记录一项断言。"""
    global PASSED
    if not condition:
        raise AssertionError(f"自检失败：{name}。{detail}")
    PASSED += 1
    print(f"  [通过] {name}")


def close(actual: float, expected: float, tolerance: float = 1e-6) -> bool:
    return abs(actual - expected) <= tolerance * max(1.0, abs(expected))


def main() -> None:
    """依次验证全部模块。"""
    print("=" * 72)
    print("finance-calculator 项目自检")
    print("=" * 72)

    import time_value as tv
    import project_invest as pi
    import capital_cost as cc
    import leverage as lv
    import capital_structure as cs
    import working_capital as wc
    import cost_analysis as ca
    import securities_valuation as sv
    import financial_analysis as fa
    import dividend_policy as dp
    import option_valuation as ov
    import financial_budget as fb
    import visual
    import export
    from utils import CalcResult

    print("\n[1/12] 资金时间价值")
    check("复利终值", close(tv.compound_future_value(100000, 0.08, 5), 146932.80768, 1e-8))
    check("复利现值互逆", close(tv.compound_present_value(146932.80768, 0.08, 5), 100000, 1e-8))
    check("普通年金终值", close(tv.ordinary_annuity_future_value(10000, 0.06, 5), 56370.92, 1e-4))
    check(
        "预付年金终值关系",
        close(
            tv.annuity_due_future_value(10000, 0.06, 5),
            tv.ordinary_annuity_future_value(10000, 0.06, 5) * 1.06,
            1e-10,
        ),
    )
    check("永续年金现值", close(tv.perpetuity_present_value(8000, 0.05), 160000, 1e-10))
    interp = tv.interpolate_discount_rate([-10000, 2500, 2500, 2500, 2500, 2500], 0.07, 0.09)
    check("内插法输出结果", "内插法折现率 i" in interp.outcomes)

    print("\n[2/12] 项目投资管理")
    cash_flows = [280000, 300000, 320000, 300000, 280000]
    npv_value = pi.npv(0.10, 1000000, cash_flows)
    irr_value = pi.irr(1000000, cash_flows)
    check("NPV 计算", npv_value > 0, f"NPV={npv_value}")
    check("IRR > 必要报酬率", irr_value > 0.10, f"IRR={irr_value}")
    check("PI > 1", pi.profitability_index(0.10, 1000000, cash_flows) > 1)
    check("静态回收期", 3 < pi.static_payback_period(1000000, cash_flows) < 4)
    comparison = pi.compare_projects(
        [
            {"name": "A", "initial": 1000000, "cash_flows": cash_flows},
            {"name": "B", "initial": 500000, "cash_flows": [220000, 240000, 260000]},
        ],
        0.10,
    )
    check("年限不同自动使用 ANCF", "年限不同" in str(comparison.outcomes["比选方法"]))

    print("\n[3/12] 资本成本")
    check("CAPM", close(cc.capm_required_return(0.03, 1.2, 0.09), 0.102, 1e-10))
    check("债务一般模式", close(cc.debt_cost_general(80, 1000, 0.25, 0.02), 0.0612244898, 1e-8))
    after_tax, before_tax = cc.debt_cost_discount(1000, 0.08, 5, 1050, 0.25, 0.02)
    check("债务贴现模式", 0 < after_tax < before_tax < 0.15, f"{after_tax=}, {before_tax=}")
    check("普通股股利增长模型", cc.equity_cost_dividend_growth(1.2, 20, 0.05, 0.03) > 0.10)
    check("WACC", close(cc.wacc([0.4, 0.6], [0.06, 0.12]), 0.096, 1e-10))

    print("\n[4/12] 杠杆原理")
    dol, contribution, ebit = lv.degree_operating_leverage(10000, 100, 60, 200000)
    dfl = lv.degree_financial_leverage(ebit, 50000)
    check("DOL", close(dol, 2.0, 1e-10))
    check("DFL", close(dfl, 4 / 3, 1e-10))
    check("DTL", close(lv.degree_total_leverage(dol, dfl), 8 / 3, 1e-10))

    print("\n[5/12] 资本结构")
    point, point_eps = cs.eps_indifference_point(
        {"interest": 0, "preferred_dividend": 0, "shares": 1000000},
        {"interest": 400000, "preferred_dividend": 0, "shares": 700000},
        0.25,
    )
    check("EPS 无差别点", close(point, 1333333.3333333333, 1e-9), f"EBIT*={point}")
    check("无差别点 EPS", close(point_eps, 1.0, 1e-9))
    company = cs.company_value_analysis(
        2000000,
        0.25,
        [
            {"name": "无负债", "debt": 0, "debt_cost": 0.06, "equity_cost": 0.10},
            {"name": "负债500万", "debt": 5000000, "debt_cost": 0.06, "equity_cost": 0.11},
        ],
    )
    check("公司价值分析推荐", "推荐资本结构" in company.outcomes)

    print("\n[6/12] 营运资金管理")
    optimal_cash, total_cost, _, _ = wc.baumol_cash_model(3600000, 1000, 0.08)
    check("Baumol 最佳现金", close(optimal_cash, 300000, 1e-8))
    check("Baumol 总成本", close(total_cost, 24000, 1e-8))
    return_point, upper, _ = wc.miller_orr_model(1000, 2000, 0.0002, 10000)
    check("Miller-Orr 控制线", upper > return_point > 10000)
    check("应收账款机会成本", wc.ar_opportunity_cost(12000000, 45, 0.6, 0.10)[1] > 0)
    eoq, eoq_cost, _ = wc.eoq_basic(36000, 500, 10)
    check("EOQ", close(eoq, 1897.366599, 1e-5))
    check("EOQ 总成本", close(eoq_cost, 18973.66599, 1e-4))
    check("陆续供货批量大于瞬时到货", wc.eoq_gradual(36000, 500, 10, 200, 100)[0] > eoq)
    check("保险储备", close(wc.safety_stock(1.65, 100, 4), 330.0, 1e-10))

    print("\n[7/12] 成本管理")
    cvp = ca.cvp_analysis(100, 60, 200000, 10000)
    check("CVP 保本点", "5,000.00 件" in cvp.outcomes["盈亏临界点销售量"])
    dm = ca.direct_material_variances(1000, 2, 2100, 10, 9.8)
    check(
        "材料差异合计",
        close(dm["price_variance"] + dm["quantity_variance"], dm["total_variance"], 1e-10),
    )
    foh = ca.fixed_overhead_three_variance(310000, 300000, 5000, 4200, 4000)
    check(
        "固定制造费用三差异合计",
        close(foh["spending"] + foh["idle"] + foh["efficiency"], foh["total"], 1e-10),
    )

    print("\n[8/12] 证券估值")
    bond = sv.bond_value(1000, 0.08, 5, 0.10)
    check("债券价值", close(bond, 924.18426, 1e-4), f"V={bond}")
    ytm = sv.bond_ytm(950, 1000, 0.08, 5)
    check("债券 YTM", 0.08 < ytm < 0.12, f"YTM={ytm}")
    check("固定增长股票价值", close(sv.constant_growth_stock_value(1.2, 0.10, 0.05), 25.2, 1e-10))

    print("\n[9/12] 财务分析")
    analysis = fa.financial_analysis(
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
        plot=False,
    )
    check("传统杜邦 ROE", "30.00%" in analysis.outcomes["净资产收益率 ROE"])
    check("改进杜邦 ROE", "30.0000%" in analysis.outcomes["改进杜邦 ROE"])

    print("\n[10/12] 股利分配")
    residual = dp.residual_dividend_result(2000000, 0.50, 2000000, 1000000)
    check("剩余股利", "1,000,000.00 元" in residual.outcomes["股利总额"])
    split = dp.stock_split_result(1000000, 2, 20, 2000000)
    check("股票分割股价", "10.0000 元/股" in split.outcomes["理论分割后股价"])

    print("\n[11/12] 期权估值")
    check("看涨期权到期价值", close(ov.option_payoff("call", 38, 40), 0, 1e-12))
    check("看跌期权到期价值", close(ov.option_payoff("put", 38, 40), 2, 1e-12))
    binomial = ov.binomial_replication(50, 60, 40, 50, 0.05, "call")
    check("复制原理期权价值", close(binomial["option_value"], 5.95238095, 1e-7))
    check(
        "风险中性定价一致",
        close(binomial["option_value"], binomial["risk_neutral_value"], 1e-10),
    )

    print("\n[12/12] 财务预算与通用功能")
    budget_result = fb.integrated_budget_result(fb._default_budget_data())
    check("预算七张表", len(budget_result.tables) == 7)
    check("预算期末现金", "期末现金余额" in budget_result.outcomes)

    image1 = visual.plot_cash_flow([-100000, 30000, 35000, 40000], "自检现金流图")
    image2 = visual.plot_cvp(100, 60, 200000, 10000)
    image3 = visual.plot_dupont_waterfall(0.10, 1.5, 2.0)
    check("现金流时间轴图片", image1.exists() and image1.stat().st_size > 0)
    check("本量利图", image2.exists() and image2.stat().st_size > 0)
    check("杜邦瀑布图", image3.exists() and image3.stat().st_size > 0)

    original_path = export.RESULT_FILE
    with tempfile.TemporaryDirectory() as temp_dir:
        export.RESULT_FILE = Path(temp_dir) / "test_result.csv"
        result = CalcResult("自检", "CSV导出测试", {"x": 1}, ["步骤"], {"y": 2})
        export.append_result(result)
        export.append_batch([result, result])
        content = export.RESULT_FILE.read_text(encoding="utf-8-sig")
        check("CSV 导出", "CSV导出测试" in content and content.count("CSV导出测试") == 3)
    export.RESULT_FILE = original_path

    print("\n" + "=" * 72)
    print(f"全部自检通过：共 {PASSED} 项。")
    print("提示：可直接运行 python main.py 进入交互菜单。")
    print("=" * 72)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[自检失败] {exc}")
        raise
