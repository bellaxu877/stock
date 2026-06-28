"""股票数据获取与模拟生成模块。

本应用面向家庭学习展示：优先尝试用 yfinance 获取公开数据；
如果网络、依赖或数据不可用，会自动切换到模拟数据，保证页面能运行。
"""

from __future__ import annotations

import random
from typing import List, Tuple

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "ticker",
    "name",
    "price",
    "roe",
    "revenue_growth",
    "net_profit_margin",
    "debt_ratio",
    "cash_flow_positive",
    "volatility",
]


DEFAULT_TICKERS = [
    "AAPL",
    "MSFT",
    "JNJ",
    "PG",
    "KO",
    "PEP",
    "WMT",
    "COST",
    "MCD",
    "V",
    "MA",
    "HD",
    "UNH",
    "ABBV",
    "MRK",
    "XOM",
    "CVX",
    "IBM",
    "ORCL",
    "CSCO",
]


COMPANY_NAMES = {
    "AAPL": "苹果公司",
    "MSFT": "微软",
    "JNJ": "强生",
    "PG": "宝洁",
    "KO": "可口可乐",
    "PEP": "百事",
    "WMT": "沃尔玛",
    "COST": "好市多",
    "MCD": "麦当劳",
    "V": "Visa",
    "MA": "万事达",
    "HD": "家得宝",
    "UNH": "联合健康",
    "ABBV": "艾伯维",
    "MRK": "默沙东",
    "XOM": "埃克森美孚",
    "CVX": "雪佛龙",
    "IBM": "IBM",
    "ORCL": "甲骨文",
    "CSCO": "思科",
}


def generate_mock_data(count: int = 35, seed: int = 42) -> pd.DataFrame:
    """生成 20~50 只模拟股票，字段与真实数据保持一致。"""
    count = max(20, min(50, count))
    rng = np.random.default_rng(seed)
    random.seed(seed)

    stable_names = [
        "安心消费",
        "常青医疗",
        "稳步科技",
        "家和食品",
        "清流能源",
        "远山电器",
        "四季零售",
        "明德药业",
        "丰禾制造",
        "蓝桥通信",
        "星河软件",
        "南风物流",
        "海棠饮品",
        "云杉家居",
        "晨光服务",
        "绿洲环保",
        "金石保险",
        "银帆银行",
        "和润地产",
        "知行教育",
    ]

    rows = []
    for index in range(count):
        ticker = f"MOCK{index + 1:03d}"
        base_name = stable_names[index % len(stable_names)]
        quality_bias = rng.normal(0, 1)

        roe = np.clip(rng.normal(0.12 + quality_bias * 0.018, 0.055), -0.05, 0.35)
        revenue_growth = np.clip(rng.normal(0.07 + quality_bias * 0.015, 0.075), -0.18, 0.32)
        net_profit_margin = np.clip(rng.normal(0.11 + quality_bias * 0.015, 0.055), -0.04, 0.32)
        debt_ratio = np.clip(rng.normal(0.42 - quality_bias * 0.04, 0.16), 0.08, 0.88)
        volatility = np.clip(rng.normal(0.22 - quality_bias * 0.015, 0.09), 0.06, 0.55)
        cash_flow_positive = int(rng.random() < np.clip(0.72 + quality_bias * 0.08, 0.35, 0.95))
        price = float(np.clip(rng.lognormal(mean=3.5, sigma=0.55), 8, 520))

        rows.append(
            {
                "ticker": ticker,
                "name": f"{base_name}{index + 1}号",
                "price": round(price, 2),
                "roe": round(float(roe), 4),
                "revenue_growth": round(float(revenue_growth), 4),
                "net_profit_margin": round(float(net_profit_margin), 4),
                "debt_ratio": round(float(debt_ratio), 4),
                "cash_flow_positive": cash_flow_positive,
                "volatility": round(float(volatility), 4),
            }
        )

    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def fetch_yfinance_data(tickers: List[str] | None = None) -> pd.DataFrame:
    """从 yfinance 获取简化基本面数据。

    yfinance 的字段覆盖不稳定，因此做了宽松兜底：
    单只股票缺字段时会用合理区间模拟补齐；整体失败则由外层切换到模拟数据。
    """
    try:
        import yfinance as yf
    except Exception as exc:
        raise RuntimeError("当前环境未安装 yfinance。") from exc

    tickers = tickers or DEFAULT_TICKERS
    rows = []
    rng = np.random.default_rng(2026)

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            history = stock.history(period="1y", auto_adjust=True)

            if history.empty:
                continue

            returns = history["Close"].pct_change().dropna()
            volatility = float(returns.std() * np.sqrt(252)) if not returns.empty else float(rng.uniform(0.14, 0.32))
            price = float(history["Close"].iloc[-1])

            roe = _safe_ratio(info.get("returnOnEquity"), rng.uniform(0.04, 0.28))
            revenue_growth = _safe_ratio(info.get("revenueGrowth"), rng.uniform(-0.05, 0.22))
            margin = _safe_ratio(info.get("profitMargins"), rng.uniform(0.04, 0.24))

            total_debt = info.get("totalDebt")
            total_assets = info.get("totalAssets")
            debt_to_equity = info.get("debtToEquity")
            if total_debt and total_assets:
                debt_ratio = float(total_debt) / max(float(total_assets), 1.0)
            elif debt_to_equity is not None:
                debt_ratio = float(debt_to_equity) / 100.0
            else:
                debt_ratio = float(rng.uniform(0.18, 0.65))
            debt_ratio = float(np.clip(debt_ratio, 0.02, 0.95))

            free_cashflow = info.get("freeCashflow")
            operating_cashflow = info.get("operatingCashflow")
            cash_flow_positive = int((free_cashflow or operating_cashflow or 1) > 0)

            rows.append(
                {
                    "ticker": ticker,
                    "name": info.get("shortName") or COMPANY_NAMES.get(ticker, ticker),
                    "price": round(price, 2),
                    "roe": round(float(np.clip(roe, -0.2, 0.6)), 4),
                    "revenue_growth": round(float(np.clip(revenue_growth, -0.5, 0.8)), 4),
                    "net_profit_margin": round(float(np.clip(margin, -0.3, 0.6)), 4),
                    "debt_ratio": round(debt_ratio, 4),
                    "cash_flow_positive": cash_flow_positive,
                    "volatility": round(float(np.clip(volatility, 0.03, 0.85)), 4),
                }
            )
        except Exception:
            continue

    if len(rows) < 10:
        raise RuntimeError("yfinance 可用数据不足，已切换为模拟数据。")

    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def load_stock_data(source: str = "模拟", count: int = 35) -> Tuple[pd.DataFrame, str]:
    """根据页面选择加载数据，并返回数据来源说明。"""
    if source == "yfinance":
        try:
            return fetch_yfinance_data(), "已尝试使用 yfinance 公开数据"
        except Exception as exc:
            data = generate_mock_data(count=count)
            return data, f"yfinance 暂不可用，已自动切换为模拟数据（原因：{exc}）"

    return generate_mock_data(count=count), "当前使用模拟股票数据"


def _safe_ratio(value: object, fallback: float) -> float:
    """把 yfinance 返回值转换成比例，缺失时使用兜底值。"""
    if value is None:
        return float(fallback)
    try:
        return float(value)
    except Exception:
        return float(fallback)
