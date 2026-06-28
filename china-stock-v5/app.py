"""家庭版中国股票准实时选股系统 V5（生产可运行版）。

运行方式：
streamlit run app.py

说明：
本工具仅用于家庭学习与模拟展示，不构成任何投资建议。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from streamlit_autorefresh import st_autorefresh


# =========================
# 固定中国股票池
# =========================

@dataclass(frozen=True)
class Stock:
    name: str
    ticker: str


STOCK_POOL = [
    Stock("贵州茅台", "600519.SS"),
    Stock("中国平安", "601318.SS"),
    Stock("招商银行", "600036.SS"),
    Stock("宁德时代", "300750.SZ"),
    Stock("比亚迪", "002594.SZ"),
    Stock("五粮液", "000858.SZ"),
    Stock("东方财富", "300059.SZ"),
    Stock("隆基绿能", "601012.SS"),
    Stock("中信证券", "600030.SS"),
    Stock("海天味业", "603288.SS"),
]


# =========================
# 页面基础设置
# =========================

st.set_page_config(
    page_title="家庭版中国股票准实时选股系统 V5",
    page_icon="🇨🇳",
    layout="wide",
)


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        max-width: 1120px;
    }
    .simple-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        background: #ffffff;
        margin-bottom: 12px;
    }
    .big-number {
        font-size: 28px;
        font-weight: 700;
        color: #111827;
    }
    .muted {
        color: #6b7280;
        font-size: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# 数据获取与评分
# =========================

@st.cache_data(ttl=55, show_spinner=False)
def fetch_stock_data(ticker: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """使用 yfinance 获取单只股票数据。

    任何异常都返回 None，避免页面崩溃。
    """
    try:
        data = yf.download(
            ticker,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        if data is None or data.empty:
            return None

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        if "Close" not in data.columns or "Volume" not in data.columns:
            return None

        clean = data[["Close", "Volume"]].copy()
        clean["Close"] = pd.to_numeric(clean["Close"], errors="coerce")
        clean["Volume"] = pd.to_numeric(clean["Volume"], errors="coerce")
        clean = clean.dropna(subset=["Close"])

        if clean.empty or len(clean) < 5:
            return None

        clean["returns"] = clean["Close"].pct_change()
        clean = clean.replace([np.inf, -np.inf], np.nan)
        return clean
    except Exception:
        return None


def calculate_score(data: Optional[pd.DataFrame]) -> Optional[float]:
    """计算稳健评分：score = momentum * 100 - volatility * 50。"""
    try:
        if data is None or data.empty or "returns" not in data.columns:
            return None

        returns = pd.to_numeric(data["returns"], errors="coerce").dropna()
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()

        if returns.empty:
            return None

        momentum = float(returns.mean())
        volatility = float(returns.std(ddof=0))

        if np.isnan(momentum) or np.isnan(volatility):
            return None

        # 防止异常极端值影响家庭展示
        momentum = float(np.clip(momentum, -0.2, 0.2))
        volatility = float(max(volatility, 0.0))

        score = (momentum * 100) - (volatility * 50)
        return round(float(score), 4)
    except Exception:
        return None


def build_ranking() -> tuple[pd.DataFrame, dict[str, Optional[pd.DataFrame]]]:
    """获取全部股票数据并生成排名表。"""
    rows = []
    data_map: dict[str, Optional[pd.DataFrame]] = {}

    for stock in STOCK_POOL:
        data = fetch_stock_data(stock.ticker)
        data_map[stock.ticker] = data
        score = calculate_score(data)

        latest_close = None
        latest_volume = None
        if data is not None and not data.empty:
            try:
                latest_close = float(data["Close"].iloc[-1])
                latest_volume = float(data["Volume"].iloc[-1])
            except Exception:
                latest_close = None
                latest_volume = None

        rows.append(
            {
                "股票名称": stock.name,
                "股票代码": stock.ticker,
                "当前评分": score if score is not None else np.nan,
                "最新收盘价": latest_close if latest_close is not None else np.nan,
                "成交量": latest_volume if latest_volume is not None else np.nan,
                "状态": "正常" if score is not None else "数据缺失",
            }
        )

    ranking = pd.DataFrame(rows)
    ranking = ranking.sort_values(
        by=["当前评分", "股票名称"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)
    return ranking, data_map


def format_display_table(ranking: pd.DataFrame) -> pd.DataFrame:
    """格式化排名表，便于家庭用户阅读。"""
    display = ranking.copy()
    display.insert(0, "排名", range(1, len(display) + 1))
    display["当前评分"] = display["当前评分"].apply(
        lambda x: "数据暂不可用" if pd.isna(x) else f"{x:.4f}"
    )
    display["最新收盘价"] = display["最新收盘价"].apply(
        lambda x: "数据暂不可用" if pd.isna(x) else f"{x:.2f}"
    )
    display["成交量"] = display["成交量"].apply(
        lambda x: "数据暂不可用" if pd.isna(x) else f"{int(x):,}"
    )
    return display[["排名", "股票名称", "股票代码", "当前评分", "最新收盘价", "成交量", "状态"]]


def plot_close_price(stock_name: str, ticker: str, data: Optional[pd.DataFrame]) -> None:
    """绘制近 6 个月收盘价走势。"""
    if data is None or data.empty or "Close" not in data.columns:
        st.info("该股票数据暂不可用，无法显示走势。")
        return

    try:
        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.plot(data.index, data["Close"], linewidth=2)
        ax.set_title(f"{stock_name}（{ticker}）近6个月收盘价走势")
        ax.set_xlabel("日期")
        ax.set_ylabel("收盘价")
        ax.grid(True, alpha=0.25)
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)
    except Exception:
        st.info("走势图暂时无法显示，但页面其他功能仍可使用。")


def show_top_bottom(ranking: pd.DataFrame) -> None:
    """展示 Top3 和 Bottom3。"""
    valid = ranking.dropna(subset=["当前评分"]).copy()
    if valid.empty:
        st.info("当前没有可用于排名的数据。")
        return

    top3 = valid.head(3)
    bottom3 = valid.tail(3).sort_values("当前评分", ascending=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 当前 Top3")
        st.dataframe(
            top3[["股票名称", "股票代码", "当前评分"]].style.format({"当前评分": "{:.4f}"}),
            use_container_width=True,
            hide_index=True,
        )
    with col2:
        st.markdown("#### 当前 Bottom3")
        st.dataframe(
            bottom3[["股票名称", "股票代码", "当前评分"]].style.format({"当前评分": "{:.4f}"}),
            use_container_width=True,
            hide_index=True,
        )


def show_family_explanation() -> None:
    """家庭解释模块。"""
    st.markdown("### 家庭解释")
    st.markdown(
        """
        <div class="simple-card">
        <p><strong>什么是评分？</strong><br>
        这个评分只看两个简单因素：最近一段时间平均是涨多一点还是跌多一点，以及每天价格起伏大不大。</p>

        <p><strong>为什么有涨有跌？</strong><br>
        股票价格会受到公司经营、市场情绪、行业消息、资金流动等很多因素影响，所以短期上涨或下跌都很正常。</p>

        <p><strong>怎么看这个工具？</strong><br>
        排名靠前，只表示它在这个简单模型里“近期表现相对更稳一些”；排名靠后，也不代表一定不好。</p>

        <p><strong>风险说明：</strong><br>
        股票不是存款，价格可能上涨，也可能下跌。本页面只是帮助家人学习观察数据，不用于买卖决策。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# 主页面
