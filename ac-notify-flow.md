# AtCoder AC通知システム 実装フロー

Slack チャンネル `#z-atcoder` のメンバーが AtCoder で AC したとき、  
「〇〇がACしました」という通知を GitHub Actions で自動送信する仕組みの設計。

---

## 全体構成

```
AtCoder Problems API
        ↓ (定期ポーリング)
GitHub Actions (cron)
        ↓ (新規AC検出)
Slack Incoming Webhook
        ↓
#z-atcoder チャンネルに通知
```

---

## ディレクトリ構成

```
.
├── .github/
│   └── workflows/
│       └── ac-notify.yml        # GitHub Actions ワークフロー
├── scripts/
│   └── check_ac.py              # AC検出 & Slack通知スクリプト
├── data/
│   └── members.yml              # メンバー設定ファイル（AtCoder ID ↔ 表示名）
│   └── last_submission_ids.json # 最後に通知した提出IDを記録（状態管理）
└── README.md
```

---

## Step 1: メンバー設定ファイルの作成

`data/members.yml` に、Slack チャンネルメンバーの AtCoder ユーザー名と表示名を記載する。

```yaml
members:
  - atcoder_id: "user_alice"
    display_name: "Alice"
  - atcoder_id: "user_bob"
    display_name: "Bob"
  - atcoder_id: "user_charlie"
    display_name: "Charlie"
```

> メンバーの追加・削除はこのファイルを編集するだけでOK。

---

## Step 2: AC検出スクリプトの作成

`scripts/check_ac.py` で以下の処理を行う。

### 使用API

