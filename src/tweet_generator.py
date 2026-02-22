"""ツイート生成モジュール - Claude APIでツイートを自動生成"""

import random
from anthropic import Anthropic
from src.logger import PostHistory


class TweetGenerator:
    """Claude APIを使ったツイート生成"""

    def __init__(self, api_key: str, history: PostHistory = None):
        self.client = Anthropic(api_key=api_key)
        self.history = history or PostHistory()

    def _select_category(self, categories: list) -> dict:
        """重み付きランダムでカテゴリを選択"""
        weights = [c.get("weight", 1) for c in categories]
        return random.choices(categories, weights=weights, k=1)[0]

    def generate(self, account_id: str, config: dict) -> dict:
        """
        ツイートを生成する

        Args:
            account_id: アカウント識別子
            config: アカウントのcontent設定

        Returns:
            {"text": str, "category": str, "is_thread": bool, "thread_texts": list}
        """
        content_config = config["content"]
        style = content_config["style"]
        category = self._select_category(content_config["categories"])
        language = config.get("language", "en")

        # 直近の投稿を取得（重複防止用）
        recent_texts = self.history.get_recent_texts(account_id, 15)
        recent_context = ""
        if recent_texts:
            recent_context = (
                "\n\n<recent_posts>\n"
                "以下はこのアカウントの直近の投稿です。内容が重複しないようにしてください:\n"
                + "\n".join(f"- {t}" for t in recent_texts)
                + "\n</recent_posts>"
            )

        # スレッド投稿判定
        is_thread = random.random() < style.get("thread_probability", 0)

        if is_thread:
            return self._generate_thread(
                account_id, content_config, style, category,
                language, recent_context
            )
        else:
            return self._generate_single(
                account_id, content_config, style, category,
                language, recent_context
            )

    def _generate_single(self, account_id, content_config, style,
                         category, language, recent_context) -> dict:
        """単一ツイートを生成"""
        lang_instruction = {
            "en": "Write the tweet in English.",
            "ja": "ツイートは日本語で書いてください。"
        }.get(language, "Write the tweet in English.")

        hashtag_instruction = ""
        if style.get("use_hashtags"):
            max_h = style.get("max_hashtags", 2)
            hashtag_instruction = f"Include up to {max_h} relevant hashtags."

        emoji_instruction = ""
        if not style.get("use_emojis", False):
            emoji_instruction = "Do NOT use any emojis."

        prompt = f"""Generate a single tweet for the following topic.

<persona>
{content_config['persona']}
</persona>

<topic>{category['topic']}</topic>
<topic_description>{category.get('description', '')}</topic_description>

<rules>
- {lang_instruction}
- Maximum {style['max_characters']} characters (this is strict - count carefully)
- {hashtag_instruction}
- {emoji_instruction}
- Be original, insightful, and engaging
- Sound like a real person, not a corporate account or AI
- Vary sentence structure and format (questions, statements, observations, tips)
- Do NOT start with "Just" or generic filler phrases
</rules>
{recent_context}

Output ONLY the tweet text. No quotes, no explanation, no preamble."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        tweet_text = response.content[0].text.strip()

        # 文字数チェック（超過時は再生成ではなくトリム）
        if len(tweet_text) > style["max_characters"]:
            tweet_text = self._trim_tweet(tweet_text, style["max_characters"])

        return {
            "text": tweet_text,
            "category": category["topic"],
            "is_thread": False,
            "thread_texts": [],
        }

    def _generate_thread(self, account_id, content_config, style,
                         category, language, recent_context) -> dict:
        """スレッド（2〜4ツイート）を生成"""
        lang_instruction = {
            "en": "Write in English.",
            "ja": "日本語で書いてください。"
        }.get(language, "Write in English.")

        thread_count = random.randint(2, 4)

        prompt = f"""Generate a Twitter thread of exactly {thread_count} tweets.

<persona>
{content_config['persona']}
</persona>

<topic>{category['topic']}</topic>
<topic_description>{category.get('description', '')}</topic_description>

<rules>
- {lang_instruction}
- Each tweet must be under {style['max_characters']} characters
- The first tweet should hook the reader
- Each subsequent tweet should add value
- The last tweet should have a takeaway or call to thought
- Sound natural, not like AI-generated content
- Only the last tweet should have hashtags (max {style.get('max_hashtags', 2)})
</rules>
{recent_context}

Output each tweet on a separate line, separated by "---" on its own line.
No quotes, no numbering, no explanation."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        tweets = [t.strip() for t in raw.split("---") if t.strip()]

        # 文字数チェック
        tweets = [
            self._trim_tweet(t, style["max_characters"])
            if len(t) > style["max_characters"] else t
            for t in tweets
        ]

        return {
            "text": tweets[0] if tweets else "",
            "category": category["topic"],
            "is_thread": True,
            "thread_texts": tweets,
        }

    def _trim_tweet(self, text: str, max_chars: int) -> str:
        """ツイートを文字数制限内にトリム"""
        if len(text) <= max_chars:
            return text

        # ハッシュタグを分離
        parts = text.rsplit("#", 1)
        if len(parts) == 2 and len(parts[0].strip()) > 0:
            main_text = parts[0].strip()
            if len(main_text) <= max_chars:
                return main_text

        # 最後の文で切る
        for sep in ["。", ". ", "! ", "？", "? "]:
            idx = text[:max_chars].rfind(sep)
            if idx > 0:
                return text[:idx + len(sep)].strip()

        # それでもダメなら強制カット
        return text[:max_chars - 1] + "…"
