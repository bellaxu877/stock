"""家庭版稳健选股系统 V1.0。

运行方式：
streamlit run app.py
"""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from backtest import run_simple_backtest
from data import load_stock_data
from scoring import apply_risk_preference, score_stocks
from utils import make_detail_table, make_top10_table, risk_badge_color


st.set_page_config(
    page_title="家庭版稳健选股系统 V1.0",
    page_icon="🏠",
    layout="wide",
)


CUSTOM_CSS = """
<style>
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1180px;
    }
    .risk-box {
        border: 2px solid #dc2626;
        background: #fff1f2;
        color: #7f1d1d;
        padding: 18px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 16px;
        line-height: 1.65;
    }
    .metric-card {
        border: 1px solid #e5e7eb;
        background: #ffffff;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
        min-height: 118px;
    }
    .metric-label {
        color: #64748b;
        font-size: 14px;
    }
    .metric-value {
        color: #0f172a;
        font-size: 25px;
        font-weight: 700;
        margin-top: 8px;
    }
    .plain-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 18px;
        background: #ffffff;
        margin-top: 10px;
        line-height: 1.8;
    }
    .small-note {
        color: #64748b;
        font-size: 14px;
        line-height: 1.6;
    }
</style>
"""


def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.title("家庭版稳健选股系统 V1.0")
    st.caption("用于学习与家庭展示，不是投资建议工具。")

    st.markdown(
        """
        <div class="risk-box">
        <strong>⚠️ 风险提示：</strong><br>
        - 本工具仅用于学习与模拟<br>
        - 不构成任何投资建议<br>
        - 股票投资存在亏损风险<br>
        - 历史数据不代表未来收益
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("设置")
        data_source = st.radio("股票池选择", ["模拟", "yfinance"], index=0)
        risk_preference = st.select_slider("风险偏好", options=["低", "中", "高"], value="中")
        enable_backtest = st.toggle("开启收益模拟", value=True)
        stock_count = st.slider("模拟股票数量", min_value=20, max_value=50, value=35, step=5)
        sort_by = st.selectbox("排序方式", ["综合评分", "风险更低", "ROE更高"], index=0)
        search_text = st.text_input("股票搜索", placeholder="输入代码或名称")

    raw_data, source_note = load_stock_data(source=data_source, count=stock_count)
    scored_data = score_stocks(raw_data)
    filtered_data = apply_risk_preference(scored_data, risk_preference)

    if filtered_data.empty:
        st.warning("当前风险偏好下没有符合条件的股票，已自动显示完整股票池。")
        filtered_data = scored_data.copy()

    if search_text.strip():
        keyword = search_text.strip().lower()
        filtered_data = filtered_data[
            filtered_data["ticker"].str.lower().str.contains(keyword)
            | filtered_data["name"].str.lower().str.contains(keyword)
        ].copy()
        if filtered_data.empty:
            st.warning("没有找到匹配的股票，请换一个关键词。")
            filtered_data = apply_risk_preference(scored_data, risk_preference)

    filtered_data = sort_stocks(filtered_data, sort_by)

    st.info(source_note)

    top_pick = filtered_data.iloc[0]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("当前第一名", f"{top_pick['name']}", f"{top_pick['ticker']}")
    with col2:
        metric_card("综合评分", f"{top_pick['score']:.1f}", "满分 100")
    with col3:
        metric_card("风险等级", f"{top_pick['risk_level']}风险", "按波动率估算")
    with col4:
        metric_card("股票池数量", f"{len(filtered_data)}", "已按设置筛选")

    st.subheader("Section 1：Top10 推荐股票")
    st.dataframe(make_top10_table(filtered_data), use_container_width=True, hide_index=True)

    st.subheader("Section 2：单只股票解释")
    options = [
        f"{row.name + 1}. {row['name']}（{row['ticker']}）- {row['score']:.1f}分"
        for _, row in filtered_data.head(10).iterrows()
    ]
    selected_label = st.selectbox("选择一只股票查看详情", options)
    selected_index = options.index(selected_label)
    selected_row = filtered_data.head(10).iloc[selected_index]

    risk_color = risk_badge_color(selected_row["risk_level"])
    st.markdown(
        f"""
        <div class="plain-card">
        <h4 style="margin-top:0;">{selected_row['name']}（{selected_row['ticker']}）</h4>
        <p>{selected_row['explanation']}</p>
        <p><strong>风险等级：</strong>
        <span style="color:{risk_color}; font-weight:700;">{selected_row['risk_level']}风险</span></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(make_detail_table(selected_row), use_container_width=True, hide_index=True)

    st.subheader("Section 3：收益曲线图")
    if enable_backtest:
        backtest_data = run_simple_backtest(filtered_data)
        chart_data = backtest_data.melt(
            id_vars="date",
            value_vars=["策略组合", "模拟基准"],
            var_name="组合",
            value_name="资金余额",
        )
        fig = px.line(
            chart_data,
            x="date",
            y="资金余额",
            color="组合",
            markers=True,
            title="教学级模拟收益曲线：策略 vs 基准",
        )
        fig.update_layout(
            yaxis_title="资金余额",
            xaxis_title="日期",
            legend_title_text="",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        final_strategy = backtest_data["策略累计收益率"].iloc[-1]
        final_benchmark = backtest_data["基准累计收益率"].iloc[-1]
        st.caption(
            f"模拟结果：策略累计收益 {final_strategy:.1%}，模拟基准累计收益 {final_benchmark:.1%}。"
            "该结果由随机模拟生成，仅用于理解方法。"
        )
    else:
        st.info("已关闭收益模拟。可在左侧打开。")

    st.subheader("Section 4：评分模型说明")
    st.markdown(
        """
        <div class="plain-card">
        <p><strong>综合评分满分 100 分，偏向“稳健型”观察：</strong></p>
        <p>盈利能力占 40%：看 ROE 和净利率，理解为“公司是否比较会赚钱”。</p>
        <p>成长能力占 20%：看营收增长，理解为“生意规模有没有继续变大”。</p>
        <p>财务健康占 25%：看负债率和现金流，理解为“借的钱多不多，手里现金是否健康”。</p>
        <p>风险控制占 15%：看波动率，理解为“价格上下起伏是否剧烈”。</p>
        <p class="small-note">所有指标会先做标准化，再合成为综合评分。分数高只代表更符合本模型的稳健标准，不代表未来一定上涨。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str) -> None:
    """绘制简洁卡片。"""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="small-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sort_stocks(data, sort_by: str):
    """根据页面选择排序。"""
    if sort_by == "风险更低":
        return data.sort_values(["volatility", "score"], ascending=[True, False]).reset_index(drop=True)
    if sort_by == "ROE更高":
        return data.sort_values(["roe", "score"], ascending=[False, False]).reset_index(drop=True)
    return data.sort_values("score", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    main()
