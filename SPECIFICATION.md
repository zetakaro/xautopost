# X自動投稿ツール 開発仕様書

## 1. プロジェクト概要

### 1.1 目的
X（旧Twitter）の2つのアカウントに対し、AIで生成したツイートを自動投稿するシステムを構築する。VPS上で常駐稼働させ、完全自動運用を実現する。

### 1.2 アカウント構成

| 項目 | アカウント1 | アカウント2 |
|------|-----------|-----------|
| 言語 | 英語 | 日本語 |
| ターゲット | 米国・グローバル | 日本 |
| タイムゾーン | US/Eastern (EST/EDT) | Asia/Tokyo (JST) |
| コアタイム | 8:00〜22:00 EST | 7:00〜23:00 JST |
| 投稿頻度 | 1日3〜5回 | 1日3〜5回 |

### 1.3 システム全体像

```
[VPS (Ubuntu)]
  └── x-auto-poster (Python常駐プロセス)
        ├── スケジューラー（コアタイム内でランダム時刻生成）
        ├── ツイート生成（Anthropic Claude API）
        ├── 投稿実行（X API v2 / tweepy）
        ├── 投稿履歴管理（JSON）
        └── ログ管理
```

---

## 2. 機能要件

### 2.1 ツイート生成機能

- Anthropic Claude API（Claude Sonnet）を使用してツイート文面を自動生成する
- 各アカウントに「ペルソナ」と「カテゴリ（重み付き）」を設定ファイルで定義する
- カテゴリは重み付きランダムで選択する
- 直近15件の投稿履歴をプロンプトに含め、内容の重複を防止する
- 1ツイートは280文字以内を厳守する
- 10%の確率でスレッド投稿（2〜4ツイート）を生成する
- ハッシュタグは各ツイート最大2個まで
- 絵文字は使用しない

### 2.2 スケジュール管理機能

- 毎日0時（各アカウントのローカルタイム）にその日の投稿スケジュールを生成する
- コアタイム内にランダムな時刻を3〜5個生成する
- 投稿間隔は最低2時間空ける
- 秒単位もランダムにし、bot感を軽減する
- 投稿数は設定値の±1でランダムに変動させる（例：設定4なら3〜5）

### 2.3 投稿実行機能

- X API v2をtweepyライブラリ経由で使用する
- 単発ツイートとスレッド投稿の両方に対応する
- スレッド投稿はリプライチェーンで連結する
- エラー時は指数バックオフで最大3回リトライする
- レート制限（429）時は自動で待機して再試行する
- 投稿成功/失敗をログに記録する

### 2.4 投稿履歴管理

- 投稿履歴をJSON形式で保存する（logs/post_history.json）
- 直近500件を保持し、古い履歴は自動削除する
- 記録内容：アカウントID、ツイート本文、ツイートID、カテゴリ、タイムスタンプ

### 2.5 ログ管理

- コンソール出力とファイル出力の両方に対応する
- 日付ごとにログファイルをローテーションする（logs/app_YYYYMMDD.log）
- ログレベルは環境変数で設定可能（DEBUG/INFO/WARNING/ERROR）

---

## 3. 非機能要件

### 3.1 実行環境

- OS: Ubuntu 22.04 LTS または 24.04 LTS（VPS）
- Python: 3.11以上
- 常駐プロセスとしてsystemdサービスで管理する
- 異常終了時は30秒後に自動再起動する

### 3.2 セキュリティ

- APIキーは.envファイルおよびconfig/accounts.yamlで管理する
- 両ファイルは.gitignoreに登録し、Gitリポジトリにコミットしない
- exampleファイル（.env.example、accounts.yaml.example）のみGit管理する

### 3.3 コスト想定

- X API: Free Plan（月1,500ツイート）で運用可能（2アカウント×5回×30日＝300回）
- Anthropic API: Claude Sonnet使用で月数ドル程度
- VPS: 月500〜700円程度（ConoHa VPS等の最小プラン）

---

## 4. 技術スタック

