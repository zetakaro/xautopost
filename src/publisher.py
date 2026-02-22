"""X API投稿モジュール - tweepyを使った投稿処理"""

import time
import logging
import tweepy

logger = logging.getLogger("x-auto-poster")


class Publisher:
    """X APIへのツイート投稿を管理"""

    def __init__(self, api_key: str, api_secret: str,
                 access_token: str, access_token_secret: str):
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

    def post_tweet(self, text: str, reply_to: str = None,
                   max_retries: int = 3) -> dict | None:
        """
        ツイートを投稿する

        Args:
            text: ツイート本文
            reply_to: リプライ先のツイートID（スレッド用）
            max_retries: リトライ回数

        Returns:
            {"id": str, "text": str} or None
        """
        for attempt in range(max_retries):
            try:
                kwargs = {"text": text}
                if reply_to:
                    kwargs["in_reply_to_tweet_id"] = reply_to

                response = self.client.create_tweet(**kwargs)

                tweet_id = response.data["id"]
                logger.info(f"投稿成功: ID={tweet_id}, 文字数={len(text)}")
                return {"id": str(tweet_id), "text": text}

            except tweepy.TooManyRequests:
                wait = 60 * (2 ** attempt)
                logger.warning(
                    f"レート制限。{wait}秒待機 (試行 {attempt + 1}/{max_retries})"
                )
                time.sleep(wait)

            except tweepy.Forbidden as e:
                logger.error(f"投稿拒否（権限エラー）: {e}")
                return None

            except tweepy.TwitterServerError as e:
                wait = 30 * (2 ** attempt)
                logger.warning(
                    f"Xサーバーエラー。{wait}秒待機: {e}"
                )
                time.sleep(wait)

            except Exception as e:
                logger.error(f"予期しないエラー: {e}")
                if attempt < max_retries - 1:
                    time.sleep(10 * (2 ** attempt))
                else:
                    return None

        logger.error(f"投稿失敗（リトライ上限）: {text[:50]}...")
        return None

    def post_thread(self, tweets: list[str]) -> list[dict]:
        """
        スレッドを投稿する

        Args:
            tweets: ツイートテキストのリスト（順序通り）

        Returns:
            投稿結果のリスト
        """
        results = []
        reply_to = None

        for i, text in enumerate(tweets):
            result = self.post_tweet(text, reply_to=reply_to)
            if result is None:
                logger.error(f"スレッド投稿中断: {i + 1}/{len(tweets)}で失敗")
                break
            results.append(result)
            reply_to = result["id"]

            # スレッド内の投稿間隔
            if i < len(tweets) - 1:
                time.sleep(2)

        return results

    def verify_credentials(self) -> bool:
        """API認証情報の確認"""
        try:
            me = self.client.get_me()
            if me.data:
                logger.info(f"認証OK: @{me.data.username}")
                return True
            return False
        except Exception as e:
            logger.error(f"認証エラー: {e}")
            return False