# =========================

def main() -> None:
    st.title("家庭版中国股票准实时选股系统 V5")
    st.caption("页面刷新或自动刷新时，会重新获取数据并计算排名。")

    st.warning("⚠️ 本工具仅用于学习与模拟\n\n⚠️ 不构成投资建议\n\n⚠️ 股票投资有风险")

    with st.sidebar:
        st.header("设置")
        selected_stock_label = st.selectbox(
            "选择股票查看走势",
            [f"{stock.name}（{stock.ticker}）" for stock in STOCK_POOL],
        )
        refresh_seconds = st.radio("刷新间隔", [60, 120, 300], index=1, horizontal=True)
        st.caption("刷新后会重新获取 yfinance 数据。")

    refresh_count = st_autorefresh(
        interval=refresh_seconds * 1000,
        key="stock_autorefresh",
    )

    st.caption(f"自动刷新间隔：{refresh_seconds} 秒｜本页第 {refresh_count + 1} 次加载")

    with st.spinner("正在获取真实股票数据，请稍候..."):
        ranking, data_map = build_ranking()

    st.markdown("### 股票稳健性排名")
    st.dataframe(format_display_table(ranking), use_container_width=True, hide_index=True)

    normal_count = int((ranking["状态"] == "正常").sum())
    missing_count = int((ranking["状态"] == "数据缺失").sum())

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("股票池数量", len(ranking))
    with col2:
        st.metric("数据正常", normal_count)
    with col3:
        st.metric("数据缺失", missing_count)

    stock_index = [f"{stock.name}（{stock.ticker}）" for stock in STOCK_POOL].index(selected_stock_label)
    selected_stock = STOCK_POOL[stock_index]

    st.markdown("### 单股实时走势")
    plot_close_price(
        selected_stock.name,
        selected_stock.ticker,
        data_map.get(selected_stock.ticker),
    )

    st.markdown("### 实时排名变化")
    show_top_bottom(ranking)

    show_family_explanation()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        st.error("页面暂时遇到问题，请刷新后重试。单只股票数据失败不会影响整体使用。")
