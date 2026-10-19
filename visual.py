"""可视化模块。

提供三类核心图形：
1. 现金流时间轴（资金时间价值、项目投资）；
2. 本量利分析图（收入、成本、利润）；
3. 杜邦分析瀑布图（ROA 与财务杠杆贡献）。

所有图片自动保存到项目 image 文件夹。使用 Agg 后端，VSCode 下无需弹窗即可出图。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union

import matplotlib

matplotlib.use("Agg")  # 无界面后端，保证在 VSCode/服务器环境均可保存图片

import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter

from utils import IMAGE_DIR


# ---------------------------------------------------------------------------
# 中文字体设置：优先使用 Windows 自带雅黑/黑体，并兼容其他系统
# ---------------------------------------------------------------------------
def _configure_chinese_font() -> str:
    """检测可用中文字体，解决 matplotlib 中文显示为方框的问题。"""
    candidates = [
        "Microsoft YaHei",
        "Microsoft YaHei UI",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "PingFang SC",
        "Arial Unicode MS",
    ]
    available = {font.name for font in font_manager.fontManager.ttflist}

    # Windows 字体缓存偶尔不完整，主动注册常见字体文件。
    windows_font_dir = Path("C:/Windows/Fonts")
    font_files = [
        windows_font_dir / "msyh.ttc",
        windows_font_dir / "msyhbd.ttc",
        windows_font_dir / "simhei.ttf",
        windows_font_dir / "simsun.ttc",
    ]
    for font_file in font_files:
        if font_file.exists():
            try:
                font_manager.fontManager.addfont(str(font_file))
                available.add(font_manager.FontProperties(fname=str(font_file)).get_name())
            except Exception:
                pass

    selected = next((name for name in candidates if name in available), "DejaVu Sans")
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [selected, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False  # 修复负号显示为方框的问题
    return selected


CHINESE_FONT = _configure_chinese_font()


def _safe_filename(name: Optional[str], prefix: str) -> Path:
    """生成不会覆盖旧图片的绝对路径。"""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    raw = name or prefix
    safe = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", raw).strip("_") or prefix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    return IMAGE_DIR / f"{safe}_{timestamp}.png"


def _save(fig: plt.Figure, filename: Optional[str], prefix: str) -> Path:
    """保存图片、关闭画布并返回路径。"""
    path = _safe_filename(filename, prefix)
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[图片已保存] {path}")
    return path


# ---------------------------------------------------------------------------
# 1. 现金流时间轴
# ---------------------------------------------------------------------------
def plot_cash_flow(
    cash_flows: Union[Sequence[float], Mapping[int, float]],
    title: str = "现金流时间轴",
    filename: Optional[str] = None,
    *,
    unit: str = "元",
) -> Path:
    """绘制现金流时间轴。

    参数:
        cash_flows: 按 t=0,1,2... 排列的现金流序列，或 {期数: 金额} 字典。
                     流出用负数、流入用正数表示。
        title: 图标题。
        filename: 图片文件名前缀，可省略。
        unit: 金额单位，用于标注。
    """
    if isinstance(cash_flows, Mapping):
        periods = sorted(cash_flows)
        values = [float(cash_flows[p]) for p in periods]
    else:
        values = [float(value) for value in cash_flows]
        periods = list(range(len(values)))
    if not values:
        raise ValueError("现金流序列不能为空。")
    if len(periods) != len(values):
        raise ValueError("期数与现金流数量不一致。")

    fig, ax = plt.subplots(figsize=(max(8.0, len(values) * 0.85), 4.8))
    max_abs = max(abs(value) for value in values)
    span = max_abs if max_abs > 0 else 1.0
    ax.axhline(0, color="#333333", linewidth=1.3, zorder=1)

    for period, value in zip(periods, values):
        color = "#2E8B57" if value >= 0 else "#C0392B"
        direction = 1 if value >= 0 else -1
        arrow_end = direction * (abs(value) / span * 0.82 + 0.08)
        ax.annotate(
            "",
            xy=(period, arrow_end),
            xytext=(period, 0),
            arrowprops={"arrowstyle": "-|>", "color": color, "lw": 2.2},
            zorder=3,
        )
        va = "bottom" if value >= 0 else "top"
        offset = 0.04 if value >= 0 else -0.04
        ax.text(
            period,
            arrow_end + offset,
            f"{value:,.2f}",
            ha="center",
            va=va,
            fontsize=9,
            color=color,
            fontweight="bold",
        )
        ax.plot(period, 0, marker="o", color="#333333", markersize=5, zorder=4)
        ax.text(period, -1.12, f"t={period}", ha="center", va="top", fontsize=9)

    ax.set_xlim(min(periods) - 0.7, max(periods) + 0.7)
    ax.set_ylim(-1.22, 1.22)
    ax.set_yticks([])
    ax.set_xticks([])
    for spine in ("left", "right", "top", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.set_title(f"{title}\n（向上为现金流入，向下为现金流出；单位：{unit}）", fontsize=13)
    return _save(fig, filename, "cash_flow")


# ---------------------------------------------------------------------------
# 2. 本量利分析图
# ---------------------------------------------------------------------------
def plot_cvp(
    unit_price: float,
    unit_variable_cost: float,
    fixed_cost: float,
    actual_quantity: float,
    *,
    title: str = "本量利分析图",
    filename: Optional[str] = None,
) -> Path:
    """绘制收入线、总成本线、固定成本线及利润图。"""
    price = float(unit_price)
    variable_cost = float(unit_variable_cost)
    fixed = float(fixed_cost)
    quantity = max(float(actual_quantity), 0.0)
    contribution = price - variable_cost
    if contribution <= 0:
        raise ValueError("单位售价必须大于单位变动成本，否则不存在盈亏临界点。")
    break_even = fixed / contribution
    q_max = max(quantity * 1.35, break_even * 1.5, 10.0)
    q = np.linspace(0, q_max, 400)
    revenue = price * q
    total_cost = fixed + variable_cost * q
    profit = revenue - total_cost

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))
    ax1.plot(q, revenue, color="#1f77b4", linewidth=2.2, label="销售收入")
    ax1.plot(q, total_cost, color="#d62728", linewidth=2.2, label="总成本")
    ax1.axhline(fixed, color="#7f7f7f", linewidth=1.5, linestyle="--", label="固定成本")
    ax1.axvline(break_even, color="#2ca02c", linewidth=1.2, linestyle=":", label="盈亏临界点")
    ax1.scatter([break_even], [price * break_even], color="#2ca02c", s=60, zorder=5)
    ax1.annotate(
        f"保本点\nQ={break_even:,.2f}",
        xy=(break_even, price * break_even),
        xytext=(break_even + q_max * 0.06, price * break_even * 0.62),
        arrowprops={"arrowstyle": "->", "color": "#2ca02c"},
        fontsize=9,
    )
    if quantity > 0:
        ax1.axvline(quantity, color="#ff7f0e", linestyle="--", linewidth=1.2, label="实际销量")
        ax1.scatter([quantity], [price * quantity], color="#ff7f0e", s=50, zorder=5)
    ax1.fill_between(q, revenue, total_cost, where=revenue >= total_cost, color="#2ca02c", alpha=0.12)
    ax1.fill_between(q, revenue, total_cost, where=revenue < total_cost, color="#d62728", alpha=0.10)
    ax1.set_xlabel("销售量（件）")
    ax1.set_ylabel("金额（元）")
    ax1.set_title("收入—成本—业务量关系")
    ax1.grid(alpha=0.25)
    ax1.legend(loc="upper left", fontsize=8)

    ax2.plot(q, profit, color="#9467bd", linewidth=2.2)
    ax2.axhline(0, color="#333333", linewidth=1.1)
    ax2.axvline(break_even, color="#2ca02c", linewidth=1.2, linestyle=":")
    if quantity > 0:
        actual_profit = (price - variable_cost) * quantity - fixed
        ax2.scatter([quantity], [actual_profit], color="#ff7f0e", s=55, zorder=5)
        ax2.annotate(
            f"实际利润\n{actual_profit:,.2f}",
            xy=(quantity, actual_profit),
            xytext=(quantity * 0.72, actual_profit * 0.55 if actual_profit != 0 else 10),
            arrowprops={"arrowstyle": "->", "color": "#ff7f0e"},
            fontsize=9,
        )
    ax2.set_xlabel("销售量（件）")
    ax2.set_ylabel("息税前利润（元）")
    ax2.set_title("利润随销量变化")
    ax2.grid(alpha=0.25)

    fig.suptitle(title, fontsize=14)
    fig.tight_layout()
    return _save(fig, filename, "cvp")


# ---------------------------------------------------------------------------
# 3. 杜邦分析瀑布图
# ---------------------------------------------------------------------------
def plot_dupont_waterfall(
    net_profit_margin: float,
    total_asset_turnover: float,
    equity_multiplier: float,
    *,
    title: str = "杜邦分析瀑布图",
    filename: Optional[str] = None,
) -> Path:
    """绘制传统杜邦体系的加法式瀑布拆解。

    ROE = 营业净利率 × 总资产周转率 × 权益乘数
        = ROA + ROA × (权益乘数 - 1)
    其中第一项是总资产净利率（经营效率），第二项是财务杠杆贡献。
    """
    npm = float(net_profit_margin)
    turnover = float(total_asset_turnover)
    multiplier = float(equity_multiplier)
    roa = npm * turnover
    leverage_contribution = roa * (multiplier - 1)
    roe = roa + leverage_contribution

    labels = ["总资产净利率\nROA", "财务杠杆贡献", "净资产收益率\nROE"]
    values = [roa, leverage_contribution, roe]
    # 瀑布图每根柱子的起点：第一项从 0 开始，杠杆贡献从 ROA 到 ROE，
    # 最后一项从 0 到 ROE；同时兼容负的杠杆贡献或负 ROE。
    bottoms = [min(0.0, roa), min(roa, roe), min(0.0, roe)]
    colors = ["#4C78A8", "#F58518", "#54A24B"]

    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    bars = ax.bar(labels, [abs(v) for v in values], bottom=bottoms, color=colors, width=0.55)
    for index, (bar, value, bottom) in enumerate(zip(bars, values, bottoms)):
        y = bottom + abs(value) / 2
        sign = "+" if index == 1 and value >= 0 else ""
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            f"{sign}{value * 100:.2f}%",
            ha="center",
            va="center",
            fontsize=10,
            color="white",
            fontweight="bold",
        )
        if index < len(values) - 1:
            level = roa if index == 0 else roe
            ax.plot(
                [bar.get_x() + bar.get_width(), bar.get_x() + bar.get_width() + 0.45],
                [level, level],
                color="#999999",
                linewidth=1.0,
                linestyle="--",
            )
    ax.axhline(0, color="#333333", linewidth=1.0)
    ax.set_ylabel("比率")
    ax.set_title(
        f"{title}\nROE = 营业净利率 × 总资产周转率 × 权益乘数",
        fontsize=12,
    )
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=1))
    ax.grid(axis="y", alpha=0.2)
    ax.text(
        0.01,
        0.97,
        f"营业净利率：{npm * 100:.2f}%\n总资产周转率：{turnover:.3f} 次\n权益乘数：{multiplier:.3f}",
        transform=ax.transAxes,
        va="top",
        fontsize=8.5,
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#F7F7F7", "edgecolor": "#CCCCCC"},
    )
    fig.tight_layout()
    return _save(fig, filename, "dupont_waterfall")


def plot_cash_flow_demo(filename: Optional[str] = None) -> Path:
    """内置现金流示例，便于快速验证中文字体与绘图环境。"""
    return plot_cash_flow(
        [-100000, 30000, 35000, 40000, 45000],
        title="项目现金流时间轴示例",
        filename=filename,
    )
