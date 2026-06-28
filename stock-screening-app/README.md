# 家庭版稳健选股系统 V1.0

这是一个用于学习与家庭展示的 Streamlit Web 应用，提供“稳健型股票筛选 + 可解释推荐 + 简单模拟收益展示”。

> 重要提示：本工具仅用于学习与模拟，不构成任何投资建议。股票投资存在亏损风险，历史数据不代表未来收益。

## 功能

- 自动使用模拟股票数据，也可尝试通过 yfinance 获取公开数据
- 对股票进行 100 分制稳健评分
- 输出 Top10 推荐列表
- 用适合家人理解的语言解释推荐原因
- 提供醒目的风险提示
- 提供教学级收益模拟曲线
- 支持搜索、风险偏好筛选和简单排序

## 文件结构

```text
app.py          Streamlit 主程序
data.py         数据生成与 yfinance 获取
scoring.py      稳健评分逻辑
backtest.py     教学级模拟回测
utils.py        页面展示工具函数
requirements.txt 依赖列表
```

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

打开页面后，左侧可以选择股票池、风险偏好、是否开启收益模拟。

## 部署到 Streamlit Community Cloud

1. 把本项目上传到 GitHub 仓库
2. 打开 Streamlit Community Cloud
3. 选择该 GitHub 仓库
4. 主文件选择 `app.py`
5. 点击部署

## 评分模型

综合评分满分 100 分：

- 盈利能力 40%：ROE、净利率
- 成长能力 20%：营收增长
- 财务健康 25%：负债率、现金流
- 风险控制 15%：波动率

所有指标会先标准化，再合成为综合评分。分数高只代表更符合本模型的稳健标准，不代表未来收益。
