"""稳健型股票评分逻辑。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def min_max_normalize(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """做 min-max 标准化，返回 0~100 分。

    higher_is_better=False 时，数值越低得分越高，适合负债率、波动率。
    """
    values = pd.to_numeric(series, errors="coerce").fillna(series.median())
    min_value = values.min()
    max_value = values.max()

    if np.isclose(max_value, min_value):
        return pd.Series(50.0, index=series.index)

    normalized = (values - min_value) / (max_value - min_value)
    if not higher_is_better:
        normalized = 1 - normalized
    return normalized * 100


def score_stocks(data: pd.DataFrame) -> pd.DataFrame:
    """计算总分 100 分的稳健评分。"""
    df = data.copy()

    roe_score = min_max_normalize(df["roe"], higher_is_better=True)
    margin_score = min_max_normalize(df["net_profit_margin"], higher_is_better=True)
    profitability = (roe_score + margin_score) / 2

    growth = min_max_normalize(df["revenue_growth"], higher_is_better=True)

    debt_score = min_max_normalize(df["debt_ratio"], higher_is_better=False)
    cash_score = df["cash_flow_positive"].astype(int) * 100
    financial_health = debt_score * 0.7 + cash_score * 0.3

    risk_control = min_max_normalize(df["volatility"], higher_is_better=False)

    df["profitability"] = profitability
    df["growth"] = growth
    df["financial_health"] = financial_health
    df["risk_control"] = risk_control
    df["score"] = (
        0.4 * profitability
        + 0.2 * growth
        + 0.25 * financial_health
        + 0.15 * risk_control
    ).round(2)
    df["risk_level"] = df["volatility"].apply(get_risk_level)
    df["explanation"] = df.apply(make_plain_explanation, axis=1)

    return df.sort_values("score", ascending=False).reset_index(drop=True)


def get_risk_level(volatility: float) -> str:
    """根据波动率给出低/中/高风险。"""
    if volatility < 0.15:
        return "低"
    if volatility <= 0.3:
        return "中"
    return "高"


def make_plain_explanation(row: pd.Series) -> str:
    """用家人容易理解的话解释推荐原因。"""
    parts = []

    if row["roe"] >= 0.15:
        parts.append("赚钱能力比较强")
    elif row["roe"] >= 0.08:
        parts.append("赚钱能力相对稳定")
    else:
        parts.append("赚钱能力不算突出")

    if row["net_profit_margin"] >= 0.12:
        parts.append("每卖出一笔产品后留下的钱较多")
    elif row["net_profit_margin"] >= 0.05:
        parts.append("利润水平还算正常")
    else:
        parts.append("利润空间偏薄")

    if row["debt_ratio"] < 0.35:
        parts.append("借的钱不多，财务压力较小")
    elif row["debt_ratio"] <= 0.6:
        parts.append("负债处在可观察范围")
    else:
        parts.append("负债偏高，需要多留意")

    if int(row["cash_flow_positive"]) == 1:
        parts.append("现金流为正，日常经营更有底气")
    else:
        parts.append("现金流暂时不够理想")

    if row["volatility"] < 0.15:
        parts.append("价格起伏较小，适合稳健观察")
    elif row["volatility"] <= 0.3:
        parts.append("价格有一定起伏，但不算特别剧烈")
    else:
        parts.append("价格起伏较大，不适合只看稳健性的家庭成员")

    return f"这家公司{parts[0]}，{parts[1]}，{parts[2]}，{parts[3]}，{parts[4]}。综合来看，它更偏向“{row['risk_level']}风险”的观察对象。"


def apply_risk_preference(scored_data: pd.DataFrame, preference: str) -> pd.DataFrame:
    """根据风险偏好过滤股票池。"""
    if preference == "低":
        return scored_data[scored_data["risk_level"] == "低"].copy()
    if preference == "中":
        return scored_data[scored_data["risk_level"].isin(["低", "中"])].copy()
    return scored_data.copy()
