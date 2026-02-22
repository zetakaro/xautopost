# CLAUDE.md

## プロジェクト概要
X（Twitter）の2アカウント自動投稿ツール。
- アカウント1: 英語（US Eastern時間帯 8:00-22:00）
- アカウント2: 日本語（JST 7:00-23:00）
- 各アカウント1日3〜5回、コアタイム内にランダム投稿
- Claude APIでツイート文面を自動生成（重複防止機能あり）
- 10%の確率でスレッド投稿（2〜4ツイート）

## 技術スタック
- Python 3.11+
- tweepy 4.14 … X API v2 投稿
- anthropic SDK … ツイート文面生成（Claude Sonnet使用）
- pyyaml … 設定ファイル管理
- python-dotenv … 環境変数
- schedule / zoneinfo … スケジュール管理・タイムゾーン処理

## ファイル構成
```
x-auto-poster/
├── config/
│   ├── accounts.yaml.example  # 設定テンプレート（APIキー・ペルソナ・スケジュール）
│   └── accounts.yaml          # 実設定（git管理外）
├── src/
│   ├── tweet_generator.py     # Claude APIでツイート生成（重複チェック込み）
│   ├── scheduler.py           # コアタイム内ランダムスケジュール生成
│   ├── publisher.py           # X API投稿（リトライ・スレッド対応）
│   └── logger.py              # ログ管理・投稿履歴（JSON）
├── logs/                      # 投稿ログ・履歴ファイル
├── systemd/                   # VPS用systemdサービス定義
├── main.py                    # エントリーポイント（CLI）
├── requirements.txt
├── .env                       # Anthropic APIキー（git管理外）
└── .env.example
```

## 主要コマンド
```bash
# 環境構築
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 実行
python main.py --dry-run    # 投稿せず生成結果のみ表示
python main.py --once       # 全アカウントに1回ずつ投稿
python main.py --verify     # API認証チェックのみ
python main.py --status     # 直近の投稿履歴表示
python main.py              # スケジューラー常駐起動
```

## 設定ファイル
- `config/accounts.yaml` … 各アカウントのAPIキー、ペルソナ、カテゴリ（weight付き）、投稿スケジュール
- `.env` … ANTHROPIC_API_KEY、LOG_LEVEL、DRY_RUN

## 設計上の重要ポイント
- `persona` と `categories` の記述がツイート品質を決める最重要設定
- 投稿間隔は最低2時間（min_interval_hours）でbot検出を回避
- 秒単位もランダム化してパターン検出を防止
- 直近15件の投稿をClaude APIプロンプトに含めて内容重複を防止
- publisher.pyはリトライ（指数バックオフ、最大3回）対応
- 投稿履歴はlogs/post_history.jsonに保存（直近500件保持）

## 拡張する場合の方針
- 画像付き投稿 → tweepy v2のmedia_upload + publisher.pyに追加
- エンゲージメント分析 → src/analytics.py を新設
- 投稿テーマ自動調整 → 反応データをtweet_generator.pyのプロンプトに反映
- Webhook通知 → 投稿成功/失敗時にSlack/Discord通知

## 注意事項
- accounts.yamlと.envは絶対にgitにコミットしない（.gitignoreに登録済み）
- X API Free Planは月1,500ツイート（2アカウント×5回×30日=300回で十分収まる）
- Anthropic APIコストはSonnet利用で月数ドル程度

## デプロイ先
- カゴヤ・ジャパン KAGOYA CLOUD VPS（Ubuntu Server 24.04）
- 詳細手順: DEPLOY_KAGOYA.md を参照
- systemdサービスのユーザーは `xposter`
