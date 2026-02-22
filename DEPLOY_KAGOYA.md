# カゴヤVPS デプロイ手順書

## 本書について
X自動投稿ツール「x-auto-poster」をカゴヤ・ジャパン KAGOYA CLOUD VPS にデプロイするための手順書です。
Claude Codeまたは手動でのセットアップに対応しています。

---

## 1. カゴヤVPS インスタンス作成

### 1.1 推奨プラン

| 項目 | 推奨 |
|------|------|
| プラン | 1コア / 1GB / 100GB NVMe SSD（最小プラン） |
| OS | Ubuntu Server 24.04 |
| 料金 | 月額550円（日額20円） / 年額506円相当 |

※ 本ツールはCPU・メモリをほぼ消費しない軽量プロセスのため、最小プランで十分です。

### 1.2 インスタンス作成手順

1. **カゴヤアカウント作成**
   - https://www.kagoya.jp/vps/ にアクセス
   - 「お申し込み」からアカウントを作成

2. **ログイン用認証キーの作成**
   - コントロールパネルにログイン
   - 「セキュリティ」→「ログイン用認証キー」→「認証キーの作成」
   - キー名を入力（例: `xposter-key`）
   - **秘密鍵ファイル（.key）がダウンロードされるので必ず保存する**
   - ⚠️ この秘密鍵は再ダウンロードできないため、安全な場所に保管すること

3. **インスタンスの作成**
   - コントロールパネル →「インスタンス」→「インスタンス作成」
   - OS: **Ubuntu Server 24.04**
   - スペック: **1コア / 1GB**
   - 認証キー: 先ほど作成したキーを選択
   - 「インスタンス作成」をクリック

4. **IPアドレスの確認**
   - インスタンス一覧でIPアドレスを確認・メモする

---

## 2. SSH接続

### 2.1 カゴヤVPSの特徴

カゴヤVPSでは、初期状態で以下のセキュリティ設定が適用されています：
- rootアカウントのログインは **公開鍵認証のみ**（パスワード認証は無効）
- SSHポートは **22番**（デフォルト）

### 2.2 Mac / Linux からの接続

```bash
# 秘密鍵のパーミッションを設定（初回のみ）
chmod 400 ~/Downloads/xposter-key.key

# SSH接続
ssh -i ~/Downloads/xposter-key.key root@<IPアドレス>
```

### 2.3 Windows からの接続（TeraTerm）

1. TeraTerm を起動
2. ホスト: インスタンスのIPアドレス
3. TCPポート: 22
4. SSH認証画面で：
   - ユーザー名: `root`
   - 「RSA/DSA/ECDSA/ED25519鍵を使う」にチェック
   - 秘密鍵: ダウンロードした `.key` ファイルを選択
5. 「OK」で接続

### 2.4 Windows からの接続（PuTTY）

PuTTYは `.key` 形式を直接使用できないため、PuTTYgenで変換が必要です：

1. PuTTYgen を起動
2. 「Load」→ ファイルフィルタを「All Files」にして `.key` ファイルを開く
3. 「Save private key」で `.ppk` 形式で保存
4. PuTTY の設定：
   - Session → Host Name: IPアドレス、Port: 22
   - Connection → SSH → Auth → Private key file: 変換した `.ppk` を指定
   - 「Open」で接続、ユーザー名 `root` でログイン

---

## 3. サーバー初期設定

SSH接続後、以下のコマンドを順番に実行します。

### 3.1 システム更新

```bash
apt update && apt upgrade -y
```

### 3.2 作業ユーザーの作成

rootで直接運用せず、専用ユーザーを作成します。

```bash
# ユーザー作成
adduser xposter
# パスワードを設定（その他の項目はEnterでスキップ）

# sudo権限付与
usermod -aG sudo xposter

# SSH公開鍵をコピー（rootの鍵をそのまま利用）
mkdir -p /home/xposter/.ssh
cp /root/.ssh/authorized_keys /home/xposter/.ssh/
chown -R xposter:xposter /home/xposter/.ssh
chmod 700 /home/xposter/.ssh
chmod 600 /home/xposter/.ssh/authorized_keys
```

### 3.3 SSHセキュリティ強化（推奨）

```bash
# SSH設定ファイルを編集
nano /etc/ssh/sshd_config
```

以下を変更・確認：
```
# rootログインを禁止（xposterユーザーでログインしてsudoを使う）
PermitRootLogin no

# パスワード認証は無効のまま
PasswordAuthentication no

# ポート変更（任意。変更する場合は50000番台を推奨）
# Port 50022
```

```bash
# SSH再起動
systemctl restart sshd
```

