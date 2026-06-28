"""教学级模拟回测模块。

这里不是专业回测系统，只用于展示“每月选 Top10 等权配置”的概念。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def run_simple_backtest(
    scored_data: pd.DataFrame,
    initial_cash: float = 100000,
    months: int = 36,
    seed: int = 2026,
) -> pd.DataFrame:
    """生成策略与基准的模拟累计收益曲线。

    策略逻辑：
    1. 每月重新选一次 Top10
    2. Top10 等权配置
    3. 股票月收益由评分、波动率与随机扰动共同生成
    """
    rng = np.random.default_rng(seed)
    universe = scored_data.copy().reset_index(drop=True)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=months + 1, freq="ME")

    strategy_values = [initial_cash]
    benchmark_values = [initial_cash]

    for month in range(months):
        noisy_scores = universe["score"] + rng.normal(0, 4, size=len(universe))
        month_universe = universe.assign(month_score=noisy_scores)
        top10 = month_universe.nlargest(10, "month_score")

        expected_monthly_return = (top10["score"].mean() - 50) / 1000
        top10_volatility = top10["volatility"].mean() / np.sqrt(12)
        strategy_return = rng.normal(expected_monthly_return, max(top10_volatility, 0.015))
        strategy_return = float(np.clip(strategy_return, -0.16, 0.16))

        benchmark_return = rng.normal(0.004, 0.045)
        benchmark_return = float(np.clip(benchmark_return, -0.18, 0.14))

        strategy_values.append(strategy_values[-1] * (1 + strategy_return))
        benchmark_values.append(benchmark_values[-1] * (1 + benchmark_return))

    result = pd.DataFrame(
        {
            "date": dates,
            "策略组合": strategy_values,
            "模拟基准": benchmark_values,
        }
    )
    result["策略累计收益率"] = result["策略组合"] / initial_cash - 1
    result["基准累计收益率"] = result["模拟基准"] / initial_cash - 1
    return result
