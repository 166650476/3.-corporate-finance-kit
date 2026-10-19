"""CSV 导出模块。

每次计算都以追加方式写入项目根目录的 result.csv：
- 使用 UTF-8 BOM 编码，Excel 双击打开不会出现中文乱码；
- 使用 csv 标准库追加，单次记录与批量情景测算均可导出；
- 文件不存在时自动写入表头。
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List, Optional

from utils import BASE_DIR, CalcResult


RESULT_FILE = BASE_DIR / "result.csv"
FIELDNAMES = ["记录时间", "模块", "计算项目", "输入参数", "计算结论", "备注"]


def _ensure_file() -> None:
    """若结果文件不存在或为空，则写入带 BOM 的表头。"""
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not RESULT_FILE.exists() or RESULT_FILE.stat().st_size == 0:
        with RESULT_FILE.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()


def append_result(result: CalcResult) -> Path:
    """追加一条计算结果并返回 result.csv 路径。"""
    if not isinstance(result, CalcResult):
        raise TypeError("append_result 只接受 CalcResult 对象。")
    return append_results([result])


def append_results(results: Iterable[CalcResult]) -> Path:
    """批量追加多条计算结果，适用于多方案比选与敏感性分析。"""
    rows: List[dict] = []
    for result in results:
        if not isinstance(result, CalcResult):
            raise TypeError("批量导出列表中存在非 CalcResult 对象。")
        rows.append(result.as_csv_row())
    if not rows:
        raise ValueError("没有可导出的计算结果。")

    _ensure_file()
    with RESULT_FILE.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writerows(rows)
    return RESULT_FILE


def append_batch(results: Iterable[CalcResult]) -> Path:
    """append_results 的语义化别名，强调“多组测算批量导出”。"""
    return append_results(results)


def export_scenarios(scenarios: Iterable[CalcResult], *, display: bool = True) -> Path:
    """批量导出多组情景，并可选择先逐条展示。"""
    items = list(scenarios)
    if display:
        from utils import show_result

        for result in items:
            show_result(result, auto_export=False)
    path = append_batch(items)
    print(f"\n[批量导出完成] 共 {len(items)} 组结果 → {path}")
    return path


def get_export_path() -> Path:
    """返回当前 CSV 路径，供界面提示。"""
    return RESULT_FILE


def reset_result_file() -> Path:
    """清空历史结果并重建表头；仅供自检或用户主动维护使用。"""
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RESULT_FILE.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
    return RESULT_FILE
