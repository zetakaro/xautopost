"""X Auto Poster - メインエントリーポイント"""

import argparse
import os
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from src.logger import setup_logger, PostHistory
from src.tweet_generator import TweetGenerator
from src.scheduler import PostScheduler
from src.publisher import Publisher

# .envファイル読み込み
load_dotenv()


def load_config() -> dict:
    """設定ファイル読み込み"""
    config_path = Path(__file__).parent / "config" / "accounts.yaml"
    if not config_path.exists():
        print("❌ config/accounts.yaml が見つかりません")
        print("   config/accounts.yaml.example をコピーして設定してください")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_publishers(config: dict) -> dict[str, Publisher]:
    """各アカウントのPublisherを生成"""
    publishers = {}
    for account_id, acc_config in config["accounts"].items():
        pub = Publisher(
            api_key=acc_config["api_key"],
            api_secret=acc_config["api_secret"],
            access_token=acc_config["access_token"],
            access_token_secret=acc_config["access_token_secret"],
        )
        publishers[account_id] = pub
    return publishers


def verify_all_credentials(publishers: dict) -> bool:
    """全アカウントの認証チェック"""
    all_ok = True
    for account_id, pub in publishers.items():
        if not pub.verify_credentials():
            print(f"❌ {account_id}: 認証失敗")
            all_ok = False
    return all_ok


def run_once(config: dict, generator: TweetGenerator,
             publishers: dict, history: PostHistory,
             dry_run: bool = False):
    """全アカウントに対して1回ずつ投稿"""
    for account_id, acc_config in config["accounts"].items():
        logger.info(f"--- [{account_id}] 投稿生成中 ---")

        # ツイート生成
        result = generator.generate(account_id, acc_config)
        logger.info(f"生成: [{result['category']}] {result['text'][:60]}...")

        if dry_run:
            logger.info(f"[DRY RUN] スキップ: {result['text']}")
            if result["is_thread"]:
                for i, t in enumerate(result["thread_texts"]):
                    logger.info(f"  スレッド {i+1}: {t}")
            continue

        # 投稿
        pub = publishers[account_id]
        if result["is_thread"] and result["thread_texts"]:
            post_results = pub.post_thread(result["thread_texts"])
            tweet_id = post_results[0]["id"] if post_results else None
        else:
            post_result = pub.post_tweet(result["text"])
            tweet_id = post_result["id"] if post_result else None

        # 履歴に追加
        if tweet_id:
            history.add(
                account_id=account_id,
                tweet_text=result["text"],
                tweet_id=tweet_id,
                category=result["category"],
            )
            logger.info(f"✅ [{account_id}] 投稿完了: {tweet_id}")
        else:
            logger.error(f"❌ [{account_id}] 投稿失敗")


def run_scheduler(config: dict, generator: TweetGenerator,
                  publishers: dict, history: PostHistory,
                  dry_run: bool = False):
    """スケジューラーモード（常駐）"""
    scheduler = PostScheduler()

    logger.info("=" * 50)
    logger.info("X Auto Poster スケジューラー起動")
    logger.info(f"ドライラン: {'ON' if dry_run else 'OFF'}")
    logger.info("=" * 50)

    # 初回スケジュール生成
    for account_id, acc_config in config["accounts"].items():
        scheduler.generate_daily_schedule(
            account_id, acc_config["schedule"]
        )

    last_schedule_date = datetime.now().date()

    try:
        while True:
            now = datetime.now()

            # 日付が変わったらスケジュール再生成
            if now.date() != last_schedule_date:
                logger.info("--- 日次スケジュール再生成 ---")
                for account_id, acc_config in config["accounts"].items():
                    scheduler.generate_daily_schedule(
                        account_id, acc_config["schedule"]
                    )
                last_schedule_date = now.date()

            # 各アカウントの投稿チェック
            for account_id, acc_config in config["accounts"].items():
                tz = acc_config["schedule"]["timezone"]

                if scheduler.should_post_now(account_id, tz):
                    local_time = datetime.now(ZoneInfo(tz))
                    logger.info(
                        f"⏰ [{account_id}] 投稿時刻到達 "
                        f"({local_time.strftime('%H:%M %Z')})"
                    )

                    # ツイート生成
                    result = generator.generate(account_id, acc_config)

                    if dry_run:
                        logger.info(
                            f"[DRY RUN] [{account_id}] "
                            f"[{result['category']}] {result['text']}"
                        )
                        if result["is_thread"]:
                            for i, t in enumerate(result["thread_texts"]):
                                logger.info(f"  スレッド {i+1}: {t}")
                        history.add(
                            account_id, result["text"],
                            "dry-run", result["category"]
                        )
                        continue

                    # 投稿実行
                    pub = publishers[account_id]
                    if result["is_thread"] and result["thread_texts"]:
                        post_results = pub.post_thread(result["thread_texts"])
                        tweet_id = (
                            post_results[0]["id"] if post_results else None
                        )
                    else:
                        post_result = pub.post_tweet(result["text"])
                        tweet_id = (
                            post_result["id"] if post_result else None
                        )

                    if tweet_id:
                        history.add(
                            account_id, result["text"],
                            tweet_id, result["category"]
                        )
                        logger.info(f"✅ [{account_id}] 投稿完了: {tweet_id}")
                    else:
                        logger.error(f"❌ [{account_id}] 投稿失敗")

            # 30秒ごとにチェック
            time.sleep(30)

    except KeyboardInterrupt:
        logger.info("スケジューラー停止（Ctrl+C）")


def main():
    parser = argparse.ArgumentParser(description="X Auto Poster")
    parser.add_argument(
        "--once", action="store_true",
        help="全アカウントに1回ずつ投稿して終了"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="投稿せずに生成結果のみ表示"
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="API認証の確認のみ"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="直近の投稿履歴を表示"
    )
    args = parser.parse_args()

    # 環境変数チェック
    dry_run = args.dry_run or os.getenv("DRY_RUN", "false").lower() == "true"

    # 設定読み込み
    config = load_config()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print("❌ ANTHROPIC_API_KEY が設定されていません (.env ファイルを確認)")
        sys.exit(1)

    # コンポーネント初期化
    generator = TweetGenerator(api_key=anthropic_key)
    history = PostHistory()
    publishers = create_publishers(config)

    # --verify: 認証チェックのみ
    if args.verify:
        if verify_all_credentials(publishers):
            print("✅ 全アカウントの認証OK")
        else:
            print("❌ 認証エラーあり")
        return

    # --status: 履歴表示
    if args.status:
        for account_id in config["accounts"]:
            posts = history.get_recent(account_id, 5)
            print(f"\n--- {account_id} (直近5件) ---")
            if not posts:
                print("  (投稿履歴なし)")
            for p in posts:
                print(f"  [{p['timestamp'][:16]}] [{p.get('category', '')}]")
                print(f"    {p['text'][:80]}...")
        return

    # --once: 1回投稿
    if args.once:
        run_once(config, generator, publishers, history, dry_run)
        return

    # デフォルト: スケジューラー起動
    if not dry_run:
        if not verify_all_credentials(publishers):
            print("❌ 認証エラー。config/accounts.yaml を確認してください")
            sys.exit(1)

    run_scheduler(config, generator, publishers, history, dry_run)


if __name__ == "__main__":
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger = setup_logger(log_level)
    main()