### 4.1 使用ライブラリ

```
tweepy==4.14.0          # X API v2クライアント
anthropic==0.42.0       # Claude APIクライアント
pyyaml==6.0.2           # 設定ファイル読み込み
python-dotenv==1.0.1    # 環境変数管理
schedule==1.2.2         # タスクスケジューリング
pytz==2024.2            # タイムゾーン処理
```

### 4.2 使用API

| API | 用途 | 認証方式 |
|-----|------|---------|
| X API v2 | ツイート投稿 | OAuth 1.0a（各アカウント4キー） |
| Anthropic Messages API | ツイート文面生成 | APIキー |

---

## 5. ファイル構成

```
x-auto-poster/
├── CLAUDE.md                      # Claude Code用プロジェクト説明
├── README.md                      # セットアップ手順
├── requirements.txt               # Pythonパッケージ一覧
├── .env.example                   # 環境変数テンプレート
├── .env                           # 実環境変数（git管理外）
├── .gitignore
├── main.py                        # エントリーポイント（CLI）
├── config/
│   ├── accounts.yaml.example      # アカウント設定テンプレート
│   └── accounts.yaml              # 実設定（git管理外）
├── src/
│   ├── __init__.py
│   ├── tweet_generator.py         # ツイート生成（Claude API）
│   ├── scheduler.py               # スケジュール管理
│   ├── publisher.py               # X API投稿
│   └── logger.py                  # ログ・履歴管理
├── logs/                          # ログ出力先
│   └── .gitkeep
└── systemd/
    └── x-auto-poster.service      # systemdサービス定義
```

---

## 6. 設定ファイル仕様

### 6.1 .env

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
LOG_LEVEL=INFO
DRY_RUN=false
```

### 6.2 config/accounts.yaml

各アカウントに以下を定義する：

```yaml
accounts:
  <account_id>:
    name: "表示名"
    language: "en" または "ja"

    # X API認証（4つのキー）
    api_key: "..."
    api_secret: "..."
    access_token: "..."
    access_token_secret: "..."

    # スケジュール設定
    schedule:
      posts_per_day: 4          # 基準投稿数（±1でランダム変動）
      timezone: "US/Eastern"    # タイムゾーン
      core_hours_start: 8       # コアタイム開始（時）
      core_hours_end: 22        # コアタイム終了（時）
      min_interval_hours: 2     # 最低投稿間隔（時間）

    # コンテンツ設定
    content:
      persona: |
        （ペルソナ記述）
      categories:
        - topic: "カテゴリ名"
          weight: 30             # 選択重み（合計100推奨）
          description: "説明"
      style:
        max_characters: 280
        use_hashtags: true
        max_hashtags: 2
        use_emojis: false
        thread_probability: 0.1  # スレッド投稿確率
