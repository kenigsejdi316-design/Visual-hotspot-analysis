from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .config import PROCESSED_DIR, RAW_DIR
from .processing import (
    aggregate_video_sentiment,
    build_dashboard_summary,
    expand_comments,
    extract_hot_keywords,
)
from .scraper import BilibiliHotScraper, GenericWebsiteHotScraper


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def persist_outputs(
    videos_df: pd.DataFrame,
    comments_df: pd.DataFrame,
    keywords_df: pd.DataFrame,
    summary: dict[str, Any],
) -> dict[str, Path]:
    videos_path = PROCESSED_DIR / "hot_videos_sentiment.csv"
    comments_path = PROCESSED_DIR / "video_comments_sentiment.csv"
    keywords_path = PROCESSED_DIR / "hot_keywords.csv"
    summary_path = PROCESSED_DIR / "dashboard_summary.json"

    sorted_videos_df = videos_df.sort_values(
        by=["avg_sentiment", "views"],
        ascending=[False, False],
    )

    sorted_videos_df.to_csv(videos_path, index=False, encoding="utf-8-sig")
    comments_df.to_csv(comments_path, index=False, encoding="utf-8-sig")
    keywords_df.to_csv(keywords_path, index=False, encoding="utf-8-sig")
    save_json(summary_path, summary)

    return {
        "videos": videos_path,
        "comments": comments_path,
        "keywords": keywords_path,
        "summary": summary_path,
    }


def run_bilibili_pipeline(
    video_limit: int,
    comment_pages: int,
    page_size: int,
    sleep_seconds: float,
) -> dict[str, Path]:
    scraper = BilibiliHotScraper()
    hot_videos = scraper.fetch_hot_with_comments(
        video_limit=video_limit,
        comment_pages=comment_pages,
        page_size=page_size,
        sleep_seconds=sleep_seconds,
    )
    if not hot_videos:
        raise RuntimeError("未获取到 B 站热点数据，请稍后重试。")

    raw_path = RAW_DIR / "bilibili_hot_raw.json"
    save_json(raw_path, hot_videos)

    videos_df = pd.DataFrame(hot_videos)
    comments_df = expand_comments(videos_df)
    videos_df = aggregate_video_sentiment(videos_df, comments_df)
    keywords_df = extract_hot_keywords(comments_df, top_k=30)
    summary = build_dashboard_summary(videos_df, comments_df)

    outputs = persist_outputs(videos_df, comments_df, keywords_df, summary)
    outputs["raw"] = raw_path
    return outputs


def run_website_pipeline(
    url: str,
    item_selector: str,
    title_selector: str,
    topic_limit: int,
) -> dict[str, Path]:
    scraper = GenericWebsiteHotScraper()
    topics = scraper.fetch_topics(
        url=url,
        item_selector=item_selector,
        title_selector=title_selector or None,
        limit=topic_limit,
    )
    if not topics:
        raise RuntimeError("未从指定网站提取到热点条目，请检查 CSS 选择器。")

    raw_path = RAW_DIR / "website_hot_raw.json"
    save_json(raw_path, topics)

    pseudo_videos = []
    for topic in topics:
        rank = int(topic.get("rank", 0))
        title = str(topic.get("title", "")).strip()
        pseudo_videos.append(
            {
                "aid": rank,
                "bvid": "",
                "title": title,
                "author": "未知",
                "views": 0,
                "replies": 0,
                "danmaku": 0,
                "likes": 0,
                "description": "",
                "pubdate": 0,
                "url": url,
                "comments": [title],
            }
        )

    videos_df = pd.DataFrame(pseudo_videos)
    comments_df = expand_comments(videos_df)
    videos_df = aggregate_video_sentiment(videos_df, comments_df)
    keywords_df = extract_hot_keywords(comments_df, top_k=30)
    summary = build_dashboard_summary(videos_df, comments_df)

    outputs = persist_outputs(videos_df, comments_df, keywords_df, summary)
    outputs["raw"] = raw_path
    return outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="热点抓取与情感分析数据管道")
    parser.add_argument("--mode", choices=["bilibili", "website"], default="bilibili")
    parser.add_argument("--video-limit", type=int, default=30)
    parser.add_argument("--comment-pages", type=int, default=2)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.2)

    parser.add_argument("--url", type=str, default="")
    parser.add_argument("--item-selector", type=str, default="")
    parser.add_argument("--title-selector", type=str, default="")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.mode == "bilibili":
        outputs = run_bilibili_pipeline(
            video_limit=max(1, args.video_limit),
            comment_pages=max(1, args.comment_pages),
            page_size=max(1, args.page_size),
            sleep_seconds=max(0.0, args.sleep),
        )
    else:
        if not args.url or not args.item_selector:
            raise ValueError("website 模式需要提供 --url 和 --item-selector。")
        outputs = run_website_pipeline(
            url=args.url,
            item_selector=args.item_selector,
            title_selector=args.title_selector,
            topic_limit=max(1, args.video_limit),
        )

    print("数据处理完成：")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
