"""スケジュール管理モジュール - コアタイム内のランダム投稿時刻を生成"""

import random
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger("x-auto-poster")


class PostScheduler:
    """各アカウントの投稿スケジュールを管理"""

    def __init__(self):
        self.schedules: dict[str, list[datetime]] = {}

    def generate_daily_schedule(self, account_id: str,
                                schedule_config: dict) -> list[datetime]:
        """
        1日分の投稿スケジュールを生成

        Args:
            account_id: アカウント識別子
            schedule_config: schedule設定

        Returns:
            投稿予定時刻のリスト（UTCのdatetime）
        """
        tz = ZoneInfo(schedule_config["timezone"])
        now_local = datetime.now(tz)
        today = now_local.date()

        posts_per_day = schedule_config.get("posts_per_day", 4)
        # 3〜5の範囲でランダムに変動させる
        actual_posts = random.randint(
            max(3, posts_per_day - 1),
            min(5, posts_per_day + 1)
        )

        core_start = schedule_config.get("core_hours_start", 8)
        core_end = schedule_config.get("core_hours_end", 22)
        min_interval = schedule_config.get("min_interval_hours", 2)

        # コアタイム内でランダムな時刻を生成
        times = []
        available_minutes = list(range(core_start * 60, core_end * 60))

        for _ in range(actual_posts):
            if not available_minutes:
                break

            minute = random.choice(available_minutes)
            hour = minute // 60
            mins = minute % 60
            # 秒もランダムに（bot感を減らす）
            secs = random.randint(0, 59)

            post_time = datetime(
                today.year, today.month, today.day,
                hour, mins, secs,
                tzinfo=tz
            )

            # この時刻の前後min_interval時間を除外
            exclude_start = minute - (min_interval * 60)
            exclude_end = minute + (min_interval * 60)
            available_minutes = [
                m for m in available_minutes
                if m < exclude_start or m > exclude_end
            ]

            times.append(post_time)

        times.sort()
        self.schedules[account_id] = times

        logger.info(
            f"[{account_id}] 本日のスケジュール生成: {len(times)}件 "
            f"({schedule_config['timezone']})"
        )
        for t in times:
            logger.info(f"  → {t.strftime('%H:%M:%S %Z')}")

        return times

    def get_next_post_time(self, account_id: str,
                           timezone: str) -> datetime | None:
        """次の投稿予定時刻を取得"""
        if account_id not in self.schedules:
            return None

        tz = ZoneInfo(timezone)
        now = datetime.now(tz)

        for t in self.schedules[account_id]:
            if t > now:
                return t

        return None

    def should_post_now(self, account_id: str, timezone: str,
                        tolerance_seconds: int = 120) -> bool:
        """
        今投稿すべきかチェック

        Args:
            account_id: アカウント識別子
            timezone: タイムゾーン
            tolerance_seconds: 許容誤差（秒）

        Returns:
            投稿すべきならTrue
        """
        if account_id not in self.schedules:
            return False

        tz = ZoneInfo(timezone)
        now = datetime.now(tz)

        for i, t in enumerate(self.schedules[account_id]):
            diff = abs((now - t).total_seconds())
            if diff <= tolerance_seconds:
                # 使用済みとしてマーク（リストから除去）
                self.schedules[account_id].pop(i)
                return True

        return False

    def is_schedule_done(self, account_id: str) -> bool:
        """本日のスケジュールが完了したか"""
        return (
            account_id in self.schedules
            and len(self.schedules[account_id]) == 0
        )

    def get_status(self) -> dict:
        """全アカウントのスケジュール状況"""
        status = {}
        for account_id, times in self.schedules.items():
            status[account_id] = {
                "remaining": len(times),
                "next": times[0].isoformat() if times else None,
            }
        return status
