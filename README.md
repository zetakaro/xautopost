# X Auto Poster - 多アカウント自動投稿ツール

## 概要
2つのXアカウント（英語・日本語）に対して、Claude APIで生成したツイートを自動投稿するツールです。

## 構成
- **アカウント1（英語）**: 米国コアタイム（EST 8:00-22:00）にランダム投稿
- **アカウント2（日本語）**: 日本コアタイム（JST 7:00-23:00）にランダム投稿
- **投稿頻度**: 各アカウント1日3〜5回

## セットアップ

### 1. 必要なAPIキーを取得

#### X (Twitter) API
1. https://developer.x.com/ でDeveloper Accountを作成
2. 各アカウントごとにAppを作成し、以下を取得:
   - API Key (Consumer Key)
   - API Secret (Consumer Secret)
   - Access Token
   - Access Token Secret
3. アプリの権限を **Read and Write** に設定

#### Anthropic API
1. https://console.anthropic.com/ でAPIキーを取得

### 2. 環境構築

```bash
cd x-auto-poster
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 設定ファイルの編集

`config/accounts.yaml` を編集してAPIキーとツイートテーマを設定:

```bash
cp config/accounts.yaml.example config/accounts.yaml
# accounts.yaml を編集（APIキーを入力）
```

`.env` ファイルを作成:
```bash
cp .env.example .env
# .env を編集（Anthropic APIキーを入力）
```

### 4. テスト実行

```bash
# ドライラン（実際には投稿しない）
python main.py --dry-run

# 1回だけ投稿テスト
python main.py --once

# スケジューラー起動（常駐）
python main.py
```

### 5. 本番運用（VPS等）

```bash
# screenやtmuxで常駐
screen -S xposter
python main.py

# またはsystemdサービスとして登録
sudo cp systemd/x-auto-poster.service /etc/systemd/system/
sudo systemctl enable x-auto-poster
sudo systemctl start x-auto-poster
```

## ファイル構成
```
x-auto-poster/
├── config/
│   ├── accounts.yaml.example  # アカウント設定テンプレート
│   └── accounts.yaml          # 実際の設定（git管理外）
├── src/
│   ├── tweet_generator.py     # Claude APIでツイート生成
│   ├── scheduler.py           # スケジュール管理
│   ├── publisher.py           # X APIで投稿
│   └── logger.py              # ログ管理
├── logs/                      # 投稿ログ
├── main.py                    # エントリーポイント
├── requirements.txt
├── .env.example
└── README.md
```

## 投稿ルール
- 同一内容の重複投稿禁止（履歴チェック機能あり）
- 各アカウントのテーマに沿った内容のみ生成
- 投稿間隔は最低2時間空ける
- エラー時はリトライ（最大3回、指数バックオフ）

## 注意事項
- X APIの利用規約を遵守してください
- Free Planは月1,500ツイート（2アカウント×5回×30日=300回なので十分）
- APIキーは絶対にGitにコミットしないでください