⚠️ **ポートを変更した場合は、変更後のポートで接続できることを確認してから既存セッションを閉じてください。**

### 3.4 ファイアウォール設定（UFW）

```bash
# UFWの初期設定
ufw default deny incoming
ufw default allow outgoing

# SSH接続を許可（ポート変更した場合はそのポート番号に変更）
ufw allow 22/tcp

# UFW有効化
ufw enable

# 状態確認
ufw status
```

### 3.5 Python環境の確認

Ubuntu 24.04にはPython 3.12がプリインストールされています。

```bash
# バージョン確認
python3 --version

# pipとvenvのインストール
apt install -y python3-pip python3-venv git
```

---

## 4. アプリケーションのデプロイ

**ここからはxposterユーザーで作業します。**

```bash
# xposterユーザーに切り替え
su - xposter
```

### 4.1 プロジェクトファイルの配置

**方法A: ローカルPCからSCPでアップロード**

```bash
# ローカルPCから実行
scp -i ~/Downloads/xposter-key.key x-auto-poster.zip xposter@<IPアドレス>:~/
```

VPS側で解凍：
```bash
cd ~
unzip x-auto-poster.zip
cd x-auto-poster
```

**方法B: Gitリポジトリからクローン（GitHubに置いている場合）**

```bash
cd ~
git clone <repository_url> x-auto-poster
cd x-auto-poster
```

**方法C: カゴヤのClaude Codeテンプレートを使う場合**

カゴヤVPSではClaude Code用テンプレートが提供されています。
別途Claude Codeテンプレートでインスタンスを立てるか、
既存のUbuntuインスタンスにClaude Codeをインストールして
VPS上で直接開発・デプロイすることも可能です。

### 4.2 Python仮想環境セットアップ

```bash
cd ~/x-auto-poster

# 仮想環境作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# パッケージインストール
pip install -r requirements.txt
```

### 4.3 設定ファイルの準備

```bash
# アカウント設定ファイルを作成
cp config/accounts.yaml.example config/accounts.yaml

# 環境変数ファイルを作成
cp .env.example .env
```

**accounts.yaml を編集（APIキーとペルソナを設定）：**

```bash
nano config/accounts.yaml
```

設定する項目：
- 英語アカウント: `api_key`, `api_secret`, `access_token`, `access_token_secret`
- 日本語アカウント: 同上
- 各アカウントの `persona`（ツイートの人格設定）
- 各アカウントの `categories`（投稿カテゴリと重み）

**.env を編集（Anthropic APIキーを設定）：**

```bash
nano .env
```

```
ANTHROPIC_API_KEY=sk-ant-ここに実際のAPIキーを入力
LOG_LEVEL=INFO
DRY_RUN=false
```

### 4.4 動作確認

```bash
# 仮想環境が有効か確認
source ~/x-auto-poster/venv/bin/activate

# API認証チェック
python main.py --verify

# ドライラン（投稿せずに生成テスト）
python main.py --dry-run

# 1回投稿テスト（実際にツイートされる）
python main.py --once
```

すべて正常に動作することを確認してから、次のステップへ進みます。

---

## 5. systemdサービス登録（常駐化）

### 5.1 サービスファイルの配置

```bash
# rootに切り替え
sudo su -

# サービスファイルをコピー
cp /home/xposter/x-auto-poster/systemd/x-auto-poster.service /etc/systemd/system/

# サービスファイルを編集（パスとユーザーを合わせる）
nano /etc/systemd/system/x-auto-poster.service
```

以下の内容に編集：

```ini
[Unit]
Description=X Auto Poster - 自動ツイート投稿サービス
After=network.target

[Service]
Type=simple
User=xposter
WorkingDirectory=/home/xposter/x-auto-poster
ExecStart=/home/xposter/x-auto-poster/venv/bin/python main.py
Restart=always
RestartSec=30
EnvironmentFile=/home/xposter/x-auto-poster/.env

# ログ出力をjournalに統合
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 5.2 サービスの起動

```bash
# systemdにサービスを認識させる
systemctl daemon-reload

# 自動起動を有効化（VPS再起動時も自動で立ち上がる）
systemctl enable x-auto-poster

# サービスを起動
systemctl start x-auto-poster

# 起動確認
systemctl status x-auto-poster
```

正常に動作している場合、以下のような出力が表示されます：

```
● x-auto-poster.service - X Auto Poster - 自動ツイート投稿サービス
     Loaded: loaded (/etc/systemd/system/x-auto-poster.service; enabled)
     Active: active (running) since ...
```

---

## 6. 運用・監視

### 6.1 日常の確認コマンド

```bash
# サービスの状態確認
sudo systemctl status x-auto-poster

