"""公共工具模块。

集中提供计算结果数据结构、参数校验、控制台输入、统一展示和格式化函数。
业务模块只负责计算，界面与导出逻辑在此复用。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


# 项目根目录：无论从哪个工作目录启动，图片和 CSV 都保存到项目内部。
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "image"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)


class ValidationError(ValueError):
    """参数不合法时抛出的业务异常，用于向用户展示友好的中文提示。"""


@dataclass
class CalcResult:
    """一次财务计算的标准结果。

    module: 所属模块；title: 计算项目；parameters: 已知参数；
    steps: 完整文字解题步骤；outcomes: 最终结果；notes: 提示；
    tables: (表格标题, DataFrame) 列表。
    """

    module: str
    title: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)
    outcomes: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    tables: List[Tuple[str, Any]] = field(default_factory=list)

    def add_step(self, text: str) -> "CalcResult":
        """追加一条解题步骤并返回自身。"""
        self.steps.append(text)
        return self

    def add_note(self, text: str) -> "CalcResult":
        """追加一条说明或提示。"""
        self.notes.append(text)
        return self

    def add_table(self, title: str, dataframe: Any) -> "CalcResult":
        """追加一张表格结果。"""
        self.tables.append((title, dataframe))
        return self

    def put(self, name: str, value: Any) -> "CalcResult":
        """写入一个最终结果。"""
        self.outcomes[name] = value
        return self

    def as_csv_row(self, timestamp: Optional[str] = None) -> Dict[str, str]:
        """转换为 result.csv 的一行记录。"""
        return {
            "记录时间": timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "模块": self.module,
            "计算项目": self.title,
            "输入参数": format_mapping(self.parameters),
            "计算结论": format_mapping(self.outcomes),
            "备注": "；".join(self.notes),
        }


# ---------------------------------------------------------------------------
# 参数校验
# ---------------------------------------------------------------------------
def require_number(
    value: Any,
    name: str = "数值",
    *,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> float:
    """校验并返回有限浮点数，拒绝布尔值、空值、NaN 和无穷大。"""
    if value is None or isinstance(value, bool):
        raise ValidationError(f"{name}必须是有效数字，不能为空。")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name}必须是数字，当前输入为：{value!r}。") from exc
    if not math.isfinite(number):
        raise ValidationError(f"{name}必须是有限数字，不能为 NaN 或无穷大。")
    if min_value is not None and number < min_value:
        raise ValidationError(f"{name}不能小于 {format_number(min_value)}。")
    if max_value is not None and number > max_value:
        raise ValidationError(f"{name}不能大于 {format_number(max_value)}。")
    return number


def require_positive(value: Any, name: str = "数值") -> float:
    """校验严格正数。"""
    number = require_number(value, name)
    if number <= 0:
        raise ValidationError(f"{name}必须大于 0，当前为 {format_number(number)}。")
    return number


def require_nonnegative(value: Any, name: str = "数值") -> float:
    """校验非负数（允许等于 0）。"""
    number = require_number(value, name)
    if number < 0:
        raise ValidationError(f"{name}不能为负数，当前为 {format_number(number)}。")
    return number


def require_int(
    value: Any,
    name: str = "期数",
    *,
    min_value: Optional[int] = 1,
    max_value: Optional[int] = 10000,
) -> int:
    """校验整数；允许 3、3.0、"3"，拒绝 3.2。"""
    if value is None or isinstance(value, bool):
        raise ValidationError(f"{name}必须是整数。")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name}必须是整数，当前输入为：{value!r}。") from exc
    if not math.isfinite(number) or not number.is_integer():
        raise ValidationError(f"{name}必须是整数，当前输入为：{value!r}。")
    result = int(number)
    if min_value is not None and result < min_value:
        raise ValidationError(f"{name}不能小于 {min_value}。")
    if max_value is not None and result > max_value:
        raise ValidationError(f"{name}不能大于 {max_value}。")
    return result


def require_rate(
    value: Any,
    name: str = "折现率",
    *,
    allow_negative: bool = False,
    max_value: float = 10.0,
) -> float:
    """校验小数形式比率（0.08 表示 8%），必须大于 -100%。"""
    rate = require_number(value, name, min_value=-0.999999, max_value=max_value)
    if not allow_negative and rate < 0:
        raise ValidationError(f"{name}不能为负数，应按百分数输入（如 8% 输入 8）。")
    return rate


def validate_discount_rate(value: Any, name: str = "折现率") -> float:
    """折现率专用校验：非负且小于 1000%。"""
    return require_rate(value, name, allow_negative=False)


def require_sequence(value: Any, name: str = "序列", min_length: int = 1) -> List[Any]:
    """校验非空可迭代序列；字符串不视为数字序列。"""
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise ValidationError(f"{name}必须是数字列表。")
    items = list(value)
    if len(items) < min_length:
        raise ValidationError(f"{name}至少需要 {min_length} 个数据。")
    return items


def require_cash_flows(
    cash_flows: Sequence[Any],
    name: str = "各期现金流量",
    *,
    min_length: int = 1,
    max_length: int = 500,
) -> List[float]:
    """校验现金流量序列，每期均须为有限数字。"""
    items = require_sequence(cash_flows, name, min_length)
    if len(items) > max_length:
        raise ValidationError(f"{name}最多支持 {max_length} 期。")
    return [require_number(item, f"{name}第{index + 1}期") for index, item in enumerate(items)]


def require_same_length(*sequences: Sequence[Any], names: Optional[Sequence[str]] = None) -> None:
    """校验多个序列长度一致。"""
    lists = [list(seq) for seq in sequences]
    if not lists:
        return
    lengths = [len(seq) for seq in lists]
    if len(set(lengths)) != 1:
        labels = list(names) if names else [f"序列{i + 1}" for i in range(len(lists))]
        detail = "、".join(f"{label}{length}" for label, length in zip(labels, lengths))
        raise ValidationError(f"相关数据长度必须一致，当前为：{detail}。")
    if lengths[0] == 0:
        raise ValidationError("数据序列不能为空。")


def ensure_not_zero(denominator: float, name: str = "分母") -> float:
    """防止除数为 0，并给出中文提示。"""
    if abs(denominator) < 1e-15:
        raise ValidationError(f"{name}不能为 0，否则公式无意义。")
    return denominator


# ---------------------------------------------------------------------------
# 格式化
# ---------------------------------------------------------------------------
def format_number(value: Any, digits: int = 2) -> str:
    """格式化普通数字；无法转换时原样返回。"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number) or math.isinf(number):
        return str(value)
    if abs(number - round(number)) < 1e-12:
        return f"{int(round(number)):,}"
    return f"{number:,.{digits}f}"


