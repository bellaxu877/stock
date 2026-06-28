"""页面展示与格式化工具。"""

from __future__ import annotations

import pandas as pd


def format_percent(value: float) -> str:
    """把比例格式化成百分比。"""
    return f"{value * 100:.1f}%"


def make_top10_table(scored_data: pd.DataFrame) -> pd.DataFrame:
    """整理页面 Top10 表格字段。"""
    top10 = scored_data.head(10).copy()
    top10.insert(0, "排名", range(1, len(top10) + 1))

    display = pd.DataFrame(
        {
            "排名": top10["排名"],
            "股票名称": top10["name"] + "（" + top10["ticker"] + "）",
            "综合评分": top10["score"].map(lambda x: f"{x:.1f}"),
            "ROE": top10["roe"].map(format_percent),
            "负债率": top10["debt_ratio"].map(format_percent),
            "波动率": top10["volatility"].map(format_percent),
            "风险等级": top10["risk_level"],
        }
    )
    return display


def make_detail_table(row: pd.Series) -> pd.DataFrame:
    """生成单只股票详情表。"""
    return pd.DataFrame(
        {
            "项目": [
                "股票代码",
                "当前股价",
                "净资产收益率 ROE",
                "营收增长",
                "净利率",
                "负债率",
                "现金流是否为正",
                "波动率",
                "综合评分",
                "风险等级",
            ],
            "数值": [
                row["ticker"],
                f"{row['price']:.2f}",
                format_percent(row["roe"]),
                format_percent(row["revenue_growth"]),
                format_percent(row["net_profit_margin"]),
                format_percent(row["debt_ratio"]),
                "是" if int(row["cash_flow_positive"]) == 1 else "否",
                format_percent(row["volatility"]),
                f"{row['score']:.1f}",
                row["risk_level"],
            ],
        }
    )


def risk_badge_color(risk_level: str) -> str:
    """给风险等级匹配柔和颜色。"""
    if risk_level == "低":
        return "#16803c"
    if risk_level == "中":
        return "#a16207"
    return "#b91c1c"
