"""Streamlit 界面公共组件。

负责输入解析、结果执行与保存、完整计算书渲染、图表/表格展示和 CSV 下载。
计算公式全部复用原有 12 个业务模块，本文件不重复实现财务公式。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional

import pandas as pd
import streamlit as st

from export import append_result, get_export_path
from utils import CalcResult, ValidationError, format_value


MODULE_DESCRIPTIONS = {
    "模块1 资金时间价值": "复利、普通/预付/递延/永续年金与内插法求折现率。",
    "模块2 项目投资管理": "NPV、IRR、PI、ANCF、回收期与互斥方案比选。",
    "模块3 资本成本": "CAPM、债务成本、普通股、留存收益与 WACC。",
    "模块4 杠杆原理": "DOL、DFL、DTL 及风险放大效应。",
    "模块5 资本结构": "EPS 无差别点与公司价值分析法。",
    "模块6 营运资金管理": "现金、应收账款、信用政策与存货管理。",
    "模块7 成本管理": "本量利、标准成本差异与作业成本法。",
    "模块8 证券估值": "债券价值、YTM 与股票估值/内部收益率。",
    "模块9 财务分析": "四大类财务指标与传统/改进杜邦分析。",
    "模块10 股利分配管理": "四种股利政策与股票股利、分割、回购。",
    "模块11 期权基础估值": "期权损益、复制原理与套期保值。",
    "模块12 财务预算": "七张季度预算表联动编制。",
}


def parse_series(text: str, label: str, *, min_length: int = 1) -> List[float]:
    """解析逗号分隔的数字序列。"""
    normalized = (text or "").replace("，", ",").replace("、", ",")
    pieces = [piece.strip() for piece in normalized.split(",") if piece.strip()]
    if len(pieces) < min_length:
        raise ValueError(f"{label}至少需要 {min_length} 个数字，请用英文逗号分隔。")
    try:
        return [float(piece) for piece in pieces]
    except ValueError as exc:
        raise ValueError(f"{label}中包含非数字内容，请检查输入。") from exc


def safe_filename(text: str) -> str:
    """清理文件名中的非法字符。"""
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", text).strip(" .")
    return cleaned or "finance_result"


def calculate_and_store(
    session_key: str,
    builder: Callable[[], CalcResult],
    *,
    show_success: bool = True,
) -> Optional[CalcResult]:
    """执行计算、追加 CSV 并保存到 session_state。"""
    try:
        result = builder()
        if not isinstance(result, CalcResult):
            raise TypeError("计算函数必须返回 CalcResult。")
        st.session_state[session_key] = result
        st.session_state[f"{session_key}_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            append_result(result)
            st.session_state[f"{session_key}_exported"] = True
        except Exception as exc:
            st.session_state[f"{session_key}_exported"] = False
            st.warning(f"结果已生成，但写入 result.csv 失败：{exc}", icon=":material/warning:")
        if show_success:
            st.toast("计算完成，结果已保存", icon=":material/check_circle:")
        return result
    except (ValidationError, ValueError, ZeroDivisionError) as exc:
        st.error(str(exc), icon=":material/error:")
        return None
    except Exception as exc:
        st.error(f"计算失败：{exc}", icon=":material/error:")
        return None


def render_saved(session_key: str) -> None:
    """若当前模块已有结果，则渲染最近一次结果。"""
    result = st.session_state.get(session_key)
    if isinstance(result, CalcResult):
        render_result(result, session_key)


def _metric_keys(result: CalcResult) -> List[str]:
    """选择更适合作为 KPI 卡片的结果字段。"""
    preferred = [
        "净现值 NPV",
        "内含收益率 IRR",
        "现值指数 PI",
        "年金净流量 ANCF",
        "WACC",
        "必要收益率（资本成本）",
        "普通股资本成本 Ks",
        "经营杠杆系数 DOL",
        "财务杠杆系数 DFL",
        "总杠杆系数 DTL",
        "每股收益无差别点 EBIT*",
        "推荐方案",
        "推荐资本结构",
        "最大公司价值 V",
        "最佳现金持有量 C*",
        "经济订货批量 Q*",
        "最低相关总成本",
        "息税前利润 EBIT",
        "盈亏临界点销售量",
        "安全边际率",
        "债券价值 V",
        "到期收益率 YTM",
        "股票价值 V",
        "净资产收益率 ROE",
        "传统杜邦乘积校验",
        "改进杜邦 ROE",
        "股利总额",
        "推荐筹资方案",
        "净损益",
        "到期日价值",
        "期权理论价值",
        "期末现金余额",
        "单位产品成本",
        "复利终值 F",
        "复利现值 P",
        "递延年金现值 P",
        "永续年金现值 P",
    ]
    keys = [key for key in preferred if key in result.outcomes]
    for key in result.outcomes:
        if key not in keys and "图片" not in key and len(keys) < 4:
            keys.append(key)
    return keys[:4]


def _is_image_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.lower().endswith((".png", ".jpg", ".jpeg")) and Path(value).exists()


def render_result(result: CalcResult, session_key: str) -> None:
    """用原生 Streamlit 组件展示完整计算书。"""
    with st.container(border=True):
        st.caption(result.module)
        st.subheader(result.title, anchor=False)
        description = MODULE_DESCRIPTIONS.get(result.module)
        if description:
            st.caption(description)
        metric_keys = _metric_keys(result)
        if metric_keys:
            columns = st.columns(len(metric_keys))
            for column, key in zip(columns, metric_keys):
                with column:
                    with st.container(border=True):
                        st.metric(key, format_value(result.outcomes[key]))

    st.subheader("完整解题步骤", icon=":material/format_list_numbered:")
    step_lines = [
        f"**{index}.** {step}" for index, step in enumerate(result.steps, start=1)
    ]
    if step_lines:
        with st.container(border=True):
            st.markdown("\n\n".join(step_lines))
    else:
        st.caption("本次计算未提供文字步骤。")

    with st.expander("查看全部结果", expanded=True, icon=":material/table_chart:"):
        outcome_rows = [
            {"项目": key, "结果": format_value(value)}
            for key, value in result.outcomes.items()
            if not _is_image_value(value)
        ]
        if outcome_rows:
            st.dataframe(pd.DataFrame(outcome_rows), hide_index=True)
        else:
            st.caption("无结果字段。")

    if result.tables:
        st.subheader("预算/计算明细表", icon=":material/dataset:")
        for index, (title, table) in enumerate(result.tables):
            with st.expander(title, expanded=index == 0, icon=":material/table_view:"):
                try:
                    st.dataframe(table, hide_index=True)
                except Exception:
                    st.write(table)

    images = [(key, value) for key, value in result.outcomes.items() if _is_image_value(value)]
    if images:
        st.subheader("图表", icon=":material/show_chart:")
        for key, path in images:
            st.image(path, caption=key)

    if result.notes:
        st.subheader("结论与提示", icon=":material/lightbulb:")
        for note in result.notes:
            if any(word in note for word in ("风险", "不可行", "无法", "谨慎", "注意")):
                st.warning(note, icon=":material/warning:")
            else:
                st.info(note, icon=":material/info:")

    with st.container(horizontal=True, horizontal_alignment="right"):
        row_df = pd.DataFrame([result.as_csv_row()])
        st.download_button(
            "下载本次结果",
            data=row_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{safe_filename(result.title)}.csv",
            mime="text/csv",
            icon=":material/download:",
            key=f"download_{session_key}",
        )
    exported = st.session_state.get(f"{session_key}_exported")
    saved_time = st.session_state.get(f"{session_key}_time", "")
    if exported is False:
        st.caption("本次结果尚未写入历史 CSV，请检查文件是否被 Excel 占用。")
    else:
        st.caption(f"已追加到 {get_export_path().name} · {saved_time}")


def page_header(module_number: str, title: str, description: str) -> None:
    """模块页标题。"""
    st.caption(f"模块 {module_number}")
    st.title(title, anchor=False)
    st.write(description)


def demo_button(
    session_key: str,
    builder: Callable[[], CalcResult],
    *,
    label: str = "运行本页示例",
) -> None:
    """运行本页固定示例。"""
    if st.button(label, icon=":material/play_arrow:", key=f"demo_{session_key}"):
        calculate_and_store(session_key, builder)


def all_results_bytes() -> Optional[bytes]:
    """读取历史 result.csv 的下载字节。"""
    path = get_export_path()
    if not path.exists():
        return None
    return path.read_bytes()