def money(value: Any, digits: int = 2) -> str:
    """输出金额。"""
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def percent(value: Any, digits: int = 2) -> str:
    """把小数比率格式化为百分数。"""
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return str(value)


def times(value: Any, digits: int = 2) -> str:
    """输出倍数。"""
    try:
        return f"{float(value):,.{digits}f} 倍"
    except (TypeError, ValueError):
        return str(value)


def format_value(value: Any) -> str:
    """通用结果格式化，支持列表、字典等。"""
    if value is None:
        return "不适用/无法收回"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "不适用"
        return f"{value:,.6f}".rstrip("0").rstrip(".")
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(format_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + "；".join(f"{key}: {format_value(val)}" for key, val in value.items()) + "}"
    return str(value)


def format_mapping(mapping: Dict[str, Any]) -> str:
    """把参数字典压缩成适合 CSV 的单行文本。"""
    return "；".join(f"{key}={format_value(value)}" for key, value in mapping.items())


# ---------------------------------------------------------------------------
# 控制台输入
# ---------------------------------------------------------------------------
def _default_text(default: Any) -> str:
    if default is None:
        return ""
    return f" [直接回车默认 {format_value(default)}]"


def ask_text(prompt: str, default: Optional[str] = None) -> str:
    """读取非空文本。"""
    raw = input(f"{prompt}{_default_text(default)}：").strip()
    if not raw:
        if default is not None:
            return default
        raise ValidationError(f"{prompt}不能为空。")
    return raw


def ask_float(
    prompt: str,
    default: Optional[float] = None,
    *,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    allow_negative: bool = True,
    allow_zero: bool = True,
) -> float:
    """循环读取合法浮点数，输入错误时提示后重试。"""
    if not allow_negative:
        min_value = 0.0 if min_value is None else max(0.0, min_value)
    if not allow_zero:
        min_value = 1e-12 if min_value is None else max(1e-12, min_value)
    hint = ""
    if min_value is not None or max_value is not None:
        pieces = []
        if min_value is not None:
            pieces.append(f"≥{format_number(min_value)}")
        if max_value is not None:
            pieces.append(f"≤{format_number(max_value)}")
        hint = f"（{', '.join(pieces)}）"
    while True:
        raw = input(f"{prompt}{hint}{_default_text(default)}：").strip()
        if raw == "" and default is not None:
            return float(default)
        try:
            return require_number(raw, prompt, min_value=min_value, max_value=max_value)
        except ValidationError as exc:
            print(f"  [输入有误] {exc} 请重新输入。")


def ask_int(
    prompt: str,
    default: Optional[int] = None,
    *,
    min_value: int = 1,
    max_value: int = 10000,
) -> int:
    """循环读取整数。"""
    while True:
        raw = input(
            f"{prompt}（整数，{min_value}~{max_value}）{_default_text(default)}："
        ).strip()
        if raw == "" and default is not None:
            return int(default)
        try:
            return require_int(raw, prompt, min_value=min_value, max_value=max_value)
        except ValidationError as exc:
            print(f"  [输入有误] {exc} 请重新输入。")


def ask_rate_percent(
    prompt: str,
    default: Optional[float] = None,
    *,
    allow_negative: bool = False,
    max_percent: float = 1000.0,
) -> float:
    """按百分数读取比率并返回小数；如输入 8 返回 0.08。"""
    default_percent = None if default is None else default * 100
    while True:
        suffix = f"（%，如 8 表示 8%）{_default_text(default_percent)}"
        raw = input(f"{prompt}{suffix}：").strip()
        if raw == "" and default_percent is not None:
            value = float(default_percent)
        else:
            try:
                value = float(raw)
            except ValueError:
                print("  [输入有误] 请输入百分数数字，例如 8 表示 8%。")
                continue
        if not math.isfinite(value):
            print("  [输入有误] 请输入有限数字。")
            continue
        if not allow_negative and value < 0:
            print("  [输入有误] 该比率不能为负数。")
            continue
        if value > max_percent:
            print(f"  [输入有误] 百分数不能超过 {max_percent:g}%。")
            continue
        return value / 100.0


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """读取是/否。"""
    default_text = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} [{default_text}]：").strip().lower()
        if raw == "":
            return default
        if raw in {"y", "yes", "是", "1"}:
            return True
        if raw in {"n", "no", "否", "0"}:
            return False
        print("  [输入有误] 请输入 y 或 n。")


