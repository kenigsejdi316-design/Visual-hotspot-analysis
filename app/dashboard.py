from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"

VIDEOS_PATH = PROCESSED_DIR / "hot_videos_sentiment.csv"
COMMENTS_PATH = PROCESSED_DIR / "video_comments_sentiment.csv"
KEYWORDS_PATH = PROCESSED_DIR / "hot_keywords.csv"
SUMMARY_PATH = PROCESSED_DIR / "dashboard_summary.json"

st.set_page_config(page_title="热点情感分析大屏", page_icon="📊", layout="wide")


@st.cache_data(ttl=180)
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=180)
def load_summary(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


st.title("热点数据抓取与情感分析大屏")
st.caption("Python + Pandas + SnowNLP + 结巴分词 + Streamlit/ECharts")

if not VIDEOS_PATH.exists():
    st.warning("还没有检测到分析数据，请先运行：python -m src.pipeline --mode bilibili")
    st.stop()

videos_df = load_csv(VIDEOS_PATH)
comments_df = load_csv(COMMENTS_PATH)
keywords_df = load_csv(KEYWORDS_PATH)
summary = load_summary(SUMMARY_PATH)

if videos_df.empty:
    st.error("分析结果为空，请重新运行数据管道。")
    st.stop()

videos_df["avg_sentiment"] = videos_df.get("avg_sentiment", 0.5).fillna(0.5)
videos_df["comment_count"] = videos_df.get("comment_count", 0).fillna(0).astype(int)

col1, col2, col3, col4 = st.columns(4)

total_videos = int(summary.get("video_count", len(videos_df)))
total_comments = int(summary.get("total_comments", len(comments_df)))
avg_sentiment = float(summary.get("avg_sentiment", videos_df["avg_sentiment"].mean()))
positive_ratio = float(
    summary.get(
        "positive_video_ratio",
        float((videos_df["avg_sentiment"] >= 0.6).mean()),
    )
)

col1.metric("热点条目", f"{total_videos}")
col2.metric("评论总量", f"{total_comments}")
col3.metric("平均情感分", f"{avg_sentiment:.3f}")
col4.metric("正向视频占比", f"{positive_ratio * 100:.1f}%")

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("评论情感分布")
    if comments_df.empty or "sentiment_label" not in comments_df.columns:
        st.info("暂无评论级情感数据")
    else:
        sentiment_counts = comments_df["sentiment_label"].value_counts()
        pie_option = {
            "tooltip": {"trigger": "item"},
            "legend": {"left": "left"},
            "series": [
                {
                    "name": "情感类别",
                    "type": "pie",
                    "radius": "65%",
                    "data": [
                        {"name": "正向", "value": int(sentiment_counts.get("正向", 0))},
                        {"name": "中性", "value": int(sentiment_counts.get("中性", 0))},
                        {"name": "负向", "value": int(sentiment_counts.get("负向", 0))},
                    ],
                }
            ],
        }
        st_echarts(options=pie_option, height="360px")

with right_col:
    st.subheader("热点视频播放量 Top 10")
    top_view_df = videos_df.sort_values("views", ascending=False).head(10)
    bar_option = {
        "tooltip": {"trigger": "axis"},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {"type": "value", "name": "播放量"},
        "yAxis": {
            "type": "category",
            "data": top_view_df["title"].tolist()[::-1],
            "axisLabel": {"fontSize": 11},
        },
        "series": [
            {
                "name": "播放量",
                "type": "bar",
                "data": top_view_df["views"].astype(int).tolist()[::-1],
            }
        ],
    }
    st_echarts(options=bar_option, height="360px")

line1, line2 = st.columns(2)

with line1:
    st.subheader("评论数 vs 情感分")
    scatter_data = [
        [int(row["comment_count"]), float(row["avg_sentiment"])]
        for _, row in videos_df[["comment_count", "avg_sentiment"]].iterrows()
    ]
    scatter_option = {
        "tooltip": {"trigger": "item"},
        "xAxis": {"type": "value", "name": "评论数"},
        "yAxis": {"type": "value", "name": "平均情感分", "min": 0, "max": 1},
        "series": [{"type": "scatter", "data": scatter_data, "symbolSize": 12}],
    }
    st_echarts(options=scatter_option, height="320px")

with line2:
    st.subheader("高频关键词 Top 15")
    if keywords_df.empty:
        st.info("暂无关键词数据")
    else:
        top_keywords_df = keywords_df.head(15)
        keyword_option = {
            "tooltip": {"trigger": "axis"},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "xAxis": {"type": "category", "data": top_keywords_df["keyword"].tolist()},
            "yAxis": {"type": "value", "name": "权重"},
            "series": [
                {
                    "name": "权重",
                    "type": "bar",
                    "data": top_keywords_df["weight"].astype(float).tolist(),
                }
            ],
        }
        st_echarts(options=keyword_option, height="320px")

st.subheader("热点详情")
show_columns = [
    column
    for column in [
        "title",
        "author",
        "views",
        "comment_count",
        "avg_sentiment",
        "sentiment_level",
        "url",
    ]
    if column in videos_df.columns
]

st.dataframe(
    videos_df[show_columns].sort_values("avg_sentiment", ascending=False),
    width="stretch",
    height=460,
)
