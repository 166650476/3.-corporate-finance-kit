"""财务管理本科全套综合计算器——程序入口。

运行方式：
    python main.py

主菜单包含 12 个财务管理模块、批量测算示例、导出文件信息。
所有计算均输出完整文字步骤，并自动追加到项目根目录 result.csv。
"""

from __future__ import annotations

import csv
import platform
from typing import List

from utils import BASE_DIR, CalcResult, pause, print_heading

import time_value
import project_invest
import capital_cost
import leverage
import capital_structure
import working_capital
import cost_analysis
import securities_valuation
import financial_analysis
import dividend_policy
import option_valuation
import financial_budget
import export


MODULES = [
    ("1", "资金时间价值", time_value.run),
    ("2", "项目投资管理", project_invest.run),
    ("3", "资本成本", capital_cost.run),
    ("4", "杠杆原理", leverage.run),
    ("5", "资本结构", capital_structure.run),
    ("6", "营运资金管理", working_capital.run),
    ("7", "成本管理", cost_analysis.run),
    ("8", "证券估值", securities_valuation.run),
    ("9", "财务分析", financial_analysis.run),
    ("10", "股利分配管理", dividend_policy.run),
    ("11", "期权基础估值", option_valuation.run),
    ("12", "财务预算", financial_budget.run),
]

APP_VERSION = "1.0.0"


def show_welcome() -> None:
    """显示欢迎页与操作提示。"""
    print_heading("财务管理本科全套综合计算器", "=")
    print("  适用对象：财务管理、会计学、金融学本科课程学习与作业书写参考")
    print("  覆盖范围：教材 12 大章节模块，60+ 类公式与决策模型")
    print("  使用提示：")
    print("    1. 每个模块均提供“一键例题演示”，可直接查看完整解题步骤；")
    print("    2. 手动输入时，比率按百分数输入（如 8% 输入 8）；")
    print("    3. 所有计算结果自动追加到 result.csv，Excel 可直接打开；")
    print("    4. 现金流时间轴、本量利图、杜邦瀑布图保存到 image 文件夹；")
    print("    5. 输入 0 可返回上一级菜单，Ctrl+C 可安全退出。")


def show_menu() -> None:
    """显示主菜单。"""
    print_heading("主菜单")
    for number, name, _ in MODULES:
        print(f"  {number:>2}. 模块{number}  {name}")
    print("  13. 批量多组测算示例（项目投资敏感性，批量导出 CSV）")
    print("  14. 查看导出文件与运行环境")
    print("  15. 公式与使用帮助")
    print("   0. 退出程序")


def show_help() -> None:
    """展示公式清单摘要与使用建议。"""
    print_heading("公式与使用帮助", "-")
    print("  资金时间价值：F=P(1+i)^n；P=F/(1+i)^n；年金现值/终值；预付×（1+i）；")
    print("                递延年金两阶段折现；永续年金 P=A/i；内插法求 i。")
    print("  项目投资：NPV；IRR；PI；ANCF；静态/动态回收期；年限不同用 EAA/ANCF。")
    print("  资本成本：CAPM；债务一般/贴现模式；股利增长模型；留存收益；WACC。")
    print("  杠杆：DOL=边际贡献/EBIT；DFL=EBIT/[EBIT-I-Dp/(1-T)]；DTL=DOL×DFL。")
    print("  资本结构：EPS 无差别点；公司价值 V=S+B，比较 WACC。")
    print("  营运资金：Baumol；Miller-Orr；应收账款机会成本；信用政策增量分析；")
    print("            EOQ；陆续供货；保险储备与再订货点。")
    print("  成本管理：本量利；直接材料/人工/变动制造费用差异；")
    print("            固定制造费用二差异/三差异；作业成本法。")
    print("  证券估值：债券价值与 YTM；零增长、固定股利、固定增长股票模型；股票 IRR。")
    print("  财务分析：偿债、营运、盈利、现金指标；传统杜邦与改进杜邦。")
    print("  股利分配：剩余股利；固定/稳定增长；固定支付率；低正常加额外；")
    print("            股票股利、股票分割、股票回购影响。")
    print("  期权：到期价值与净损益；单期二叉树复制原理与套期保值。")
    print("  财务预算：销售、生产、材料、人工、制造费用、产品成本、现金预算。")
    print("\n  详细公式推导与示例见 README.md。")
    print("  自动自检命令：python selftest.py")