```

### 6.3 英語アカウントのデフォルトペルソナ

```
You are a tech entrepreneur sharing insights about AI,
automation, and the future of work. Your tone is thoughtful,
practical, and slightly contrarian. You share real experiences
and actionable advice, not hype.
```

カテゴリ：
- AI automation tips（30%）
- Future of work insights（25%）
- Productivity hacks（20%）
- Industry trends（15%）
- Motivational / Mindset（10%）

### 6.4 日本語アカウントのデフォルトペルソナ

```
あなたはDX推進・業務改善の専門家です。電力小売業界での実務経験を持ち、
AI活用・業務自動化・チームマネジメントについて発信しています。
トーンは実践的で、現場目線。理論だけでなく「明日から使える」情報を重視します。
```

カテゴリ：
- AI・DX活用術（30%）
- マネジメント・リーダーシップ（25%）
- 業務改善・効率化（20%）
- 業界トレンド（15%）
- 自己啓発・学び（10%）

---

## 7. CLIインターフェース

main.pyは以下のコマンドラインオプションを提供する：

```bash
python main.py                # スケジューラー常駐起動（デフォルト）
python main.py --dry-run      # 投稿せず生成結果のみ表示
python main.py --once         # 全アカウントに1回ずつ投稿して終了
python main.py --verify       # API認証チェックのみ
python main.py --status       # 直近の投稿履歴を表示
```

---

## 8. 各モジュール詳細仕様

### 8.1 tweet_generator.py

**クラス: TweetGenerator**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| __init__ | api_key: str | - | Anthropicクライアント初期化 |
| generate | account_id, config | dict | ツイート生成（下記参照） |

generate()の戻り値：
```python
{
    "text": str,           # ツイート本文
    "category": str,       # 選択されたカテゴリ名
    "is_thread": bool,     # スレッドかどうか
    "thread_texts": list   # スレッドの場合の全ツイートリスト
}
```

**生成プロンプト要件：**
- ペルソナとカテゴリをプロンプトに含める
- 直近15件の投稿履歴を含めて重複防止する
- 「AIっぽくない」「企業アカウントっぽくない」自然な文体を指示する
- 文頭の定型表現（"Just"等）を禁止する
- 文字数超過時はトリム処理する（句点で切り、最終手段で「…」付加）

### 8.2 scheduler.py

**クラス: PostScheduler**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| generate_daily_schedule | account_id, schedule_config | list[datetime] | 1日分のスケジュール生成 |
| should_post_now | account_id, timezone, tolerance_seconds=120 | bool | 今投稿すべきか判定 |
| get_next_post_time | account_id, timezone | datetime or None | 次の投稿時刻 |
| is_schedule_done | account_id | bool | 本日のスケジュール完了判定 |
| get_status | - | dict | 全アカウントの状況 |

**スケジュール生成ロジック：**
1. コアタイムの分単位リストを作成
2. ランダムに1つ選択
3. その前後min_interval_hours分を候補から除外
4. posts_per_day回繰り返す
5. 時刻順にソート

### 8.3 publisher.py

**クラス: Publisher**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| __init__ | api_key, api_secret, access_token, access_token_secret | - | tweepyクライアント初期化 |
| post_tweet | text, reply_to=None, max_retries=3 | dict or None | ツイート投稿 |
| post_thread | tweets: list[str] | list[dict] | スレッド投稿 |
| verify_credentials | - | bool | 認証確認 |

**エラーハンドリング：**
- TooManyRequests（429）: 指数バックオフ（60秒×2^attempt）で待機
- TwitterServerError（5xx）: 指数バックオフ（30秒×2^attempt）で待機
- Forbidden（403）: 権限エラーとしてログ出力、リトライしない
- その他: ログ出力後リトライ

### 8.4 logger.py

**クラス: PostHistory**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| add | account_id, tweet_text, tweet_id, category | - | 履歴追加 |
| get_recent | account_id, count=20 | list | 直近の投稿取得 |
| get_recent_texts | account_id, count=20 | list[str] | 直近の投稿テキスト取得 |
| get_last_post_time | account_id | datetime or None | 最終投稿時刻取得 |

---

## 9. メインループ仕様

### 9.1 スケジューラーモード（デフォルト）

```
1. 起動時に全アカウントの当日スケジュールを生成
2. 30秒ごとにループ：
   a. 日付が変わっていたらスケジュール再生成
   b. 各アカウントについて should_post_now() をチェック
   c. 投稿時刻なら：
      - ツイート生成
      - 投稿実行
      - 履歴記録
      - ログ出力
3. Ctrl+Cで安全に停止
```

### 9.2 ドライランモード

- ツイート生成は実行するが、X APIへの投稿をスキップする
- 生成結果をログに出力する
- 履歴には"dry-run"としてツイートIDを記録する

---

## 10. VPSデプロイ手順

### デプロイ先: カゴヤ・ジャパン KAGOYA CLOUD VPS

詳細な手順は **DEPLOY_KAGOYA.md** を参照してください。
以下は概要のみ記載します。

### 10.1 前提条件

- カゴヤ KAGOYA CLOUD VPS（1コア/1GB/100GBプラン、月額550円）
- OS: Ubuntu Server 24.04
- SSH公開鍵認証によるアクセス
- Python 3.11以上（Ubuntu 24.04は3.12プリインストール済み）

### 10.2 セットアップ手順

```bash
# 1. プロジェクト配置
cd ~
git clone <repository_url> x-auto-poster  # またはZIPをアップロード・解凍
cd x-auto-poster

