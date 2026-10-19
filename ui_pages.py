"""Streamlit 各模块页面。

每个页面只负责收集输入并调用对应核心模块，计算步骤、导出和展示由 ui_core 统一处理。
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
import streamlit as st

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
from ui_core import (
    calculate_and_store,
    demo_button,
    page_header,
    parse_series,
    render_saved,
)


# ---------------------------------------------------------------------------
# 输入控件封装
# ---------------------------------------------------------------------------
def money_input(
    label: str,
    value: float,
    key: str,
    *,
    step: float = 1000.0,
    allow_negative: bool = False,
    help_text: str = "",
) -> float:
    """金额输入。"""
    return float(
        st.number_input(
            label,
            value=float(value),
            step=float(step),
            min_value=None if allow_negative else 0.0,
            format="%.2f",
            key=key,
            help=help_text or None,
        )
    )


def decimal_input(
    label: str,
    value: float,
    key: str,
    *,
    step: float = 0.01,
    help_text: str = "",
) -> float:
    """普通小数/数量输入。"""
    return float(
        st.number_input(
            label,
            value=float(value),
            step=float(step),
            min_value=0.0,
            format="%.4f",
            key=key,
            help=help_text or None,
        )
    )


def rate_input(
    label: str,
    value_percent: float,
    key: str,
    *,
    step: float = 0.1,
    allow_negative: bool = False,
    max_value: float = 1000.0,
    help_text: str = "",
) -> float:
    """按百分数录入，返回小数。"""
    value = st.number_input(
        f"{label}（%）",
        value=float(value_percent),
        step=float(step),
        min_value=-100.0 if allow_negative else 0.0,
        max_value=float(max_value),
        format="%.4f",
        key=key,
        help=help_text or None,
    )
    return float(value) / 100.0


def integer_input(
    label: str, value: int, key: str, *, minimum: int = 1, maximum: int = 1000
) -> int:
    """整数输入。"""
    return int(
        st.number_input(
            label,
            value=int(value),
            step=1,
            min_value=int(minimum),
            max_value=int(maximum),
            key=key,
        )
    )


def series_text(label: str, value: str, key: str, *, help_text: str = "") -> str:
    """逗号分隔序列输入。"""
    return st.text_input(label, value=value, key=key, help=help_text or None)


def primary_button() -> bool:
    """表单主按钮。"""
    return st.form_submit_button(
        "开始计算",
        type="primary",
        icon=":material/calculate:",
        width="stretch",
    )


# ---------------------------------------------------------------------------
# 模块 1：资金时间价值
# ---------------------------------------------------------------------------
TV_TYPES = [
    "复利终值",
    "复利现值",
    "普通年金终值",
    "普通年金现值",
    "预付年金终值",
    "预付年金现值",
    "递延年金现值和终值",
    "永续年金现值",
    "内插法求折现率",
    "现金流时间轴与净现值",
]


def _tv_demo(kind: str):
    if kind == "复利终值":
        return tv.compound_fv_result(100000, 0.08, 5)
    if kind == "复利现值":
        return tv.compound_pv_result(146932.81, 0.08, 5)
    if kind == "普通年金终值":
        return tv.annuity_result(10000, 0.06, 5, due=False, value_type="FV")
    if kind == "普通年金现值":
        return tv.annuity_result(10000, 0.06, 5, due=False, value_type="PV")
    if kind == "预付年金终值":
        return tv.annuity_result(10000, 0.06, 5, due=True, value_type="FV")
    if kind == "预付年金现值":
        return tv.annuity_result(10000, 0.06, 5, due=True, value_type="PV")
    if kind == "递延年金现值和终值":
        return tv.deferred_result(10000, 0.08, 5, 3)
    if kind == "永续年金现值":
        return tv.perpetuity_result(8000, 0.05)
    if kind == "内插法求折现率":
        return tv.interpolate_discount_rate(
            [-10000, 2500, 2500, 2500, 2500, 2500], 0.07, 0.09
        )
    return tv.cash_flow_timeline_result(
        [-100000, 30000, 35000, 40000, 45000], 0.10, "项目现金流时间轴"
    )


def page_time_value() -> None:
    page_header(
        "1",
        "资金时间价值",
        "复利、普通年金、预付年金、递延年金、永续年金和内插法。比率按百分数输入。",
    )
    kind = st.selectbox("计算类型", TV_TYPES, key="tv_kind")
    with st.form("tv_form"):
        builder = None
        if kind == "复利终值":
            present = money_input("复利现值 P（元）", 100000, "tv_p")
            rate = rate_input("年利率", 8.0, "tv_rate_fv")
            periods = integer_input("期数 n（年）", 5, "tv_n_fv")
            builder = lambda: tv.compound_fv_result(present, rate, periods)
        elif kind == "复利现值":
            future = money_input("复利终值 F（元）", 146932.81, "tv_f")
            rate = rate_input("年利率", 8.0, "tv_rate_pv")
            periods = integer_input("期数 n（年）", 5, "tv_n_pv")
            builder = lambda: tv.compound_pv_result(future, rate, periods)
        elif kind in {"普通年金终值", "普通年金现值", "预付年金终值", "预付年金现值"}:
            payment = money_input("每期年金 A（元）", 10000, "tv_annuity")
            rate = rate_input("每期利率", 6.0, "tv_rate_annuity")
            periods = integer_input("收付期数 n", 5, "tv_n_annuity")
            due = kind.startswith("预付")
            value_type = "FV" if "终值" in kind else "PV"
            builder = lambda: tv.annuity_result(
                payment, rate, periods, due=due, value_type=value_type
            )
        elif kind == "递延年金现值和终值":
            payment = money_input("每期年金 A（元）", 10000, "tv_def_payment")
            rate = rate_input("年利率", 8.0, "tv_def_rate")
            periods = integer_input("连续收付期数 n", 5, "tv_def_n")
            deferred = integer_input("递延期数 m", 3, "tv_def_m", minimum=0)
            builder = lambda: tv.deferred_result(payment, rate, periods, deferred)
        elif kind == "永续年金现值":
            payment = money_input("每期永续年金 A（元）", 8000, "tv_perp_payment")
            rate = rate_input("折现率", 5.0, "tv_perp_rate")
            builder = lambda: tv.perpetuity_result(payment, rate)
        elif kind == "内插法求折现率":
            flows = series_text(
                "现金流量（t=0 起，流出为负）",
                "-10000,2500,2500,2500,2500,2500",
                "tv_interp_flows",
            )
            low = rate_input("较低测试折现率 i1", 7.0, "tv_interp_low")
            high = rate_input("较高测试折现率 i2", 9.0, "tv_interp_high")
            builder = lambda: tv.interpolate_discount_rate(
                parse_series(flows, "现金流量", min_length=2), low, high
            )
        else:
            flows = series_text(
                "现金流量（t=0 起，流出为负）",
                "-100000,30000,35000,40000,45000",
                "tv_timeline_flows",
            )
            rate = rate_input("折现率", 10.0, "tv_timeline_rate")
            title = st.text_input("图表标题", value="项目现金流时间轴", key="tv_timeline_title")
            builder = lambda: tv.cash_flow_timeline_result(
                parse_series(flows, "现金流量"), rate, title
            )
        submitted = primary_button()
    if submitted and builder is not None:
        calculate_and_store("tv_result", builder)
    demo_button("tv_result", lambda: _tv_demo(kind))
    render_saved("tv_result")


# ---------------------------------------------------------------------------
# 模块 2：项目投资管理
# ---------------------------------------------------------------------------
PROJECT_TYPES = ["项目全面评价", "互斥方案比选"]


def page_project() -> None:
    page_header(
        "2",
        "项目投资管理",
        "计算 NPV、IRR、PI、ANCF、回收期，并在年限相同/不同方案之间做互斥决策。",
    )
    kind = st.selectbox("计算类型", PROJECT_TYPES, key="pi_kind")
    with st.form("pi_form"):
        if kind == "项目全面评价":
            left, right = st.columns([1, 1])
            with left:
                name = st.text_input("项目名称", value="A项目", key="pi_name")
                initial = money_input("初始投资（元）", 1000000, "pi_initial")
            with right:
                flows_text = series_text(
                    "第 1~n 年净现金流量（元）",
                    "280000,300000,320000,300000,280000",
                    "pi_flows",
                )
                rate = rate_input("必要报酬率", 10.0, "pi_rate")
            plot = st.checkbox("绘制现金流时间轴", value=True, key="pi_plot")
            builder = lambda: pi.project_appraisal_result(
                initial,
                parse_series(flows_text, "净现金流量"),
                rate,
                project_name=name,
                plot=plot,
            )
        else:
            rate = rate_input("统一必要报酬率", 10.0, "pi_compare_rate")
            first_col, second_col = st.columns(2)
            with first_col:
                st.markdown("**方案 A**")
                name_a = st.text_input("方案 A 名称", value="A方案", key="pi_name_a")
                initial_a = money_input("方案 A 初始投资（元）", 1000000, "pi_initial_a")
                flows_a = series_text(
                    "方案 A 年净现金流量",
                    "280000,300000,320000,300000,280000",
                    "pi_flows_a",
                )
            with second_col:
                st.markdown("**方案 B**")
                name_b = st.text_input("方案 B 名称", value="B方案", key="pi_name_b")
                initial_b = money_input("方案 B 初始投资（元）", 900000, "pi_initial_b")
                flows_b = series_text(
                    "方案 B 年净现金流量",
                    "250000,280000,300000,280000,250000",
                    "pi_flows_b",
                )
            builder = lambda: pi.compare_projects(
                [
                    {
                        "name": name_a,
                        "initial": initial_a,
                        "cash_flows": parse_series(flows_a, "方案 A 年净现金流量"),
                    },
                    {
                        "name": name_b,
                        "initial": initial_b,
                        "cash_flows": parse_series(flows_b, "方案 B 年净现金流量"),
                    },
                ],
                rate,
            )
        submitted = primary_button()
    if submitted and builder is not None:
        calculate_and_store("pi_result", builder)

    def demo():
        if kind == "项目全面评价":
            return pi.project_appraisal_result(
                1000000,
                [280000, 300000, 320000, 300000, 280000],
                0.10,
                project_name="A项目",
                plot=True,
            )
        return pi.compare_projects(
            [
                {"name": "短寿命方案", "initial": 500000, "cash_flows": [220000, 240000, 260000]},
                {
                    "name": "长寿命方案",
                    "initial": 800000,
                    "cash_flows": [230000, 250000, 280000, 300000, 320000],
                },
            ],
            0.10,
        )

    demo_button("pi_result", demo)
    render_saved("pi_result")


# ---------------------------------------------------------------------------
# 模块 3：资本成本
# ---------------------------------------------------------------------------
COST_TYPES = [
    "CAPM 必要收益率",
    "债务资本成本——一般模式",
    "债务资本成本——贴现模式",
    "普通股成本——股利增长模型",
    "留存收益资本成本",
    "加权平均资本成本 WACC",
]


def _capital_demo(kind: str):
    if kind == "CAPM 必要收益率":
        return cc.capm_result(0.03, 1.2, 0.09)
    if kind == "债务资本成本——一般模式":
        return cc.debt_cost_general_result(80, 1000, 0.25, 0.02)
    if kind == "债务资本成本——贴现模式":
        return cc.debt_cost_discount_result(1000, 0.08, 5, 1050, 0.25, 0.02)
    if kind == "普通股成本——股利增长模型":
        return cc.equity_cost_growth_result(1.2, 20, 0.05, 0.03)
    if kind == "留存收益资本成本":
        return cc.retained_earnings_result(1.2, 20, 0.05)
    return cc.wacc_result(
        [
            {"name": "长期借款", "amount": 400, "cost": 0.0612},
            {"name": "普通股权益", "amount": 600, "cost": 0.1149},
        ]
    )


def page_capital_cost() -> None:
    page_header(
        "3",
        "资本成本",
        "CAPM、债务一般/贴现模式、普通股、留存收益和 WACC。WACC 可直接增删资本来源。",
    )
    kind = st.selectbox("计算类型", COST_TYPES, key="cc_kind")
    with st.form("cc_form"):
        builder = None
        if kind == "CAPM 必要收益率":
            col1, col2, col3 = st.columns(3)
            with col1:
                rf = rate_input("无风险收益率", 3.0, "cc_rf")
            with col2:
                beta = decimal_input("β 系数", 1.2, "cc_beta")
            with col3:
                rm = rate_input("市场组合收益率", 9.0, "cc_rm")
            builder = lambda: cc.capm_result(rf, beta, rm)
        elif kind == "债务资本成本——一般模式":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                interest = money_input("年利息（元）", 80, "cc_interest", step=10)
            with col2:
                amount = money_input("债务筹资额（元）", 1000, "cc_debt", step=100)
            with col3:
                tax = rate_input("所得税税率", 25.0, "cc_tax_general", max_value=100)
            with col4:
                fee = rate_input("筹资费率", 2.0, "cc_fee_general", max_value=100)
            builder = lambda: cc.debt_cost_general_result(interest, amount, tax, fee)
        elif kind == "债务资本成本——贴现模式":
            col1, col2, col3 = st.columns(3)
            with col1:
                face = money_input("债券面值（元）", 1000, "cc_face", step=100)
                coupon = rate_input("票面利率", 8.0, "cc_coupon")
            with col2:
                years = integer_input("剩余期限（年）", 5, "cc_years")
                price = money_input("发行价格（元）", 1050, "cc_price", step=10)
            with col3:
                tax = rate_input("所得税税率", 25.0, "cc_tax_discount", max_value=100)
                fee = rate_input("筹资费率", 2.0, "cc_fee_discount", max_value=100)
            builder = lambda: cc.debt_cost_discount_result(face, coupon, years, price, tax, fee)
        elif kind == "普通股成本——股利增长模型":
            col1, col2 = st.columns(2)
            with col1:
                d0 = decimal_input("当前每股股利 D0（元）", 1.2, "cc_d0", step=0.1)
                price = decimal_input("每股市价 P0（元）", 20.0, "cc_price", step=1.0)
            with col2:
                growth = rate_input("股利增长率", 5.0, "cc_growth", allow_negative=True)
                fee = rate_input("筹资费率", 3.0, "cc_fee_equity", max_value=100)
            builder = lambda: cc.equity_cost_growth_result(d0, price, growth, fee)
        elif kind == "留存收益资本成本":
            col1, col2, col3 = st.columns(3)
            with col1:
                d0 = decimal_input("当前每股股利 D0（元）", 1.2, "cc_ret_d0", step=0.1)
            with col2:
                price = decimal_input("每股市价 P0（元）", 20.0, "cc_ret_price", step=1.0)
            with col3:
                growth = rate_input("股利增长率", 5.0, "cc_ret_growth", allow_negative=True)
            builder = lambda: cc.retained_earnings_result(d0, price, growth)
        else:
            st.caption("按金额权重计算，资本成本请填写百分数。可增删行。")
            default_components = pd.DataFrame(
                [
                    {"名称": "长期借款", "金额": 400.0, "资本成本(%)": 6.12},
                    {"名称": "普通股权益", "金额": 600.0, "资本成本(%)": 11.49},
                ]
            )
            edited = st.data_editor(
                default_components,
                num_rows="dynamic",
                hide_index=True,
                key="cc_wacc_editor",
                column_config={
                    "名称": st.column_config.TextColumn(required=True),
                    "金额": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                    "资本成本(%)": st.column_config.NumberColumn(
                        min_value=0.0, max_value=100.0, format="%.4f"
                    ),
                },
            )

            def build_wacc():
                components: List[Dict[str, object]] = []
                for _, row in edited.iterrows():
                    if pd.isna(row["名称"]) or pd.isna(row["金额"]):
                        continue
                    components.append(
                        {
                            "name": str(row["名称"]),
                            "amount": float(row["金额"]),
                            "cost": float(row["资本成本(%)"]) / 100.0,
                        }
                    )
                return cc.wacc_result(components)

            builder = build_wacc
        submitted = primary_button()
    if submitted and builder is not None:
        calculate_and_store("cc_result", builder)
    demo_button("cc_result", lambda: _capital_demo(kind))
    render_saved("cc_result")


# ---------------------------------------------------------------------------
# 模块 4：杠杆原理
# ---------------------------------------------------------------------------
def page_leverage() -> None:
    page_header(
        "4",
        "杠杆原理",
        "计算 DOL、DFL、DTL，并查看销量变化对 EBIT 与每股收益的放大效应。",
    )
    with st.form("lv_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            q = decimal_input("销售量 Q（件）", 10000, "lv_q", step=100)
            price = decimal_input("单价 P（元）", 100, "lv_price", step=1)
        with col2:
            variable = decimal_input("单位变动成本 V（元）", 60, "lv_variable", step=1)
            fixed = money_input("固定经营成本 F（元）", 200000, "lv_fixed", step=10000)
        with col3:
            interest = money_input("利息费用 I（元）", 50000, "lv_interest", step=5000)
            preferred = money_input("优先股股利 Dp（元）", 0, "lv_preferred", step=1000)
        with col4:
            tax = rate_input("所得税税率", 25.0, "lv_tax", max_value=100)
            change = rate_input(
                "预计销售变动率", 10.0, "lv_change", allow_negative=True, max_value=100
            )
        submitted = primary_button()
    if submitted:
        calculate_and_store(
            "lv_result",
            lambda: lv.leverage_result(
                q, price, variable, fixed, interest, preferred, tax, change
            ),
        )
    demo_button(
        "lv_result",
        lambda: lv.leverage_result(10000, 100, 60, 200000, 50000, 0, 0.25, 0.10),
    )
    render_saved("lv_result")


# ---------------------------------------------------------------------------
# 模块 5：资本结构
# ---------------------------------------------------------------------------
CAPITAL_STRUCTURE_TYPES = ["每股收益无差别点", "公司价值分析法"]


def page_capital_structure() -> None:
    page_header(
        "5",
        "资本结构",
        "用 EBIT-EPS 无差别点比较筹资方案，或用公司价值 V=S+B 与 WACC 选择资本结构。",
    )
    kind = st.selectbox("计算类型", CAPITAL_STRUCTURE_TYPES, key="cs_kind")
    with st.form("cs_form"):
        if kind == "每股收益无差别点":
            left, right = st.columns(2)
            with left:
                st.markdown("**方案 A**")
                name_a = st.text_input("方案 A 名称", value="增发普通股", key="cs_name_a")
                interest_a = money_input("方案 A 年利息（元）", 0, "cs_int_a", step=10000)
                preferred_a = money_input("方案 A 优先股股利（元）", 0, "cs_pref_a", step=10000)
                shares_a = decimal_input("方案 A 普通股股数", 1000000, "cs_shares_a", step=10000)
            with right:
                st.markdown("**方案 B**")
                name_b = st.text_input("方案 B 名称", value="债务融资", key="cs_name_b")
                interest_b = money_input("方案 B 年利息（元）", 400000, "cs_int_b", step=10000)
                preferred_b = money_input("方案 B 优先股股利（元）", 0, "cs_pref_b", step=10000)
                shares_b = decimal_input("方案 B 普通股股数", 700000, "cs_shares_b", step=10000)
            col1, col2 = st.columns(2)
            with col1:
                tax = rate_input("所得税税率", 25.0, "cs_tax", max_value=100)
            with col2:
                expected = money_input("预期息税前利润 EBIT（元）", 2000000, "cs_expected")
            builder = lambda: cs.eps_indifference_result(
                {
                    "name": name_a,
                    "interest": interest_a,
                    "preferred_dividend": preferred_a,
                    "shares": shares_a,
                },
                {
                    "name": name_b,
                    "interest": interest_b,
                    "preferred_dividend": preferred_b,
                    "shares": shares_b,
                },
                tax,
                expected,
            )
        else:
            col1, col2 = st.columns(2)
            with col1:
                ebit = money_input("息税前利润 EBIT（元）", 2000000, "cs_ebit")
            with col2:
                tax = rate_input("所得税税率", 25.0, "cs_value_tax", max_value=100)
            st.caption("每个方案填写债务价值、税前债务成本和股权资本成本，可增删行。")
            default_structures = pd.DataFrame(
                [
                    {"方案": "无负债", "债务价值": 0.0, "税前债务成本(%)": 6.0, "股权成本(%)": 10.0},
                    {"方案": "负债500万", "债务价值": 5000000.0, "税前债务成本(%)": 6.0, "股权成本(%)": 11.0},
                    {"方案": "负债1000万", "债务价值": 10000000.0, "税前债务成本(%)": 7.0, "股权成本(%)": 12.5},
                ]
            )
            edited = st.data_editor(
                default_structures,
                num_rows="dynamic",
                hide_index=True,
                key="cs_structures_editor",
                column_config={
                    "方案": st.column_config.TextColumn(required=True),
                    "债务价值": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                    "税前债务成本(%)": st.column_config.NumberColumn(
                        min_value=0.0, max_value=100.0, format="%.2f"
                    ),
                    "股权成本(%)": st.column_config.NumberColumn(
                        min_value=0.0, max_value=100.0, format="%.2f"
                    ),
                },
            )

            def build_company_value():
                structures = []
                for _, row in edited.iterrows():
                    if pd.isna(row["方案"]) or pd.isna(row["债务价值"]):
                        continue
                    structures.append(
                        {
                            "name": str(row["方案"]),
                            "debt": float(row["债务价值"]),
                            "debt_cost": float(row["税前债务成本(%)"]) / 100.0,
                            "equity_cost": float(row["股权成本(%)"]) / 100.0,
                        }
                    )
                return cs.company_value_analysis(ebit, tax, structures)

            builder = build_company_value
        submitted = primary_button()
    if submitted and builder is not None:
        calculate_and_store("cs_result", builder)

    def demo():
        if kind == "每股收益无差别点":
            return cs.eps_indifference_result(
                {"name": "全部权益", "interest": 0, "preferred_dividend": 0, "shares": 1000000},
                {"name": "债务融资", "interest": 400000, "preferred_dividend": 0, "shares": 700000},
                0.25,
                2000000,
            )
        return cs.company_value_analysis(
            2000000,
            0.25,
            [
                {"name": "无负债", "debt": 0, "debt_cost": 0.06, "equity_cost": 0.10},
                {"name": "负债500万", "debt": 5000000, "debt_cost": 0.06, "equity_cost": 0.11},
                {"name": "负债1000万", "debt": 10000000, "debt_cost": 0.07, "equity_cost": 0.125},
            ],
        )

    demo_button("cs_result", demo)
    render_saved("cs_result")


# ---------------------------------------------------------------------------
# 模块 6：营运资金管理
# ---------------------------------------------------------------------------
WC_TYPES = [
    "现金管理——存货模型",
    "现金管理——Miller-Orr 模型",
    "应收账款机会成本",
    "信用政策决策",
    "存货管理——EOQ",
    "存货管理——陆续供货",
    "存货管理——保险储备",
]


def _wc_demo(kind: str):
    if kind == "现金管理——存货模型":
        return wc.baumol_result(3600000, 1000, 0.08)
    if kind == "现金管理——Miller-Orr 模型":
        return wc.miller_orr_result(1000, 2000, 0.0002, 10000)
    if kind == "应收账款机会成本":
        return wc.ar_opportunity_result(12000000, 45, 0.60, 0.10)
    if kind == "信用政策决策":
        return wc.credit_policy_result(
            {
                "sales": 10000000, "dso": 30, "bad_debt_rate": 0.01,
                "collection_cost": 50000, "variable_cost_ratio": 0.60,
                "opportunity_rate": 0.10, "discount_rate": 0.0,
                "discount_proportion": 0.0,
            },
            {
                "sales": 12000000, "dso": 45, "bad_debt_rate": 0.02,
                "collection_cost": 80000, "variable_cost_ratio": 0.60,
                "opportunity_rate": 0.10, "discount_rate": 0.02,
                "discount_proportion": 0.50,
            },
        )
    if kind == "存货管理——EOQ":
        return wc.eoq_result(36000, 500, 10)
    if kind == "存货管理——陆续供货":
        return wc.eoq_gradual_result(36000, 500, 10, 200, 100)
    return wc.safety_stock_result(1.65, 100, 4, 1000)


def page_working_capital() -> None:
    page_header(
        "6",
        "营运资金管理",
        "现金存货/随机模型、应收账款与信用政策、EOQ、陆续供货和保险储备。",
    )
    kind = st.selectbox("计算类型", WC_TYPES, key="wc_kind")
    with st.form("wc_form"):
        builder = None
        if kind == "现金管理——存货模型":
            col1, col2, col3 = st.columns(3)
            with col1:
                demand = money_input("全年现金需求 T（元）", 3600000, "wc_cash_t")
            with col2:
                cost = money_input("每次转换成本 F（元）", 1000, "wc_cash_f", step=100)
            with col3:
                rate = rate_input("有价证券年收益率 K", 8.0, "wc_cash_k")
            builder = lambda: wc.baumol_result(demand, cost, rate)
        elif kind == "现金管理——Miller-Orr 模型":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                cost = money_input("每次转换成本 F（元）", 1000, "wc_mo_f", step=100)
            with col2:
                sigma = money_input("每日现金流标准差（元）", 2000, "wc_mo_sigma", step=100)
            with col3:
                rate = rate_input("日机会成本率", 0.02, "wc_mo_rate", step=0.001, max_value=10)
            with col4:
                lower = money_input("最低控制线 L（元）", 10000, "wc_mo_l", step=1000)
            builder = lambda: wc.miller_orr_result(cost, sigma, rate, lower)
        elif kind == "应收账款机会成本":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                sales = money_input("年销售额（元）", 12000000, "wc_ar_sales")
            with col2:
                dso = decimal_input("平均收现期（天）", 45, "wc_ar_dso", step=1)
            with col3:
                variable_ratio = rate_input("变动成本率", 60.0, "wc_ar_vcr", max_value=100)
            with col4:
                rate = rate_input("资金机会成本率", 10.0, "wc_ar_rate")
            builder = lambda: wc.ar_opportunity_result(sales, dso, variable_ratio, rate)
        elif kind == "信用政策决策":
            rate = rate_input("资金机会成本率（两方案共用）", 10.0, "wc_credit_rate")
            st.caption("直接在表中修改现行与拟议政策；销售额、收账费用为元，其余为百分数。")
            credit_df = pd.DataFrame(
                [
                    {"政策": "现行政策", "年销售额": 10000000.0, "平均收现期": 30.0,
                     "坏账率(%)": 1.0, "收账费用": 50000.0, "变动成本率(%)": 60.0,
                     "现金折扣率(%)": 0.0, "享受折扣比例(%)": 0.0},
                    {"政策": "拟议政策", "年销售额": 12000000.0, "平均收现期": 45.0,
                     "坏账率(%)": 2.0, "收账费用": 80000.0, "变动成本率(%)": 60.0,
                     "现金折扣率(%)": 2.0, "享受折扣比例(%)": 50.0},
                ]
            )
            edited = st.data_editor(
                credit_df,
                num_rows="fixed",
                hide_index=True,
                key="wc_credit_editor",
                column_config={
                    "政策": st.column_config.TextColumn(required=True),
                    "年销售额": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                    "平均收现期": st.column_config.NumberColumn(min_value=0.0, format="%.1f"),
                    "坏账率(%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, format="%.2f"),
                    "收账费用": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                    "变动成本率(%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, format="%.2f"),
                    "现金折扣率(%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, format="%.2f"),
                    "享受折扣比例(%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, format="%.2f"),
                },
            )

            def build_credit():
                if len(edited) != 2:
                    raise ValueError("信用政策决策需要保持两行：现行政策和拟议政策。")

                def policy(row):
                    return {
                        "sales": float(row["年销售额"]),
                        "dso": float(row["平均收现期"]),
                        "bad_debt_rate": float(row["坏账率(%)"]) / 100.0,
                        "collection_cost": float(row["收账费用"]),
                        "variable_cost_ratio": float(row["变动成本率(%)"]) / 100.0,
                        "opportunity_rate": rate,
                        "discount_rate": float(row["现金折扣率(%)"]) / 100.0,
                        "discount_proportion": float(row["享受折扣比例(%)"]) / 100.0,
                    }

                return wc.credit_policy_result(
                    policy(edited.iloc[0]), policy(edited.iloc[1])
                )

            builder = build_credit
        elif kind == "存货管理——EOQ":
            col1, col2, col3 = st.columns(3)
            with col1:
                demand = decimal_input("全年需求量 D（件）", 36000, "wc_eoq_d", step=100)
            with col2:
                cost = money_input("每次订货成本 K（元）", 500, "wc_eoq_k", step=50)
            with col3:
                holding = money_input("单位年储存成本 Kc（元）", 10, "wc_eoq_kc", step=1)
            builder = lambda: wc.eoq_result(demand, cost, holding)
        elif kind == "存货管理——陆续供货":
            col1, col2, col3 = st.columns(3)
            with col1:
                demand = decimal_input("全年需求量 D（件）", 36000, "wc_grad_d", step=100)
                cost = money_input("每次订货成本 K（元）", 500, "wc_grad_k", step=50)
            with col2:
                holding = money_input("单位年储存成本 Kc（元）", 10, "wc_grad_kc", step=1)
                supply = decimal_input("每日供货量 p（件/天）", 200, "wc_grad_p", step=10)
            with col3:
                daily = decimal_input("每日耗用量 d（件/天）", 100, "wc_grad_daily", step=10)
            builder = lambda: wc.eoq_gradual_result(demand, cost, holding, supply, daily)
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                z = decimal_input("安全系数 z", 1.65, "wc_ss_z", step=0.01)
            with col2:
                sigma = decimal_input("日需求标准差（件）", 100, "wc_ss_sigma", step=10)
            with col3:
                lead = decimal_input("提前期（天）", 4, "wc_ss_lead", step=1)
            with col4:
                daily = decimal_input("平均日需求量（件/天）", 1000, "wc_ss_daily", step=10)
            builder = lambda: wc.safety_stock_result(z, sigma, lead, daily)
        submitted = primary_button()
    if submitted and builder is not None:
        calculate_and_store("wc_result", builder)
    demo_button("wc_result", lambda: _wc_demo(kind))
    render_saved("wc_result")


# ---------------------------------------------------------------------------
# 模块 7：成本管理
# ---------------------------------------------------------------------------
COST_ANALYSIS_TYPES = [
    "本量利分析",
    "直接材料差异",
    "直接人工差异",
    "变动制造费用差异",
    "固定制造费用二差异",
    "固定制造费用三差异",
    "作业成本法",
]


def _cost_demo(kind: str):
    if kind == "本量利分析":
        return ca.cvp_analysis(100, 60, 200000, 10000, plot=True)
    if kind == "直接材料差异":
        return ca.direct_material_result(1000, 2, 2100, 10, 9.8)
    if kind == "直接人工差异":
        return ca.direct_labor_result(1000, 2, 1950, 20, 21)
    if kind == "变动制造费用差异":
        return ca.variable_overhead_result(1000, 2, 1950, 5, 5.2)
    if kind == "固定制造费用二差异":
        return ca.fixed_overhead_two_variance_result(310000, 300000, 5000, 4000)
    if kind == "固定制造费用三差异":
        return ca.fixed_overhead_three_variance_result(310000, 300000, 5000, 4200, 4000)
    return ca.abc_cost(
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


def page_cost_analysis() -> None:
    page_header(
        "7",
        "成本管理",
        "本量利、四类标准成本差异、固定制造费用二/三差异和作业成本法。",
    )
    kind = st.selectbox("计算类型", COST_ANALYSIS_TYPES, key="ca_kind")
    with st.form("ca_form"):
        builder = None
        if kind == "本量利分析":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                price = decimal_input("单价 P（元）", 100, "ca_cvp_p", step=1)
            with col2:
                variable = decimal_input("单位变动成本 V（元）", 60, "ca_cvp_v", step=1)
            with col3:
                fixed = money_input("固定成本 F（元）", 200000, "ca_cvp_f", step=10000)
            with col4:
                quantity = decimal_input("实际销售量 Q（件）", 10000, "ca_cvp_q", step=100)
            plot = st.checkbox("绘制本量利图", value=True, key="ca_cvp_plot")
            builder = lambda: ca.cvp_analysis(price, variable, fixed, quantity, plot=plot)
        elif kind == "直接材料差异":
            col1, col2, col3 = st.columns(3)
            with col1:
                output = decimal_input("实际产量（件）", 1000, "ca_dm_output", step=10)
                std_qty = decimal_input("单位标准用量", 2, "ca_dm_stdqty", step=0.1)
            with col2:
                actual_qty = decimal_input("实际用量", 2100, "ca_dm_aqty", step=10)
            with col3:
                std_price = decimal_input("标准单价（元）", 10, "ca_dm_stdprice", step=0.5)
                actual_price = decimal_input("实际单价（元）", 9.8, "ca_dm_actprice", step=0.1)
            builder = lambda: ca.direct_material_result(
                output, std_qty, actual_qty, std_price, actual_price
            )
        elif kind == "直接人工差异":
            col1, col2, col3 = st.columns(3)
            with col1:
                output = decimal_input("实际产量（件）", 1000, "ca_dl_output", step=10)
                std_hours = decimal_input("单位标准工时", 2, "ca_dl_stdhours", step=0.1)
            with col2:
                actual_hours = decimal_input("实际工时", 1950, "ca_dl_ahours", step=10)
            with col3:
                std_rate = decimal_input("标准工资率（元/小时）", 20, "ca_dl_stdrate", step=1)
                actual_rate = decimal_input("实际工资率（元/小时）", 21, "ca_dl_actrate", step=0.5)
            builder = lambda: ca.direct_labor_result(
                output, std_hours, actual_hours, std_rate, actual_rate
            )
        elif kind == "变动制造费用差异":
            col1, col2, col3 = st.columns(3)
            with col1:
                output = decimal_input("实际产量（件）", 1000, "ca_voh_output", step=10)
                std_hours = decimal_input("单位标准工时", 2, "ca_voh_stdhours", step=0.1)
            with col2:
                actual_hours = decimal_input("实际工时", 1950, "ca_voh_ahours", step=10)
            with col3:
                std_rate = decimal_input("标准分配率（元/小时）", 5, "ca_voh_stdrate", step=0.5)
                actual_rate = decimal_input("实际分配率（元/小时）", 5.2, "ca_voh_actrate", step=0.1)
            builder = lambda: ca.variable_overhead_result(
                output, std_hours, actual_hours, std_rate, actual_rate
            )
        elif kind == "固定制造费用二差异":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                actual = money_input("实际固定制造费用（元）", 310000, "ca_foh2_actual", step=1000)
            with col2:
                budget = money_input("预算固定制造费用（元）", 300000, "ca_foh2_budget", step=1000)
            with col3:
                denom = decimal_input("预算产量标准工时", 5000, "ca_foh2_denom", step=100)
            with col4:
                allowed = decimal_input("实际产量标准工时", 4000, "ca_foh2_allowed", step=100)
            builder = lambda: ca.fixed_overhead_two_variance_result(
                actual, budget, denom, allowed
            )
        elif kind == "固定制造费用三差异":
            col1, col2, col3 = st.columns(3)
            with col1:
                actual = money_input("实际固定制造费用（元）", 310000, "ca_foh3_actual", step=1000)
                budget = money_input("预算固定制造费用（元）", 300000, "ca_foh3_budget", step=1000)
            with col2:
                denom = decimal_input("预算产量标准工时", 5000, "ca_foh3_denom", step=100)
                actual_hours = decimal_input("实际工时", 4200, "ca_foh3_ahours", step=100)
            with col3:
                allowed = decimal_input("实际产量标准工时", 4000, "ca_foh3_allowed", step=100)
            builder = lambda: ca.fixed_overhead_three_variance_result(
                actual, budget, denom, actual_hours, allowed
            )
        else:
            st.caption("每个作业中心填写成本库、成本动因总量和本产品耗用量；可增删行。")
            activity_df = pd.DataFrame(
                [
                    {"作业中心": "设备调试", "作业成本": 50000.0, "成本动因总量": 500.0, "本产品耗用量": 100.0},
                    {"作业中心": "质量检验", "作业成本": 30000.0, "成本动因总量": 1000.0, "本产品耗用量": 200.0},
                    {"作业中心": "材料搬运", "作业成本": 20000.0, "成本动因总量": 2000.0, "本产品耗用量": 500.0},
                ]
            )
            edited = st.data_editor(
                activity_df,
                num_rows="dynamic",
                hide_index=True,
                key="ca_abc_editor",
                column_config={
                    "作业中心": st.column_config.TextColumn(required=True),
                    "作业成本": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                    "成本动因总量": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                    "本产品耗用量": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                },
            )
            col1, col2 = st.columns(2)
            with col1:
                product_name = st.text_input("产品名称", value="甲产品", key="ca_abc_product")
            with col2:
                output = decimal_input("产品产量（件）", 10000, "ca_abc_output", step=100)

            def build_abc():
                activities = []
                usages = {}
                for _, row in edited.iterrows():
                    if pd.isna(row["作业中心"]) or pd.isna(row["作业成本"]):
                        continue
                    name = str(row["作业中心"])
                    activities.append(
                        {
                            "name": name,
                            "cost": float(row["作业成本"]),
                            "driver_total": float(row["成本动因总量"]),
                        }
                    )
                    usages[name] = float(row["本产品耗用量"])
                return ca.abc_cost(
                    activities,
                    [{"name": product_name, "output": output, "usage": usages}],
                )

            builder = build_abc
        submitted = primary_button()
    if submitted and builder is not None:
        calculate_and_store("ca_result", builder)
    demo_button("ca_result", lambda: _cost_demo(kind))
    render_saved("ca_result")


# ---------------------------------------------------------------------------
# 模块 8：证券估值
# ---------------------------------------------------------------------------
SECURITY_TYPES = [
    "债券价值",
    "债券到期收益率",
    "股票价值——零增长",
    "股票价值——固定股利（有限期）",
    "股票价值——固定增长",
    "股票内部收益率",
]
STOCK_IRR_MODELS = ["零增长模型", "固定增长模型", "有限期固定股利模型"]


def _security_demo(kind: str, irr_model: str):
    if kind == "债券价值":
        return sv.bond_value_result(1000, 0.08, 5, 0.10)
    if kind == "债券到期收益率":
        return sv.bond_ytm_result(950, 1000, 0.08, 5)
    if kind == "股票价值——零增长":
        return sv.zero_growth_stock_result(1.2, 0.10)
    if kind == "股票价值——固定股利（有限期）":
        return sv.fixed_dividend_stock_result(1.2, 0.10, 5, 22)
    if kind == "股票价值——固定增长":
        return sv.constant_growth_stock_result(1.2, 0.10, 0.05)
    if irr_model == "零增长模型":
        return sv.stock_irr_result("zero", 20, 1.2)
    if irr_model == "固定增长模型":
        return sv.stock_irr_result("growth", 20, 1.2, growth_rate=0.05)
    return sv.stock_irr_result("fixed", 20, 1.2, years=5, selling_price=22)


def page_securities() -> None:
    page_header(
        "8",
        "证券估值",
        "债券价值与到期收益率，零增长/固定股利/固定增长股票模型及股票内部收益率。",
    )
    kind = st.selectbox("计算类型", SECURITY_TYPES, key="sv_kind")
    irr_model = "零增长模型"
    if kind == "股票内部收益率":
        irr_model = st.selectbox("股票 IRR 模型", STOCK_IRR_MODELS, key="sv_irr_model")
    with st.form("sv_form"):
        builder = None
        if kind == "债券价值":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                face = money_input("债券面值（元）", 1000, "sv_bond_face", step=100)
            with col2:
                coupon = rate_input("票面利率", 8.0, "sv_bond_coupon")
            with col3:
                years = integer_input("剩余期限（年）", 5, "sv_bond_years")
            with col4:
                required = rate_input("市场必要收益率", 10.0, "sv_bond_required")
            builder = lambda: sv.bond_value_result(face, coupon, years, required)
        elif kind == "债券到期收益率":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                price = money_input("债券当前价格（元）", 950, "sv_ytm_price", step=10)
            with col2:
                face = money_input("债券面值（元）", 1000, "sv_ytm_face", step=100)
            with col3:
                coupon = rate_input("票面利率", 8.0, "sv_ytm_coupon")
            with col4:
                years = integer_input("剩余期限（年）", 5, "sv_ytm_years")
            builder = lambda: sv.bond_ytm_result(price, face, coupon, years)
        elif kind == "股票价值——零增长":
            col1, col2 = st.columns(2)
            with col1:
                dividend = decimal_input("每股股利 D（元）", 1.2, "sv_zero_d", step=0.1)
            with col2:
                required = rate_input("必要收益率", 10.0, "sv_zero_r")
            builder = lambda: sv.zero_growth_stock_result(dividend, required)
        elif kind == "股票价值——固定股利（有限期）":
            col1, col2 = st.columns(2)
            with col1:
                dividend = decimal_input("每股固定股利 D（元）", 1.2, "sv_fixed_d", step=0.1)
                required = rate_input("必要收益率", 10.0, "sv_fixed_r")
            with col2:
                years = integer_input("持有期 n（年）", 5, "sv_fixed_n")
                selling = decimal_input("期末售价 Pn（元）", 22, "sv_fixed_pn", step=1)
            builder = lambda: sv.fixed_dividend_stock_result(
                dividend, required, years, selling
            )
        elif kind == "股票价值——固定增长":
            col1, col2, col3 = st.columns(3)
            with col1:
                d0 = decimal_input("当前每股股利 D0（元）", 1.2, "sv_growth_d0", step=0.1)
            with col2:
                required = rate_input("必要收益率", 10.0, "sv_growth_r")
            with col3:
                growth = rate_input("股利增长率", 5.0, "sv_growth_g", allow_negative=True)
            builder = lambda: sv.constant_growth_stock_result(d0, required, growth)
        else:
            price = decimal_input("股票价格 P（元）", 20, "sv_irr_price", step=1)
            if irr_model == "零增长模型":
                dividend = decimal_input("每股股利 D（元）", 1.2, "sv_irr_zero_d", step=0.1)
                builder = lambda: sv.stock_irr_result("zero", price, dividend)
            elif irr_model == "固定增长模型":
                col1, col2 = st.columns(2)
                with col1:
                    d0 = decimal_input("当前每股股利 D0（元）", 1.2, "sv_irr_d0", step=0.1)
                with col2:
                    growth = rate_input("股利增长率", 5.0, "sv_irr_g", allow_negative=True)
                builder = lambda: sv.stock_irr_result(
                    "growth", price, d0, growth_rate=growth
                )
            else:
                col1, col2 = st.columns(2)
                with col1:
                    dividend = decimal_input("每股固定股利 D（元）", 1.2, "sv_irr_fixed_d", step=0.1)
                with col2:
                    years = integer_input("持有期 n（年）", 5, "sv_irr_fixed_n")
                    selling = decimal_input("期末售价 Pn（元）", 22, "sv_irr_fixed_pn", step=1)
                builder = lambda: sv.stock_irr_result(
                    "fixed", price, dividend, years=years, selling_price=selling
                )
        submitted = primary_button()
    if submitted and builder is not None:
        calculate_and_store("sv_result", builder)
    demo_button("sv_result", lambda: _security_demo(kind, irr_model))
    render_saved("sv_result")


# ---------------------------------------------------------------------------
# 模块 9：财务分析
# ---------------------------------------------------------------------------
def _financial_demo():
    return fa.financial_analysis(
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


def page_financial_analysis() -> None:
    page_header(
        "9",
        "财务分析",
        "一次计算偿债、营运、盈利、现金指标，并输出传统杜邦与改进杜邦瀑布图。",
    )
    with st.form("fa_form"):
        st.subheader("资产负债表数据", icon=":material/account_balance:")
        col1, col2, col3 = st.columns(3)
        with col1:
            current_assets = money_input("流动资产", 800, "fa_ca", step=100)
            inventory = money_input("存货", 300, "fa_inventory", step=100)
            cash = money_input("货币资金", 150, "fa_cash", step=100)
        with col2:
            receivables = money_input("平均应收账款", 250, "fa_ar", step=100)
            current_liabilities = money_input("流动负债", 400, "fa_cl", step=100)
            total_liabilities = money_input("负债总额", 1000, "fa_tl", step=100)
        with col3:
            total_assets = money_input("平均总资产", 2000, "fa_ta", step=100)
            total_equity = money_input("平均股东权益", 1000, "fa_equity", step=100)
            net_debt = money_input("净负债", 300, "fa_netdebt", step=100, allow_negative=True)
        st.subheader("利润与现金流数据", icon=":material/receipt_long:")
        col4, col5, col6 = st.columns(3)
        with col4:
            revenue = money_input("营业收入", 3000, "fa_revenue", step=100)
            operating_cost = money_input("营业成本", 2100, "fa_cost", step=100)
            net_profit = money_input("净利润", 300, "fa_np", step=100)
        with col5:
            interest = money_input("利息费用", 60, "fa_interest", step=10)
            ebit = money_input("息税前利润 EBIT", 460, "fa_ebit", step=10)
            tax = rate_input("所得税税率", 25.0, "fa_tax", max_value=100)
        with col6:
            operating_cash_flow = money_input(
                "经营活动现金流量净额", 380, "fa_ocf", step=100, allow_negative=True
            )
            depreciation = money_input("折旧摊销", 100, "fa_dep", step=10)
        plot = st.checkbox("绘制杜邦分析瀑布图", value=True, key="fa_plot")
        submitted = primary_button()
    if submitted:
        data = {
            "current_assets": current_assets,
            "inventory": inventory,
            "cash": cash,
            "receivables": receivables,
            "current_liabilities": current_liabilities,
            "total_liabilities": total_liabilities,
            "total_assets": total_assets,
            "total_equity": total_equity,
            "revenue": revenue,
            "operating_cost": operating_cost,
            "net_profit": net_profit,
            "interest_expense": interest,
            "ebit": ebit,
            "tax_rate": tax,
            "operating_cash_flow": operating_cash_flow,
            "depreciation": depreciation,
            "net_debt": net_debt,
        }
        calculate_and_store("fa_result", lambda: fa.financial_analysis(data, plot=plot))
    demo_button("fa_result", _financial_demo)
    render_saved("fa_result")


# ---------------------------------------------------------------------------
# 模块 10：股利分配管理
# ---------------------------------------------------------------------------
DIVIDEND_TYPES = [
    "剩余股利政策",
    "固定或稳定增长股利",
    "固定股利支付率",
    "低正常股利加额外股利",
    "股票股利",
    "股票分割",
    "股票回购",
]


def _dividend_demo(kind: str):
    if kind == "剩余股利政策":
        return dp.residual_dividend_result(2000000, 0.50, 2000000, 1000000)
    if kind == "固定或稳定增长股利":
        return dp.stable_dividend_result(1.0, 0.05, 3, 1000000, 3000000)
    if kind == "固定股利支付率":
        return dp.fixed_payout_result(3000000, 0.40, 1000000)
    if kind == "低正常股利加额外股利":
        return dp.low_regular_extra_result(2000000, 1000000, 0.50, 0.30)
    if kind == "股票股利":
        return dp.stock_dividend_result(1000000, 0.10, 20, 2000000)
    if kind == "股票分割":
        return dp.stock_split_result(1000000, 2, 20, 2000000)
    return dp.stock_repurchase_result(2000000, 1000000, 20, 2000000)


def page_dividend() -> None:
    page_header(
        "10",
        "股利分配管理",
        "四种股利政策，以及股票股利、股票分割和股票回购对股数、EPS 与股价的影响。",
    )
    kind = st.selectbox("计算类型", DIVIDEND_TYPES, key="dp_kind")
    with st.form("dp_form"):
        builder = None
        if kind == "剩余股利政策":
            col1, col2 = st.columns(2)
            with col1:
                budget = money_input("投资资金预算（元）", 2000000, "dp_budget")
                debt_ratio = rate_input("目标资产负债率", 50.0, "dp_debt_ratio", max_value=100)
            with col2:
                income = money_input("净利润（元）", 2000000, "dp_income")
                shares = decimal_input("普通股股数", 1000000, "dp_shares", step=10000)
            builder = lambda: dp.residual_dividend_result(budget, debt_ratio, income, shares)
        elif kind == "固定或稳定增长股利":
            col1, col2, col3 = st.columns(3)
            with col1:
                prior = decimal_input("上年每股股利（元/股）", 1.0, "dp_prior", step=0.1)
                growth = rate_input("股利增长率", 5.0, "dp_growth", allow_negative=True)
            with col2:
                years = integer_input("预测年数", 3, "dp_years")
                shares = decimal_input("普通股股数", 1000000, "dp_stable_shares", step=10000)
            with col3:
                income = money_input("预计年净利润（元）", 3000000, "dp_stable_income")
            builder = lambda: dp.stable_dividend_result(prior, growth, years, shares, income)
        elif kind == "固定股利支付率":
            col1, col2, col3 = st.columns(3)
            with col1:
                income = money_input("净利润（元）", 3000000, "dp_payout_income")
            with col2:
                payout = rate_input("股利支付率", 40.0, "dp_payout_ratio", max_value=100)
            with col3:
                shares = decimal_input("普通股股数", 1000000, "dp_payout_shares", step=10000)
            builder = lambda: dp.fixed_payout_result(income, payout, shares)
        elif kind == "低正常股利加额外股利":
            col1, col2 = st.columns(2)
            with col1:
                income = money_input("净利润（元）", 2000000, "dp_low_income")
                shares = decimal_input("普通股股数", 1000000, "dp_low_shares", step=10000)
            with col2:
                regular = decimal_input("低正常每股股利（元/股）", 0.50, "dp_regular", step=0.05)
                extra = decimal_input("额外每股股利（元/股）", 0.30, "dp_extra", step=0.05)
            builder = lambda: dp.low_regular_extra_result(income, shares, regular, extra)
        elif kind == "股票股利":
            col1, col2 = st.columns(2)
            with col1:
                shares = decimal_input("原普通股股数", 1000000, "dp_sd_shares", step=10000)
                ratio = rate_input("股票股利比例", 10.0, "dp_sd_ratio", max_value=100)
            with col2:
                price = decimal_input("发放前股价（元）", 20, "dp_sd_price", step=1)
                income = money_input("净利润（元）", 2000000, "dp_sd_income")
            builder = lambda: dp.stock_dividend_result(shares, ratio, price, income)
        elif kind == "股票分割":
            col1, col2 = st.columns(2)
            with col1:
                shares = decimal_input("分割前股数", 1000000, "dp_split_shares", step=10000)
                ratio = decimal_input("分割比例（如 2 表示 1 拆 2）", 2, "dp_split_ratio", step=0.5)
            with col2:
                price = decimal_input("分割前股价（元）", 20, "dp_split_price", step=1)
                income = money_input("净利润（元）", 2000000, "dp_split_income")
            builder = lambda: dp.stock_split_result(shares, ratio, price, income)
        else:
            col1, col2 = st.columns(2)
            with col1:
                income = money_input("净利润（元）", 2000000, "dp_rep_income")
                shares = decimal_input("回购前股数", 1000000, "dp_rep_shares", step=10000)
            with col2:
                price = decimal_input("回购价格（元/股）", 20, "dp_rep_price", step=1)
                amount = money_input("回购金额（元）", 2000000, "dp_rep_amount")
            builder = lambda: dp.stock_repurchase_result(income, shares, price, amount)
        submitted = primary_button()
    if submitted and builder is not None:
        calculate_and_store("dp_result", builder)
    demo_button("dp_result", lambda: _dividend_demo(kind))
    render_saved("dp_result")


# ---------------------------------------------------------------------------
# 模块 11：期权基础估值
# ---------------------------------------------------------------------------
OPTION_TYPES = ["到期价值与净损益", "复制原理——看涨期权", "复制原理——看跌期权"]


def _option_demo(kind: str):
    if kind == "到期价值与净损益":
        return ov.option_payoff_result("call", 38, 40, 3, 1)
    option_type = "call" if "看涨" in kind else "put"
    return ov.binomial_result(50, 60, 40, 50, 0.05, option_type)


def page_option() -> None:
    page_header(
        "11",
        "期权基础估值",
        "看涨/看跌期权到期损益，以及单期二叉树复制原理与套期保值。",
    )
    kind = st.selectbox("计算类型", OPTION_TYPES, key="ov_kind")
    with st.form("ov_form"):
        builder = None
        if kind == "到期价值与净损益":
            option_type = st.selectbox(
                "期权类型", ["看涨期权 call", "看跌期权 put"], key="ov_option_type"
            )
            position = st.selectbox(
                "持仓方向", ["多头（买方）", "空头（卖方）"], key="ov_position"
            )
            col1, col2, col3 = st.columns(3)
            with col1:
                spot = decimal_input("到期标的资产价格 S（元）", 38, "ov_spot", step=1)
            with col2:
                strike = decimal_input("执行价格 K（元）", 40, "ov_strike", step=1)
            with col3:
                premium = decimal_input("期权费（元）", 3, "ov_premium", step=0.5)
            builder = lambda: ov.option_payoff_result(
                "call" if option_type.startswith("看涨") else "put",
                spot,
                strike,
                premium,
                1 if position.startswith("多头") else -1,
            )
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                s0 = decimal_input("当前股价 S0（元）", 50, "ov_s0", step=1)
                su = decimal_input("上涨后股价 Su（元）", 60, "ov_su", step=1)
            with col2:
                sd = decimal_input("下跌后股价 Sd（元）", 40, "ov_sd", step=1)
                strike = decimal_input("执行价格 K（元）", 50, "ov_strike_bin", step=1)
            with col3:
                risk_free = rate_input("单期无风险利率", 5.0, "ov_rf", max_value=100)
            option_type = "call" if "看涨" in kind else "put"
            builder = lambda: ov.binomial_result(s0, su, sd, strike, risk_free, option_type)
        submitted = primary_button()
    if submitted and builder is not None:
        calculate_and_store("ov_result", builder)
    demo_button("ov_result", lambda: _option_demo(kind))
    render_saved("ov_result")


# ---------------------------------------------------------------------------
# 模块 12：财务预算
# ---------------------------------------------------------------------------
def page_budget() -> None:
    page_header(
        "12",
        "财务预算",
        "一次生成销售、生产、材料、人工、制造费用、产品成本和现金预算七张联动表。",
    )
    st.caption("季度序列用英文逗号分隔；回款/付款比例填写小数（0.6 表示 60%）。")
    with st.form("fb_form"):
        st.subheader("销售与生产", icon=":material/point_of_sale:")
        col1, col2, col3 = st.columns(3)
        with col1:
            volumes_text = st.text_input(
                "各季度销售量（件）", value="1000,1200,1500,1300", key="fb_volumes"
            )
            price = decimal_input("销售单价（元）", 100, "fb_price", step=1)
        with col2:
            beginning_fg = decimal_input("期初产成品（件）", 100, "fb_begin_fg", step=10)
            ending_fg_ratio = rate_input("期末产成品占下期销售比例", 10.0, "fb_end_fg_ratio", max_value=100)
        with col3:
            ending_fg_last = decimal_input("最后一期期末产成品（件）", 150, "fb_end_fg_last", step=10)
        st.subheader("直接材料", icon=":material/inventory_2:")
        col4, col5, col6 = st.columns(3)
        with col4:
            material_per_unit = decimal_input("单位产品材料用量（千克/件）", 2, "fb_material_unit", step=0.1)
            material_price = decimal_input("材料单价（元/千克）", 5, "fb_material_price", step=0.5)
        with col5:
            beginning_material = decimal_input("期初材料（千克）", 200, "fb_begin_material", step=10)
            ending_material_ratio = rate_input("期末材料占下期耗用比例", 20.0, "fb_end_material_ratio", max_value=200)
        with col6:
            ending_material_last = decimal_input("最后一期期末材料（千克）", 300, "fb_end_material_last", step=10)
        st.subheader("人工与制造费用", icon=":material/engineering:")
        col7, col8, col9 = st.columns(3)
        with col7:
            hours_per_unit = decimal_input("单位产品工时（小时/件）", 1.5, "fb_hours", step=0.1)
            wage_rate = decimal_input("小时工资率（元/小时）", 20, "fb_wage", step=1)
        with col8:
            variable_overhead = decimal_input("变动制造费用分配率（元/小时）", 5, "fb_voh", step=0.5)
            fixed_overhead = money_input("每季度固定制造费用（元）", 20000, "fb_fixed", step=1000)
        with col9:
            depreciation = money_input("每季度折旧（元）", 8000, "fb_dep", step=500)
        st.subheader("现金预算", icon=":material/payments:")
        col10, col11, col12 = st.columns(3)
        with col10:
            collection_rates = st.text_input("销售回款比例序列", value="0.6,0.4", key="fb_collect")
            beginning_ar = money_input("期初应收账款（元）", 80000, "fb_begin_ar", step=1000)
            selling_admin = st.text_input(
                "各期销售管理费用（元）", value="30000,30000,30000,30000", key="fb_selling"
            )
        with col11:
            payment_rates = st.text_input("采购付款比例序列", value="0.7,0.3", key="fb_pay")
            beginning_ap = money_input("期初应付账款（元）", 30000, "fb_begin_ap", step=1000)
            equipment = st.text_input(
                "各期设备购置（元）", value="100000,0,0,0", key="fb_equipment"
            )
        with col12:
            initial_cash = money_input("期初现金（元）", 50000, "fb_initial_cash", step=1000)
            minimum_cash = money_input("最低现金（元）", 40000, "fb_minimum_cash", step=1000)
            taxes = st.text_input("各期所得税（元）", value="10000,10000,10000,10000", key="fb_tax")
        col13, col14 = st.columns(2)
        with col13:
            dividends = st.text_input("各期股利（元）", value="0,50000,0,0", key="fb_dividends")
        with col14:
            borrowing_rate = rate_input("季度借款利率", 2.0, "fb_borrow_rate", max_value=100)
        submitted = primary_button()
    if submitted:
        def build_budget():
            data = {
                "sales_volumes": parse_series(volumes_text, "各季度销售量"),
                "price": price,
                "beginning_fg": beginning_fg,
                "ending_fg_ratio": ending_fg_ratio,
                "ending_fg_last": ending_fg_last,
                "material_per_unit": material_per_unit,
                "material_price": material_price,
                "beginning_material": beginning_material,
                "ending_material_ratio": ending_material_ratio,
                "ending_material_last": ending_material_last,
                "hours_per_unit": hours_per_unit,
                "wage_rate": wage_rate,
                "variable_overhead_rate": variable_overhead,
                "fixed_overhead": fixed_overhead,
                "depreciation": depreciation,
                "collection_rates": parse_series(collection_rates, "销售回款比例"),
                "beginning_receivables": beginning_ar,
                "payment_rates": parse_series(payment_rates, "采购付款比例"),
                "beginning_payables": beginning_ap,
                "selling_admin": parse_series(selling_admin, "各期销售管理费用"),
                "equipment_purchases": parse_series(equipment, "各期设备购置"),
                "income_taxes": parse_series(taxes, "各期所得税"),
                "dividends": parse_series(dividends, "各期股利"),
                "initial_cash": initial_cash,
                "minimum_cash": minimum_cash,
                "borrowing_rate": borrowing_rate,
            }
            return fb.integrated_budget_result(data)

        calculate_and_store("fb_result", build_budget)
    demo_button("fb_result", lambda: fb.integrated_budget_result(fb._default_budget_data()))
    render_saved("fb_result")
