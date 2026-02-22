"""ログ管理モジュール - 投稿履歴とアプリケーションログ"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """アプリケーションロガーのセットアップ"""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("x-auto-poster")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # コンソール出力
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(console)

    # ファイル出力
    file_handler = logging.FileHandler(
        log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    ))
    logger.addHandler(file_handler)

    return logger


class PostHistory:
    """投稿履歴の管理（重複チェック用）"""

    def __init__(self, history_dir: str = None):
        if history_dir is None:
            history_dir = Path(__file__).parent.parent / "logs"
        self.history_file = Path(history_dir) / "post_history.json"
        self.history_file.parent.mkdir(exist_ok=True)
        self._load()

    def _load(self):
        if self.history_file.exists():
            with open(self.history_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {"posts": []}

    def _save(self):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add(self, account_id: str, tweet_text: str, tweet_id: str = None,
            category: str = None):
        """投稿を履歴に追加"""
        entry = {
            "account": account_id,
            "text": tweet_text,
            "tweet_id": tweet_id,
            "category": category,
            "timestamp": datetime.now().isoformat(),
        }
        self.data["posts"].append(entry)
        # 直近500件のみ保持
        self.data["posts"] = self.data["posts"][-500:]
        self._save()

    def get_recent(self, account_id: str, count: int = 20) -> list:
        """指定アカウントの直近の投稿を取得"""
        account_posts = [
            p for p in self.data["posts"] if p["account"] == account_id
        ]
        return account_posts[-count:]

    def get_recent_texts(self, account_id: str, count: int = 20) -> list[str]:
        """直近の投稿テキストのみ取得（重複チェック用）"""
        return [p["text"] for p in self.get_recent(account_id, count)]

    def get_last_post_time(self, account_id: str) -> datetime | None:
        """最後の投稿時刻を取得"""
        posts = self.get_recent(account_id, 1)
        if posts:
            return datetime.fromisoformat(posts[0]["timestamp"])
        return None