def ask_series(
    prompt: str,
    default: Optional[Sequence[float]] = None,
    *,
    min_length: int = 1,
    allow_negative: bool = True,
) -> List[float]:
    """读取逗号分隔的数字序列。"""
    default_text = ""
    if default is not None:
        default_text = " [直接回车默认 " + ",".join(format_value(x) for x in default) + "]"
    while True:
        raw = input(f"{prompt}（用英文逗号分隔）{default_text}：").strip()
        if raw == "" and default is not None:
            values = list(default)
        else:
            normalized = raw.replace("，", ",").replace("、", ",")
            pieces = [piece.strip() for piece in normalized.split(",") if piece.strip()]
            try:
                values = [float(piece) for piece in pieces]
            except ValueError:
                print("  [输入有误] 序列中包含非数字，请重新输入。")
                continue
        if len(values) < min_length:
            print(f"  [输入有误] 至少需要 {min_length} 个数字。")
            continue
        if not allow_negative and any(value < 0 for value in values):
            print("  [输入有误] 该序列不能包含负数。")
            continue
        return values


def pause(message: str = "按回车键继续...") -> None:
    """暂停，便于阅读输出。"""
    try:
        input(f"\n{message}")
    except EOFError:
        pass


# ---------------------------------------------------------------------------
# 结果展示 / 安全执行
# ---------------------------------------------------------------------------
def print_heading(text: str, char: str = "=") -> None:
    """打印标题。"""
    print("\n" + char * 78)
    print(text)
    print(char * 78)


def print_subheading(text: str) -> None:
    """打印小标题。"""
    print(f"\n{text}")
    print("-" * 78)


def show_result(result: CalcResult, *, auto_export: bool = True) -> Optional[Path]:
    """统一打印计算过程，默认追加写入项目根目录 result.csv。"""
    print_heading(f"【{result.module}】{result.title}")
    if result.parameters:
        print_subheading("一、已知参数")
        for key, value in result.parameters.items():
            print(f"  {key}：{format_value(value)}")

    if result.steps:
        print_subheading("二、完整解题步骤")
        for index, step in enumerate(result.steps, start=1):
            print(f"  ({index}) {step}")

    if result.outcomes:
        print_subheading("三、计算结果")
        for key, value in result.outcomes.items():
            print(f"  {key}：{format_value(value)}")

    if result.tables:
        print_subheading("四、表格结果")
        for table_title, table in result.tables:
            print(f"\n  {table_title}")
            try:
                print(table.to_string(index=False))
            except AttributeError:
                print(table)

    if result.notes:
        print_subheading("五、结论与提示")
        for note in result.notes:
            print(f"  - {note}")

    export_path = None
    if auto_export:
        try:
            from export import append_result

            export_path = append_result(result)
            print(f"\n  [已导出] {export_path}")
        except Exception as exc:  # 导出失败不应影响计算结果查看
            print(f"\n  [导出提示] CSV 导出失败：{exc}")
    print("=" * 78)
    return export_path


def run_calculation(func: Callable[[], Optional[CalcResult]]) -> Optional[CalcResult]:
    """执行计算函数并统一捕获异常，保证菜单不会因一次输入错误而退出。"""
    try:
        result = func()
        if result is not None:
            show_result(result)
        return result
    except ValidationError as exc:
        print(f"\n[参数错误] {exc}\n请检查后重新计算。")
        return None
    except ZeroDivisionError:
        print("\n[计算错误] 公式中出现了除数为 0 的情况，请检查相关参数。")
        return None
    except KeyboardInterrupt:
        raise
    except Exception as exc:  # 兜底，避免显示冗长堆栈影响课堂使用
        print(f"\n[计算失败] 发生未预期错误：{exc}")
        print("建议检查输入数据是否完整；若问题持续，请运行 python selftest.py 自检。")
        return None


def safe_divide(numerator: float, denominator: float, name: str = "分母") -> float:
    """安全除法，分母为 0 时抛出中文参数异常。"""
    ensure_not_zero(denominator, name)
    return numerator / denominator
