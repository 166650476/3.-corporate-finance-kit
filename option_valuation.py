"""模块 11：期权基础估值。

覆盖看涨/看跌期权到期价值与净损益、单期二叉树复制原理和套期保值原理。
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

from utils import (
    CalcResult,
    ValidationError,
    ask_float,
    ask_rate_percent,
    money,
    pause,
    percent,
    print_heading,
    require_nonnegative,
    require_positive,
    require_rate,
    run_calculation,
    show_result,
)


MODULE = "模块11 期权基础估值"


def option_payoff(option_type: str, spot_price: float, strike_price: float) -> float:
    """到期日价值：看涨 max(S-K,0)，看跌 max(K-S,0)。"""
    spot = require_nonnegative(spot_price, "到期标的资产价格 S")
    strike = require_positive(strike_price, "执行价格 K")
    if option_type == "call":
        return max(spot - strike, 0.0)
    if option_type == "put":
        return max(strike - spot, 0.0)
    raise ValidationError("期权类型只能是 call（看涨）或 put（看跌）。")


def option_payoff_result(
    option_type: str,
    spot_price: float,
    strike_price: float,
    premium: float,
    position: int = 1,
) -> CalcResult:
    """构建期权到期价值与净损益结果；position=1 多头，-1 空头。"""
    option_type = option_type.lower()
    if option_type not in {"call", "put"}:
        raise ValidationError("期权类型只能是 call 或 put。")
    if position not in (1, -1):
        raise ValidationError("position 只能是 1（多头）或 -1（空头）。")
    spot = require_nonnegative(spot_price, "到期标的资产价格 S")
    strike = require_positive(strike_price, "执行价格 K")
    option_premium = require_nonnegative(premium, "期权费")
    payoff = option_payoff(option_type, spot, strike)
    pnl = position * (payoff - option_premium)
    option_name = "看涨期权" if option_type == "call" else "看跌期权"
    position_name = "多头（买方）" if position == 1 else "空头（卖方）"
    break_even = strike + option_premium if option_type == "call" else strike - option_premium
    result = CalcResult(
        MODULE,
        f"{option_name}到期价值与净损益",
        {
            "期权类型": option_name,
            "持仓方向": position_name,
            "到期标的资产价格 S": f"{money(spot)} 元",
            "执行价格 K": f"{money(strike)} 元",
            "期权费": f"{money(option_premium)} 元",
        },
    )
    if option_type == "call":
        result.add_step("看涨期权到期价值 = max(S-K, 0)。")
    else:
        result.add_step("看跌期权到期价值 = max(K-S, 0)。")
    result.add_step(
        f"到期价值 = max({'S-K' if option_type == 'call' else 'K-S'},0) = {money(payoff)} 元。"
    )
    result.add_step("买方净损益=到期价值-期权费；卖方净损益=期权费-到期价值。")
    result.add_step(
        f"本题为{position_name}，净损益={position:+d}×({money(payoff)}-"
        f"{money(option_premium)})={money(pnl)} 元。"
    )
    result.add_step(
        f"盈亏平衡点标的资产价格={'K+期权费' if option_type == 'call' else 'K-期权费'}="
        f"{money(break_even)} 元。"
    )
    result.put("到期日价值", f"{money(payoff)} 元")
    result.put("净损益", f"{money(pnl)} 元")
    result.put("盈亏平衡点", f"{money(break_even)} 元")
    if payoff == 0:
        result.add_note("期权到期未被执行，买方损失全部期权费；卖方获得全部期权费。")
    else:
        result.add_note("期权被执行，到期价值为正；买方净损益需扣除初始期权费。")
    status = "盈利" if pnl > 0 else ("亏损" if pnl < 0 else "盈亏平衡")
    result.add_note(f"本次期权交易结果为：{status}。")

    rows = []
    for scenario in [spot * 0.5, spot * 0.8, spot, spot * 1.2, spot * 1.5]:
        scenario_payoff = option_payoff(option_type, scenario, strike)
        scenario_pnl = position * (scenario_payoff - option_premium)
        rows.append(
            {
                "到期价格 S": round(scenario, 2),
                "到期价值": round(scenario_payoff, 2),
                "净损益": round(scenario_pnl, 2),
            }
        )
    result.add_table("不同到期价格情景表（元）", pd.DataFrame(rows))
    return result


def binomial_replication(
    current_price: float,
    up_price: float,
    down_price: float,
    strike_price: float,
    risk_free_rate: float,
    option_type: str = "call",
) -> Dict[str, float]:
    """单期二叉树复制与套期保值。"""
    s0 = require_positive(current_price, "当前股价 S0")
    su = require_positive(up_price, "上涨后股价 Su")
    sd = require_positive(down_price, "下跌后股价 Sd")
    strike = require_positive(strike_price, "执行价格 K")
    r = require_rate(risk_free_rate, "无风险利率 r")
    option_type = option_type.lower()
    if option_type not in {"call", "put"}:
        raise ValidationError("期权类型只能是 call 或 put。")
    if su <= sd:
        raise ValidationError("上涨后股价 Su 必须大于下跌后股价 Sd。")
    cu = option_payoff(option_type, su, strike)
    cd = option_payoff(option_type, sd, strike)
    delta = (cu - cd) / (su - sd)
    # 复制组合：购买 Δ 股股票，并借入 B 元；B=(Δ×Sd-Cd)/(1+r)。
    borrowed = (delta * sd - cd) / (1.0 + r)
    option_value = delta * s0 - borrowed
    u = su / s0
    d = sd / s0
    probability = (1.0 + r - d) / (u - d)
    if probability < -1e-10 or probability > 1.0 + 1e-10:
        raise ValidationError(
            "无套利条件不满足：无风险利率应介于股票下跌收益率与上涨收益率之间。"
        )
    risk_neutral_value = (probability * cu + (1.0 - probability) * cd) / (1.0 + r)
    return {
        "su": su,
        "sd": sd,
        "cu": cu,
        "cd": cd,
        "delta": delta,
        "borrowed": borrowed,
        "option_value": option_value,
        "probability": probability,
        "risk_neutral_value": risk_neutral_value,
    }


def binomial_result(
    current_price: float,
    up_price: float,
    down_price: float,
    strike_price: float,
    risk_free_rate: float,
    option_type: str = "call",
) -> CalcResult:
    """构建复制原理与套期保值结果。"""
    values = binomial_replication(
        current_price, up_price, down_price, strike_price, risk_free_rate, option_type
    )
    option_name = "看涨期权" if option_type == "call" else "看跌期权"
    result = CalcResult(
        MODULE,
        f"单期二叉树——{option_name}复制与套期保值",
        {
            "当前股价 S0": f"{money(current_price)} 元",
            "上涨后股价 Su": f"{money(up_price)} 元",
            "下跌后股价 Sd": f"{money(down_price)} 元",
            "执行价格 K": f"{money(strike_price)} 元",
            "无风险利率 r": percent(risk_free_rate),
        },
    )
    result.add_step(
        f"计算到期日期权价值：上涨时 Cu={money(values['cu'])} 元，"
        f"下跌时 Cd={money(values['cd'])} 元。"
    )
    result.add_step("套期保值比率 Δ=(Cu-Cd)/(Su-Sd)，即每份期权对应的股票数量。")
    result.add_step(
        f"Δ=({money(values['cu'])}-{money(values['cd'])})/"
        f"({money(values['su'])}-{money(values['sd'])})={values['delta']:.6f}。"
    )
    if values["borrowed"] >= 0:
        borrow_text = f"借入 {money(values['borrowed'])} 元"
    else:
        borrow_text = f"贷出/投资 {money(-values['borrowed'])} 元"
    result.add_step(
        f"为使复制组合到期价值与期权一致，需{borrow_text}，"
        f"即 B=(Δ×Sd-Cd)/(1+r)={money(values['borrowed'])} 元。"
    )
    result.add_step(
        f"复制组合当前成本=Δ×S0-B={values['delta']:.6f}×{money(current_price)}"
        f"-({money(values['borrowed'])})={money(values['option_value'])} 元，"
        "即为期权理论价值。"
    )
    result.add_step(
        f"风险中性概率 p=(1+r-d)/(u-d)="
        f"({percent(1 + risk_free_rate)}-{percent(values['sd'] / current_price)})/"
        f"({percent(values['su'] / current_price)}-{percent(values['sd'] / current_price)})"
        f"={values['probability']:.4f}。"
    )
    result.add_step(
        f"风险中性定价校验：V=[p×Cu+(1-p)×Cd]/(1+r)="
        f"{money(values['risk_neutral_value'])} 元，与复制组合成本一致。"
    )
    result.put("上涨时期权价值 Cu", f"{money(values['cu'])} 元")
    result.put("下跌时期权价值 Cd", f"{money(values['cd'])} 元")
    result.put("套期保值比率 Δ", f"{values['delta']:.6f}")
    result.put("借款额 B（负数为贷出）", f"{money(values['borrowed'])} 元")
    result.put("期权理论价值", f"{money(values['option_value'])} 元")
    result.put("风险中性概率 p", f"{values['probability']:.4f}")
    result.put("风险中性定价校验", f"{money(values['risk_neutral_value'])} 元")
    result.add_note("复制原理：用 Δ 股股票和借贷资金构造与期权到期价值相同的组合。")
    result.add_note("套期保值：卖出一份期权并买入 Δ 股股票，可对冲股价波动风险。")
    return result


# ---------------------------------------------------------------------------
# 交互菜单与例题
# ---------------------------------------------------------------------------
def _interactive_payoff() -> CalcResult:
    print("  1. 看涨期权（call）")
    print("  2. 看跌期权（put）")
    type_choice = input("请选择期权类型：").strip()
    option_type = "call" if type_choice == "1" else "put" if type_choice == "2" else ""
    if not option_type:
        raise ValidationError("期权类型只能选择 1 或 2。")
    print("  1. 多头（买方）")
    print("  2. 空头（卖方）")
    position_choice = input("请选择持仓方向：").strip()
    position = 1 if position_choice == "1" else -1 if position_choice == "2" else 0
    if position == 0:
        raise ValidationError("持仓方向只能选择 1 或 2。")
    return option_payoff_result(
        option_type,
        ask_float("到期标的资产价格 S（元）", 38, min_value=0, allow_negative=False),
        ask_float("执行价格 K（元）", 40, min_value=0, allow_negative=False),
        ask_float("期权费（元）", 3, min_value=0, allow_negative=False),
        position,
    )


def _interactive_binomial(option_type: str) -> CalcResult:
    return binomial_result(
        ask_float("当前股价 S0（元）", 50, min_value=0, allow_negative=False),
        ask_float("上涨后股价 Su（元）", 60, min_value=0, allow_negative=False),
        ask_float("下跌后股价 Sd（元）", 40, min_value=0, allow_negative=False),
        ask_float("执行价格 K（元）", 50, min_value=0, allow_negative=False),
        ask_rate_percent("单期无风险利率 r", 0.05),
        option_type,
    )


def _run_demo() -> None:
    """一键演示期权基础计算。"""
    print_heading("期权基础估值：全套例题一键演示", "★")
    show_result(option_payoff_result("call", 38, 40, 3, 1))
    show_result(option_payoff_result("put", 38, 40, 3, 1))
    show_result(binomial_result(50, 60, 40, 50, 0.05, "call"))
    show_result(binomial_result(50, 60, 40, 50, 0.05, "put"))
    print("\n[演示完成] 已演示看涨/看跌期权损益及二叉树复制与套期保值。")


def run() -> None:
    """模块 11 控制台菜单。"""
    while True:
        print_heading("模块11 期权基础估值")
        print("  1. 期权到期日价值与净损益（看涨/看跌）")
        print("  2. 复制原理与套期保值（看涨期权）")
        print("  3. 复制原理与套期保值（看跌期权）")
        print("  4. 全套例题一键演示")
        print("  0. 返回主菜单")
        try:
            choice = input("请选择功能：").strip()
        except EOFError:
            return
        if choice == "0":
            return
        if choice == "1":
            run_calculation(_interactive_payoff)
            pause()
        elif choice == "2":
            run_calculation(lambda: _interactive_binomial("call"))
            pause()
        elif choice == "3":
            run_calculation(lambda: _interactive_binomial("put"))
            pause()
        elif choice == "4":
            _run_demo()
            pause()
        else:
            print("[提示] 无效选项，请输入 0~4。")