[AtCoder Problems API](https://github.com/kenkoooo/AtCoderProblems/blob/master/doc/api.md) のユーザー提出履歴エンドポイントを利用する（非公式・無料）。

```
GET https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions
    ?user={atcoder_id}
    &from_second={unix_timestamp}
```

### スクリプトの処理フロー

```
1. data/members.yml を読み込む
2. data/last_submission_ids.json を読み込む（初回は空）
3. 各メンバーについて:
   a. AtCoder Problems API に直近の提出履歴をリクエスト
   b. result == "AC" の提出を抽出
   c. 前回通知済みのIDより新しいものだけを選別
   d. 新規ACがあれば Slack Webhook に POST
      → メッセージ例: "Alice が A - Beginner Contest 123 を AC しました！ 🎉"
4. data/last_submission_ids.json を最新の提出IDで更新
5. 更新したファイルを git commit & push（状態を永続化）
```

### Slack 通知メッセージ例

```json
{
  "text": ":tada: *Alice* が <https://atcoder.jp/contests/abc123/tasks/abc123_a|ABC123 - A問題> を AC しました！"
}
```

---

## Step 3: Slack Incoming Webhook の設定

1. [Slack API](https://api.slack.com/apps) にアクセスし、新しいアプリを作成
2. **Incoming Webhooks** を有効化
3. `#z-atcoder` チャンネル向けの Webhook URL を生成
4. 生成した URL を GitHub リポジトリの **Secrets** に登録

```
Settings → Secrets and variables → Actions → New repository secret
  Name  : SLACK_WEBHOOK_URL
  Value : https://hooks.slack.com/services/XXXXX/YYYYY/ZZZZZ
```

---

## Step 4: GitHub Actions ワークフローの作成

`.github/workflows/ac-notify.yml`

```yaml
name: AtCoder AC Notify

on:
  schedule:
    - cron: "*/10 * * * *"   # 10分ごとに実行
  workflow_dispatch:          # 手動実行も可能

permissions:
  contents: write             # last_submission_ids.json を commit & push するため

jobs:
  check-ac:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install requests pyyaml

      - name: Run AC check script
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: python scripts/check_ac.py

      - name: Commit and push state file
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/last_submission_ids.json
          git diff --cached --quiet || git commit -m "chore: update last submission ids"
          git push
```

> **cron の最短間隔は5分**（GitHub Actions の制限）。  
> リアルタイム性が重要な場合は間隔を `*/5` に短縮可能。

---

## Step 5: 状態管理の仕組み

重複通知を防ぐため、通知済みの最新提出IDを `data/last_submission_ids.json` に保存し、  
チェック後に自動でリポジトリに commit・push する。

```json
{
  "user_alice": 987654321,
  "user_bob":   987654000,
  "user_charlie": 987653000
}
```

---

## 実装チェックリスト

- [ ] `data/members.yml` にメンバーを登録する　← **手動対応が必要**
- [ ] Slack アプリを作成し Incoming Webhook URL を取得する　← **手動対応が必要**
- [ ] GitHub Secrets に `SLACK_WEBHOOK_URL` を登録する　← **手動対応が必要**
- [x] `scripts/check_ac.py` を実装する
- [x] `.github/workflows/ac-notify.yml` を作成する
- [x] `data/last_submission_ids.json` の初期ファイル（`{}`）をコミットする
- [ ] リポジトリを GitHub に push する　← **手動対応が必要**
- [ ] `workflow_dispatch` で手動実行して動作確認する　← **手動対応が必要**
- [ ] cron による定期実行を確認する

---

## 手動対応が必要な作業

以下の作業はファイル自動生成では完結しないため、手動で実施してください。

### 1. `data/members.yml` に実際のメンバーを登録する

`data/members.yml` を開き、ダミーのメンバーを削除して実際の AtCoder ID と表示名に書き換えてください。

```yaml
members:
  - atcoder_id: "your_atcoder_id"   # AtCoder の URL /users/<ここ> の部分
    display_name: "表示名"           # Slack 通知で表示される名前
```

> **AtCoder ID の確認方法**: AtCoder のプロフィールページ `https://atcoder.jp/users/<ID>` の `<ID>` 部分

---

### 2. Slack Incoming Webhook の URL を取得する

1. [https://api.slack.com/apps](https://api.slack.com/apps) にアクセスし、**Create New App** をクリック
2. **From scratch** を選択し、アプリ名（例: `AtCoder Notify`）とワークスペースを設定
3. 左メニューの **Incoming Webhooks** を開き、**Activate Incoming Webhooks** を ON にする
4. **Add New Webhook to Workspace** をクリック
5. 投稿先チャンネルとして `#z-atcoder` を選択し、**Allow** をクリック
6. 生成された Webhook URL（`https://hooks.slack.com/services/XXXXX/YYYYY/ZZZZZ`）をコピーして控えておく

---

### 3. GitHub Secrets に `SLACK_WEBHOOK_URL` を登録する

1. このリポジトリの GitHub ページを開く
2. **Settings** → **Secrets and variables** → **Actions** を開く
3. **New repository secret** をクリック
4. 以下の通り入力して **Add secret** をクリック

```
Name  : SLACK_WEBHOOK_URL
Secret: （手順2でコピーした Webhook URL）
```

---

### 4. リポジトリを GitHub に push する

まだリモートリポジトリが存在しない場合は、GitHub でリポジトリを作成してから以下を実行してください。

```bash
cd /Users/mmk02/AtCoder
git init
git add .
git commit -m "feat: add AtCoder AC notification system"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

> すでにリモートが設定済みの場合は `git push` のみでOKです。

---

### 5. 動作確認（workflow_dispatch による手動実行）

1. GitHub のリポジトリページで **Actions** タブを開く
2. 左側のワークフロー一覧から **AtCoder AC Notify** を選択
3. **Run workflow** → **Run workflow** をクリック
4. ジョブが成功し、`#z-atcoder` チャンネルに通知が届くことを確認する
5. `data/last_submission_ids.json` が自動的に更新・コミットされていることも確認する

> 初回実行時は最近 15 分以内の AC のみ通知されます（過去の大量通知を防ぐため）。  
> テスト用に AtCoder で実際に問題を AC するか、スクリプトの `default_from_second` を調整してください。

---

## 注意事項

| 項目 | 内容 |
|------|------|
| API レート制限 | AtCoder Problems API は非公式。過度なリクエストは避け、間隔は最低5分以上推奨 |
| cron の遅延 | GitHub Actions の cron は負荷状況によって数分遅延することがある |
| 初回実行 | `last_submission_ids.json` が空の場合、過去の提出が大量通知される恐れがあるため、初回は直近の提出IDで初期化する |
| ブランチ保護 | `main` ブランチに保護ルールがある場合、bot による push が弾かれることがある。Actions に `contents: write` 権限を付与し、必要に応じてブランチ保護ルールの例外設定を行う |
