"""财务管理综合计算器——Streamlit 图形界面入口。

本地运行：
    streamlit run app.py

Windows 用户可直接双击项目根目录的“启动财务计算器.bat”。
"""

from __future__ import annotations

import csv
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import streamlit as st

from export import get_export_path
from ui_core import all_results_bytes
import ui_pages


st.set_page_config(
    page_title="财务管理综合计算器",
    page_icon=":material/account_balance:",
    layout="wide",
    initial_sidebar_state="expanded",
)


MODULE_CARDS: List[Tuple[str, str, str, str]] = [
    ("1 资金时间价值", "复利与年金、内推法", "复利、年金、递延/永续年金与内插法。", "schedule"),
    ("2 项目投资管理", "NPV / IRR / 回收期", "全面评价与互斥方案比选。", "trending_up"),
    ("3 资本成本", "CAPM / WACC", "债务、股权、留存收益与加权平均成本。", "percent"),
    ("4 杠杆原理", "DOL / DFL / DTL", "经营、财务和总杠杆与风险解读。", "balance"),
    ("5 资本结构", "EPS / 公司价值", "无差别点和公司价值最大化决策。", "account_tree"),
    ("6 营运资金管理", "现金 / 应收 / 存货", "Baumol、Miller-Orr、EOQ 与信用政策。", "inventory_2"),
    ("7 成本管理", "本量利 / 差异分析", "CVP、标准成本差异与作业成本法。", "factory"),
    ("8 证券估值", "债券 / 股票", "债券 YTM 与股票估值、内部收益率。", "candlestick_chart"),
    ("9 财务分析", "指标 / 杜邦", "四大类指标与改进杜邦瀑布图。", "analytics"),
    ("10 股利分配管理", "政策 / 回购", "四种股利政策与股票操作影响。", "payments"),
    ("11 期权基础估值", "损益 / 复制", "到期损益、二叉树复制与套期保值。", "ssid_chart"),
    ("12 财务预算", "七表联动", "销售到现金预算的完整季度联动。", "table_view"),
]

PAGES: Dict[str, Optional[Callable[[], None]]] = {
    "概览": None,
    "1 资金时间价值": ui_pages.page_time_value,
    "2 项目投资管理": ui_pages.page_project,
    "3 资本成本": ui_pages.page_capital_cost,
    "4 杠杆原理": ui_pages.page_leverage,
    "5 资本结构": ui_pages.page_capital_structure,
    "6 营运资金管理": ui_pages.page_working_capital,
    "7 成本管理": ui_pages.page_cost_analysis,
    "8 证券估值": ui_pages.page_securities,
    "9 财务分析": ui_pages.page_financial_analysis,
    "10 股利分配管理": ui_pages.page_dividend,
    "11 期权基础估值": ui_pages.page_option,
    "12 财务预算": ui_pages.page_budget,
}


def _goto(page_name: str) -> None:
    st.session_state["nav"] = page_name


def _result_row_count() -> int:
    path = get_export_path()
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return max(sum(1 for _ in csv.reader(handle)) - 1, 0)
    except Exception:
        return 0


def render_sidebar() -> str:
    with st.sidebar:
        st.title("财务管理计算器", anchor=False)
        st.caption("本科全套 · 本地运行 · 计算书自动导出")
        page = st.radio(
            "模块导航",
            options=list(PAGES),
            key="nav",
            label_visibility="collapsed",
        )
        st.caption("比率按百分数输入，例如 8% 输入 8。")
        with st.expander("结果文件", icon=":material/folder_open:"):
            st.caption(f"已保存 {_result_row_count()} 条计算结果")
            all_data = all_results_bytes()
            if all_data:
                st.download_button(
                    "下载全部历史结果",
                    data=all_data,
                    file_name="财务管理计算结果.csv",
                    mime="text/csv",
                    icon=":material/download:",
                    width="stretch",
                )
            else:
                st.caption("完成第一次计算后会生成 result.csv。")
            st.caption(f"文件位置：{get_export_path()}")
        st.caption("计算结果仅供课程学习与作业校验参考。")
    return str(page)


def render_home() -> None:
    with st.container(border=True):
        st.badge("本地桌面工具", icon=":material/computer:", color="green")
        st.title("财务管理综合计算器", anchor=False)
        st.write(
            "覆盖本科财务管理 12 个章节模块。选择模块、填写参数，即可获得"
            "完整公式步骤、结果表格、图表和可下载的 Excel 兼容 CSV。"
        )
    st.space("small")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.metric("章节模块", "12", border=False)
    with c2:
        with st.container(border=True):
            st.metric("公式/模型", "60+", border=False)
    with c3:
        with st.container(border=True):
            st.metric("历史结果", f"{_result_row_count()} 条", border=False)
    with c4:
        with st.container(border=True):
            st.metric("图表类型", "3", border=False)

    st.subheader("选择模块", icon=":material/apps:")
    for row_start in range(0, len(MODULE_CARDS), 3):
        columns = st.columns(3)
        for column, card in zip(columns, MODULE_CARDS[row_start:row_start + 3]):
            page_name, subtitle, description, icon = card
            with column:
                with st.container(border=True):
                    st.markdown(f"#### :material/{icon}: {page_name}")
                    st.caption(subtitle)
                    st.write(description)
                    st.button(
                        "进入模块",
                        key=f"home_go_{page_name}",
                        icon=":material/arrow_forward:",
                        on_click=_goto,
                        args=(page_name,),
                        width="stretch",
                    )

    with st.expander("使用说明", expanded=False, icon=":material/help:"):
        st.markdown(
            """
1. 所有金额不需要填写千分位；比率填写百分数。
2. 现金流量、季度序列用英文逗号分隔，例如 `-100000,30000,35000`。
3. 点击“开始计算”后，结果会自动追加到项目根目录的 `result.csv`。
4. 每个模块都有“运行本页示例”，可一键查看标准例题。
5. 图表写入项目 `image` 文件夹，同时在页面中直接展示。
6. 关闭启动窗口即可停止本地服务。
            """
        )


def main() -> None:
    st.session_state.setdefault("nav", "概览")
    page_name = render_sidebar()
    page = PAGES.get(page_name)
    if page is None:
        render_home()
    else:
        try:
            page()
        except Exception as exc:
            st.error(f"页面运行失败：{exc}", icon=":material/error:")
            with st.expander("错误详情"):
                st.exception(exc)
    st.caption(
        f"财务管理综合计算器 · 本地运行 · {datetime.now().strftime('%Y-%m-%d')}"
    )


if __name__ == "__main__":
    main()