# 2. Python仮想環境セットアップ
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 設定ファイル準備
cp config/accounts.yaml.example config/accounts.yaml
cp .env.example .env
# 各ファイルにAPIキーを入力（nano、vim等で編集）

# 4. 動作確認
python main.py --verify       # API認証チェック
python main.py --dry-run      # ドライラン確認

# 5. systemdサービス登録
sudo cp systemd/x-auto-poster.service /etc/systemd/system/
# service内のUser、WorkingDirectory、ExecStartのパスを環境に合わせて修正
sudo systemctl daemon-reload
sudo systemctl enable x-auto-poster
sudo systemctl start x-auto-poster

# 6. 稼働確認
sudo systemctl status x-auto-poster
tail -f logs/app_*.log
```

### 10.3 systemdサービス定義

```ini
[Unit]
Description=X Auto Poster - 自動ツイート投稿サービス
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/x-auto-poster
ExecStart=/home/ubuntu/x-auto-poster/venv/bin/python main.py
Restart=always
RestartSec=30
EnvironmentFile=/home/ubuntu/x-auto-poster/.env

[Install]
WantedBy=multi-user.target
```

### 10.4 運用コマンド

```bash
# サービス管理
sudo systemctl start x-auto-poster    # 起動
sudo systemctl stop x-auto-poster     # 停止
sudo systemctl restart x-auto-poster  # 再起動
sudo systemctl status x-auto-poster   # 状態確認

# ログ確認
journalctl -u x-auto-poster -f        # systemdログ
tail -f ~/x-auto-poster/logs/app_*.log # アプリログ

# 投稿履歴確認
cd ~/x-auto-poster
source venv/bin/activate
python main.py --status
```

---

## 11. X APIポリシー遵守事項

- 各アカウントは明確に異なるテーマ・言語で運用する（英語/日本語で分離）
- 同一・類似コンテンツの複数アカウント投稿は行わない
- 自動いいね・フォロー・リツイートは実装しない
- 投稿頻度は控えめに設定する（1日3〜5回）
- 投稿間隔を2時間以上空けてスパム判定を回避する
- 各アカウントのApp権限はRead and Writeのみに設定する

---

## 12. 将来の拡張候補（本仕様の対象外）

以下は初期リリースには含めないが、将来追加を検討する機能：

1. **画像付き投稿** — tweepy v2のmedia_upload対応
2. **エンゲージメント分析** — いいね・RT・インプレッション数を取得し投稿戦略を最適化
3. **投稿テーマ自動調整** — エンゲージメントデータを基にカテゴリの重みを自動調整
4. **Webhook通知** — 投稿成功/失敗時にSlackやDiscordへ通知
5. **Web管理画面** — 設定変更・履歴確認・手動投稿をブラウザから操作
6. **アカウント追加** — 3つ目以降のアカウント対応（設定ファイル追記のみで対応可能な設計）

---

## 13. 成果物チェックリスト

Claude Codeでの実装完了時に以下を確認すること：

- [ ] 全ソースコードが作成されている
- [ ] `python main.py --dry-run` でエラーなく実行できる
- [ ] `python main.py --verify` でAPI認証が通る
- [ ] `python main.py --once` で実際に投稿される
- [ ] 英語アカウントが英語でツイートを生成する
- [ ] 日本語アカウントが日本語でツイートを生成する
- [ ] 投稿履歴がlogs/post_history.jsonに記録される
- [ ] スケジューラーモードが常駐で動作する
- [ ] systemdサービスファイルが正しく記述されている
- [ ] .gitignoreで秘密情報が除外されている
- [ ] README.mdにセットアップ手順が記載されている
- [ ] CLAUDE.mdにプロジェクト概要が記載されている
