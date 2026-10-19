"""Streamlit 图形界面的自动自检。

运行：python selftest_ui.py

使用 Streamlit 官方 AppTest，在无浏览器环境下依次打开 12 个模块，
点击每个页面的“运行本页示例”，检查是否有页面异常。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from streamlit.testing.v1 import AppTest

import export
import ui_pages


PAGES = [
    ("1 资金时间价值", "demo_tv_result"),
    ("2 项目投资管理", "demo_pi_result"),
    ("3 资本成本", "demo_cc_result"),
    ("4 杠杆原理", "demo_lv_result"),
    ("5 资本结构", "demo_cs_result"),
    ("6 营运资金管理", "demo_wc_result"),
    ("7 成本管理", "demo_ca_result"),
    ("8 证券估值", "demo_sv_result"),
    ("9 财务分析", "demo_fa_result"),
    ("10 股利分配管理", "demo_dp_result"),
    ("11 期权基础估值", "demo_ov_result"),
    ("12 财务预算", "demo_fb_result"),
]

TYPE_OPTIONS = {
    "1 资金时间价值": ("tv_kind", ui_pages.TV_TYPES),
    "2 项目投资管理": ("pi_kind", ui_pages.PROJECT_TYPES),
    "3 资本成本": ("cc_kind", ui_pages.COST_TYPES),
    "4 杠杆原理": (None, []),
    "5 资本结构": ("cs_kind", ui_pages.CAPITAL_STRUCTURE_TYPES),
    "6 营运资金管理": ("wc_kind", ui_pages.WC_TYPES),
    "7 成本管理": ("ca_kind", ui_pages.COST_ANALYSIS_TYPES),
    "8 证券估值": ("sv_kind", ui_pages.SECURITY_TYPES),
    "9 财务分析": (None, []),
    "10 股利分配管理": ("dp_kind", ui_pages.DIVIDEND_TYPES),
    "11 期权基础估值": ("ov_kind", ui_pages.OPTION_TYPES),
    "12 财务预算": (None, []),
}


def submit_current_form(at: AppTest, context: str) -> None:
    """找到当前页面的表单提交按钮并点击。"""
    buttons = [
        button for button in at.button if button.key.startswith("FormSubmitter:")
    ]
    if not buttons:
        raise AssertionError(f"{context} 未找到表单提交按钮")
    buttons[0].click().run()
    if at.exception:
        raise AssertionError(f"{context} 表单计算异常：{list(at.exception)}")


def main() -> None:
    original_path = export.RESULT_FILE
    with tempfile.TemporaryDirectory() as temp_dir:
        export.RESULT_FILE = Path(temp_dir) / "ui_test_result.csv"
        try:
            at = AppTest.from_file("app.py", default_timeout=120).run()
            if at.exception:
                raise AssertionError(f"首页加载异常：{list(at.exception)}")
            print("[通过] 首页")

            home_buttons = [
                button for button in at.button if button.key == "home_go_1 资金时间价值"
            ]
            if not home_buttons:
                raise AssertionError("首页未找到模块入口按钮")
            home_buttons[0].click().run()
            if at.exception or at.sidebar.radio[0].value != "1 资金时间价值":
                raise AssertionError("首页模块入口按钮跳转失败")
            print("[通过] 首页模块入口按钮")

            for page_name, demo_key in PAGES:
                at.sidebar.radio[0].set_value(page_name).run()
                if at.exception:
                    raise AssertionError(f"{page_name} 页面异常：{list(at.exception)}")
                submit_current_form(at, f"{page_name} 默认表单")

                buttons = [button for button in at.button if button.key == demo_key]
                if not buttons:
                    raise AssertionError(f"{page_name} 未找到示例按钮 {demo_key}")
                buttons[0].click().run()
                if at.exception:
                    raise AssertionError(
                        f"{page_name} 示例计算异常：{list(at.exception)}"
                    )

                kind_key, options = TYPE_OPTIONS[page_name]
                for option in options:
                    at.sidebar.radio[0].set_value(page_name).run()
                    at.selectbox(key=kind_key).select(option).run()
                    if at.exception:
                        raise AssertionError(
                            f"{page_name} / {option} 选择异常：{list(at.exception)}"
                        )
                    if page_name == "8 证券估值" and option == "股票内部收益率":
                        for model in ui_pages.STOCK_IRR_MODELS:
                            at.sidebar.radio[0].set_value(page_name).run()
                            at.selectbox(key=kind_key).select(option).run()
                            at.selectbox(key="sv_irr_model").select(model).run()
                            submit_current_form(
                                at, f"{page_name} / {option} / {model}"
                            )
                    else:
                        submit_current_form(at, f"{page_name} / {option}")
                suffix = f" · {len(options)} 种类型" if options else ""
                print(f"[通过] {page_name} · 表单 + 示例{suffix}")
        finally:
            export.RESULT_FILE = original_path

    print("\n界面自检全部通过：首页 + 12 个模块示例。")


if __name__ == "__main__":
    main()
