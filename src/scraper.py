from __future__ import annotations

import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

from .config import (
    BILIBILI_RANK_API,
    BILIBILI_REPLY_API,
    DEFAULT_HEADERS,
    REQUEST_TIMEOUT,
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class BilibiliHotScraper:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_hot_videos(self, limit: int = 30) -> list[dict[str, Any]]:
        params = {"rid": 0, "type": "all"}
        response = self.session.get(BILIBILI_RANK_API, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        payload = response.json()
        raw_list = payload.get("data", {}).get("list")
        if raw_list is None and isinstance(payload.get("data"), list):
            raw_list = payload.get("data", [])
        if raw_list is None:
            raw_list = []

        hot_videos: list[dict[str, Any]] = []
        for item in raw_list[: max(0, limit)]:
            stat = item.get("stat", {}) if isinstance(item, dict) else {}
            owner = item.get("owner", {}) if isinstance(item, dict) else {}
            aid = _safe_int(item.get("aid"))
            bvid = str(item.get("bvid", ""))

            hot_videos.append(
                {
                    "aid": aid,
                    "bvid": bvid,
                    "title": str(item.get("title", "")).strip(),
                    "author": str(owner.get("name", "未知")),
                    "views": _safe_int(stat.get("view")),
                    "replies": _safe_int(stat.get("reply")),
                    "danmaku": _safe_int(stat.get("danmaku")),
                    "likes": _safe_int(stat.get("like")),
                    "description": str(item.get("desc", "")).strip(),
                    "pubdate": _safe_int(item.get("pubdate")),
                    "url": f"https://www.bilibili.com/video/{bvid}" if bvid else "",
                    "comments": [],
                }
            )

        return hot_videos

    def fetch_video_comments(
        self,
        aid: int,
        max_pages: int = 2,
        page_size: int = 20,
        sleep_seconds: float = 0.2,
    ) -> list[str]:
        comments: list[str] = []

        for page in range(1, max_pages + 1):
            params = {
                "pn": page,
                "type": 1,
                "oid": aid,
                "sort": 2,
                "nohot": 1,
                "ps": page_size,
            }

            try:
                response = self.session.get(
                    BILIBILI_REPLY_API,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError):
                break

            replies = payload.get("data", {}).get("replies") or []
            if not replies:
                break

            page_comment_count = 0
            for reply in replies:
                message = str(reply.get("content", {}).get("message", "")).strip()
                if message:
                    comments.append(message)
                    page_comment_count += 1

            if page_comment_count == 0:
                break

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        return comments

    def fetch_hot_with_comments(
        self,
        video_limit: int = 30,
        comment_pages: int = 2,
        page_size: int = 20,
        sleep_seconds: float = 0.2,
    ) -> list[dict[str, Any]]:
        hot_videos = self.fetch_hot_videos(limit=video_limit)
        for video in hot_videos:
            aid = _safe_int(video.get("aid"))
            if aid <= 0:
                continue
            video["comments"] = self.fetch_video_comments(
                aid=aid,
                max_pages=comment_pages,
                page_size=page_size,
                sleep_seconds=sleep_seconds,
            )
        return hot_videos


class GenericWebsiteHotScraper:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_topics(
        self,
        url: str,
        item_selector: str,
        title_selector: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(item_selector)

        topics: list[dict[str, Any]] = []
        for index, item in enumerate(items[: max(0, limit)], start=1):
            title_node = item.select_one(title_selector) if title_selector else item
            if title_node is None:
                continue

            title = re.sub(r"\s+", " ", title_node.get_text(" ", strip=True)).strip()
            if not title:
                continue

            topics.append(
                {
                    "rank": index,
                    "title": title,
                }
            )

        return topics
