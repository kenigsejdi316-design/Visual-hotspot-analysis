from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import jieba.analyse
import pandas as pd
from snownlp import SnowNLP

URL_PATTERN = re.compile(r"https?://\S+")
MENTION_PATTERN = re.compile(r"@[\w\-\u4e00-\u9fa5]+")
SPACE_PATTERN = re.compile(r"\s+")


def clean_text(text: str) -> str:
    normalized = str(text or "")
    normalized = URL_PATTERN.sub(" ", normalized)
    normalized = MENTION_PATTERN.sub(" ", normalized)
    normalized = normalized.replace("\n", " ").replace("\t", " ").replace("\r", " ")
    normalized = SPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()


def sentiment_score(text: str) -> float:
    if not text:
        return 0.5

    try:
        score = float(SnowNLP(text).sentiments)
    except Exception:
        score = 0.5

    return max(0.0, min(1.0, score))


def sentiment_label(score: float) -> str:
    if score >= 0.6:
        return "正向"
    if score <= 0.4:
        return "负向"
    return "中性"


def expand_comments(videos_df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []

    for _, row in videos_df.iterrows():
        comments = row.get("comments", [])
        if not isinstance(comments, list):
            continue

        for comment in comments:
            cleaned = clean_text(comment)
            if not cleaned:
                continue

            score = sentiment_score(cleaned)
            records.append(
                {
                    "aid": row.get("aid"),
                    "bvid": row.get("bvid", ""),
                    "title": row.get("title", ""),
                    "comment": str(comment),
                    "clean_comment": cleaned,
                    "sentiment_score": score,
                    "sentiment_label": sentiment_label(score),
                }
            )

    if not records:
        return pd.DataFrame(
            columns=[
                "aid",
                "bvid",
                "title",
                "comment",
                "clean_comment",
                "sentiment_score",
                "sentiment_label",
            ]
        )

    return pd.DataFrame(records)


def aggregate_video_sentiment(videos_df: pd.DataFrame, comments_df: pd.DataFrame) -> pd.DataFrame:
    output_df = videos_df.copy()
    if output_df.empty:
        return output_df

    if comments_df.empty:
        output_df["comment_count"] = 0
        output_df["avg_sentiment"] = 0.5
        output_df["positive_ratio"] = 0.0
        output_df["neutral_ratio"] = 0.0
        output_df["negative_ratio"] = 0.0
        output_df["sentiment_level"] = "中性"
        return output_df

    sentiment_avg = (
        comments_df.groupby("aid", as_index=False)["sentiment_score"]
        .mean()
        .rename(columns={"sentiment_score": "avg_sentiment"})
    )

    sentiment_count = (
        comments_df.pivot_table(
            index="aid",
            columns="sentiment_label",
            values="comment",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    for label in ["正向", "中性", "负向"]:
        if label not in sentiment_count.columns:
            sentiment_count[label] = 0

    sentiment_count["comment_count"] = (
        sentiment_count["正向"] + sentiment_count["中性"] + sentiment_count["负向"]
    )

    denominator = sentiment_count["comment_count"].replace(0, 1)
    sentiment_count["positive_ratio"] = sentiment_count["正向"] / denominator
    sentiment_count["neutral_ratio"] = sentiment_count["中性"] / denominator
    sentiment_count["negative_ratio"] = sentiment_count["负向"] / denominator

    metrics_df = sentiment_avg.merge(
        sentiment_count[
            [
                "aid",
                "comment_count",
                "positive_ratio",
                "neutral_ratio",
                "negative_ratio",
            ]
        ],
        on="aid",
        how="left",
    )

    output_df = output_df.merge(metrics_df, on="aid", how="left")
    output_df["comment_count"] = output_df["comment_count"].fillna(0).astype(int)
    output_df["avg_sentiment"] = output_df["avg_sentiment"].fillna(0.5)
    output_df["positive_ratio"] = output_df["positive_ratio"].fillna(0.0)
    output_df["neutral_ratio"] = output_df["neutral_ratio"].fillna(0.0)
    output_df["negative_ratio"] = output_df["negative_ratio"].fillna(0.0)
    output_df["sentiment_level"] = output_df["avg_sentiment"].apply(sentiment_label)

    return output_df


def extract_hot_keywords(comments_df: pd.DataFrame, top_k: int = 30) -> pd.DataFrame:
    if comments_df.empty:
        return pd.DataFrame(columns=["keyword", "weight"])

    text_corpus = " ".join(comments_df["clean_comment"].fillna("").astype(str).tolist()).strip()
    if not text_corpus:
        return pd.DataFrame(columns=["keyword", "weight"])

    tags = jieba.analyse.extract_tags(
        text_corpus,
        topK=max(1, top_k),
        withWeight=True,
        allowPOS=("n", "nr", "ns", "nt", "nz", "vn", "v", "a"),
    )

    rows = [{"keyword": word, "weight": round(float(weight), 4)} for word, weight in tags]
    return pd.DataFrame(rows)


def build_dashboard_summary(videos_df: pd.DataFrame, comments_df: pd.DataFrame) -> dict[str, Any]:
    avg_sentiment = (
        float(videos_df["avg_sentiment"].mean())
        if (not videos_df.empty and "avg_sentiment" in videos_df.columns)
        else 0.5
    )

    positive_video_ratio = (
        float((videos_df["avg_sentiment"] >= 0.6).mean())
        if (not videos_df.empty and "avg_sentiment" in videos_df.columns)
        else 0.0
    )

    return {
        "video_count": int(len(videos_df)),
        "total_comments": int(len(comments_df)),
        "avg_sentiment": round(avg_sentiment, 4),
        "positive_video_ratio": round(positive_video_ratio, 4),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