def show_runtime_info() -> None:
    """显示运行环境、结果行数和图片数量。"""
    print_heading("导出文件与运行环境", "-")
    print(f"  项目目录：{BASE_DIR}")
    print(f"  结果文件：{export.get_export_path()}")
    print(f"  图片目录：{BASE_DIR / 'image'}")
    print(f"  程序版本：{APP_VERSION}")
    print(f"  Python 版本：{platform.python_version()}")
    print(f"  操作系统：{platform.platform()}")
    if export.get_export_path().exists():
        try:
            with export.get_export_path().open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
            print(f"  已导出记录：{max(len(rows) - 1, 0)} 条（不含表头）")
        except Exception as exc:
            print(f"  结果文件读取失败：{exc}")
    else:
        print("  已导出记录：0 条（尚未生成 result.csv）")
    images = sorted((BASE_DIR / "image").glob("*.png"))
    print(f"  已生成图片：{len(images)} 张")
    if images:
        print("  最近图片：")
        for path in images[-3:]:
            print(f"    - {path.name}")
    print("\n  可用命令：")
    print("    python main.py       启动交互程序")
    print("    python selftest.py   运行 50 项自动自检")


def batch_sensitivity_demo() -> None:
    """批量多组测算示例：不同折现率下的项目 NPV/ANCF。"""
    print_heading("批量多组测算示例：折现率敏感性", "★")
    initial = 1000000.0
    cash_flows = [280000, 300000, 320000, 300000, 280000]
    rates = [0.06, 0.08, 0.10, 0.12, 0.14]
    results: List[CalcResult] = []
    for rate in rates:
        value = project_invest.npv(rate, initial, cash_flows)
        ancf = project_invest.annual_net_cash_flow(rate, initial, cash_flows)
        pi = project_invest.profitability_index(rate, initial, cash_flows)
        result = CalcResult(
            "批量测算 项目投资敏感性",
            f"折现率 {rate * 100:.0f}% 情景",
            {"初始投资": f"{initial:,.2f} 元", "折现率": f"{rate * 100:.2f}%"},
            [f"NPV=-{initial:,.2f}+Σ[CF_t/(1+{rate:.2%})^t]={value:,.2f} 元。"],
            {
                "净现值 NPV": f"{value:,.2f} 元",
                "现值指数 PI": f"{pi:.4f}",
                "年金净流量 ANCF": f"{ancf:,.2f} 元/年",
                "决策": "可行" if value > 0 else "不可行",
            },
            ["批量情景用于观察折现率变化对项目可行性的影响。"],
        )
        results.append(result)
    export.export_scenarios(results, display=True)
    print("\n[批量测算说明] 5 组结果已一次性追加到 result.csv，可在 Excel 中排序、筛选和制图。")


def main() -> None:
    """主程序循环。"""
    show_welcome()
    while True:
        show_menu()
        try:
            choice = input("\n请选择功能：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出财务管理计算器，再见！")
            return
        if choice == "0":
            print("\n感谢使用！计算结果保存在 result.csv，图片保存在 image 文件夹。")
            return
        action = next((func for number, _, func in MODULES if number == choice), None)
        if action is not None:
            try:
                action()
            except KeyboardInterrupt:
                print("\n[提示] 已中断当前模块，返回主菜单。")
            except Exception as exc:
                print(f"\n[模块运行异常] {exc}")
            continue
        if choice == "13":
            try:
                batch_sensitivity_demo()
            except Exception as exc:
                print(f"\n[批量测算失败] {exc}")
            pause()
        elif choice == "14":
            show_runtime_info()
            pause()
        elif choice == "15":
            show_help()
            pause()
        else:
            print("[提示] 无效选项，请输入 0~15。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已退出。")