# リアルタイムログ表示（systemd経由）
sudo journalctl -u x-auto-poster -f

# アプリケーションログの確認
tail -f /home/xposter/x-auto-poster/logs/app_*.log

# 投稿履歴の確認
cd /home/xposter/x-auto-poster
source venv/bin/activate
python main.py --status
```

### 6.2 サービス操作

```bash
# 停止
sudo systemctl stop x-auto-poster

# 再起動
sudo systemctl restart x-auto-poster

# 起動
sudo systemctl start x-auto-poster
```

### 6.3 設定変更時の手順

```bash
# 1. サービスを停止
sudo systemctl stop x-auto-poster

# 2. 設定ファイルを編集
nano /home/xposter/x-auto-poster/config/accounts.yaml

# 3. ドライランで確認
cd /home/xposter/x-auto-poster
source venv/bin/activate
python main.py --dry-run

# 4. サービスを再起動
sudo systemctl start x-auto-poster
```

### 6.4 ソースコード更新時の手順

```bash
# 1. サービスを停止
sudo systemctl stop x-auto-poster

# 2. ファイルを更新（Git利用の場合）
cd /home/xposter/x-auto-poster
git pull

# 3. パッケージ更新（requirements.txtが変わった場合）
source venv/bin/activate
pip install -r requirements.txt

# 4. サービスを再起動
sudo systemctl start x-auto-poster
```

---

## 7. トラブルシューティング

### 7.1 SSH接続できない

| 症状 | 対処 |
|------|------|
| Connection refused | インスタンスが起動中か確認。コントロールパネルで「起動」する |
| Permission denied | 秘密鍵ファイルのパスとパーミッション（chmod 400）を確認 |
| ポート変更後に接続できない | コントロールパネルの「コンソール」からブラウザ経由でログインし、UFW設定を確認 |

### 7.2 サービスが起動しない

```bash
# エラー詳細を確認
sudo journalctl -u x-auto-poster -n 50 --no-pager

# よくある原因
# - .envファイルのパスが間違っている
# - Pythonパスが間違っている（ExecStartの確認）
# - accounts.yamlが存在しない
# - APIキーが無効
```

### 7.3 ツイートが投稿されない

```bash
# ログでエラーを確認
tail -100 /home/xposter/x-auto-poster/logs/app_*.log | grep -i error

# よくある原因
# - X APIの認証情報が間違っている → python main.py --verify で確認
# - X APIのアプリ権限が Read Only になっている → Read and Write に変更
# - レート制限に達している → ログに "レート制限" と表示される
# - Anthropic APIキーが無効 → .env を確認
```

### 7.4 インスタンス再起動後の確認

カゴヤVPSのインスタンスを再起動した場合、systemdで `enable` 設定していれば
x-auto-posterは自動的に再起動されます。

```bash
# 再起動後の確認
sudo systemctl status x-auto-poster
```

---

## 8. コスト一覧

| 項目 | 月額目安 |
|------|---------|
| カゴヤVPS（1コア/1GB、月額） | 550円 |
| カゴヤVPS（1コア/1GB、年額換算） | 506円 |
| Anthropic API（Claude Sonnet） | 200〜500円（$1〜3） |
| X API（Free Plan） | 0円 |
| **合計** | **約750〜1,050円/月** |

※ X API Free Planは月1,500ツイートまで。2アカウント×5回×30日＝300回なので十分収まります。
※ Anthropic APIは1ツイート生成あたり約$0.003〜0.005。月300回で約$1〜1.5。

---

## 9. チェックリスト

### インスタンス作成
- [ ] カゴヤアカウント作成済み
- [ ] 認証キー（秘密鍵）をダウンロード・保管済み
- [ ] Ubuntu Server 24.04 でインスタンス作成済み
- [ ] IPアドレスをメモ済み

### サーバー初期設定
- [ ] SSH接続確認済み
- [ ] apt update && upgrade 実行済み
- [ ] xposter ユーザー作成済み
- [ ] UFW（ファイアウォール）設定済み
- [ ] Python 3, pip, venv インストール済み

### アプリケーション
- [ ] プロジェクトファイル配置済み
- [ ] venv作成・パッケージインストール済み
- [ ] config/accounts.yaml にAPIキー設定済み
- [ ] .env にAnthropic APIキー設定済み
- [ ] `python main.py --verify` 認証OK
- [ ] `python main.py --dry-run` 正常動作
- [ ] `python main.py --once` 実投稿テストOK

### 常駐化
- [ ] systemdサービスファイル配置済み
- [ ] `systemctl enable` で自動起動設定済み
- [ ] `systemctl start` でサービス起動済み
- [ ] `systemctl status` で active (running) 確認済み
