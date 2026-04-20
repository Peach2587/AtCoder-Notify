# AtCoder AC通知システム 実装フロー

Slack チャンネル `#z-atcoder` のメンバーが AtCoder で AC したとき、  
「〇〇がACしました」という通知を GitHub Actions で自動送信する仕組みの設計。

---

## 全体構成

```
AtCoder Problems API
        ↓ (定期ポーリング: 10分ごと)
GitHub Actions (check_ac.py)
        ↓ (新規AC検出 + streak更新)
Slack Incoming Webhook → #z-atcoder チャンネルに通知
        
定期レポート (manual/cron)
        ↓
GitHub Actions (count_streak.py)
        ↓ (全ユーザーのstreak集計)
Slack Incoming Webhook → streak レポート通知
```

---

## ディレクトリ構成

```
.
├── .github/
│   └── workflows/
│       ├── ac-notify.yml          # AC検出ワークフロー（cron: 10分ごと）
│       └── count-streak.yml       # streak集計ワークフロー（manual）
├── scripts/
│   ├── check_ac.py                # AC検出 & Slack通知＆streak更新スクリプト
│   └── count_streak.py            # streak集計・レポートスクリプト
├── utils/
│   ├── __init__.py                # ユーティリティパッケージ
│   ├── constants.py               # 定数定義（パス、API設定など）
│   ├── hash_utils.py              # ハッシュ関連関数
│   ├── file_utils.py              # ファイル操作関数
│   ├── api_utils.py               # API呼び出し関数
│   └── slack_utils.py             # Slack通知関数
├── data/
│   ├── last_submission_ids.json   # 最後に通知した提出IDを記録
│   ├── streak.json                # 各ユーザーのstreak情報（ハッシュID管理）
│   └── members.yml                # メンバー設定ファイル（フォールバック用）
├── .gitignore
├── .python-version
├── uv.lock
└── README.md
```

---

## Step 1: メンバー設定を GitHub Secrets に登録

メンバー情報（AtCoder ID と表示名）を GitHub Secrets に登録する。

```
Settings → Secrets and variables → Actions → New repository secret
```

### 方法A: MEMBERS_YAML（推奨）

```
Name  : MEMBERS_YAML
Value : members:
  - atcoder_id: "user_alice"
    display_name: "Alice"
  - atcoder_id: "user_bob"
    display_name: "Bob"
```

> **メリット**: YAML形式で人間が読みやすく、複数行での設定に対応

### 方法B: MEMBERS_JSON

```
Name  : MEMBERS_JSON
Value : [{"atcoder_id": "user_alice", "display_name": "Alice"}, {"atcoder_id": "user_bob", "display_name": "Bob"}]
```

> **MEMBERS_YAML が優先されます**。フォールバックのみに用途に用いてください。

メンバーの追加・削除はこの Secret を編集して更新する。

---

## Step 2: AC検出スクリプト（check_ac.py）

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
1. 環境変数 MEMBERS_YAML/MEMBERS_JSON から メンバー情報を読み込む（utils.load_members を使用）
2. data/last_submission_ids.json と data/streak.json を読み込む（初回は空）
3. 各メンバーについて:
   a. AtCoder Problems API に直近の提出履歴をリクエスト
   b. result == "AC" の提出を抽出
   c. 前回通知済みのIDより新しいものだけを選別
   d. 新規ACがあれば以下を実行:
      - Slack Webhook に POST（通知）
      - その日付に基づいて streak を計算・更新（utils.update_streak_for_date）
      - streak情報を data/streak.json に保存
4. data/last_submission_ids.json と data/streak.json を最新の情報で更新
5. 更新したファイルを git commit & push（状態を永続化）
```

### Streak計算ロジック

新規AC検出時、その提出日付に対して以下の処理を実行：

```
- 前回のAC日が「昨日」→ streak継続（+1）
- 前回のAC日が「昨日以外」 → streak リセット（=1）
- 初回 → streak = 1
```

これにより、**API制限の範囲内で段階的にaccurate なstreak管理を実現**。

### Slack 通知メッセージ例

```
:accepted: *Alice* が <https://atcoder.jp/contests/abc123/tasks/abc123_a|A - Beginner Contest 123> を AC しました！
```

---

## Step 3: Streak集計スクリプト（count_streak.py）

`scripts/count_streak.py` で以下の処理を行う。

### 目的

check_ac.py による段階的な streak 更新を補完し、定期的に全ユーザーの streak を確認・集計する。

**特徴:**
- API 制限を回避し、最新3ヶ月の提出履歴のみを参照
- ユーザーのID をハッシュ化して管理（プライバシー保護）
- 集計結果を表形式で表示・Slack に通知

### 処理フロー

```
1. 環境変数 MEMBERS_YAML/MEMBERS_JSON から メンバー情報を読み込む（utils.load_members）
2. 各メンバーについて:
   a. fetch_submissions(atcoder_id, from_second=過去3ヶ月) で最新提出を取得
   b. AC日付一覧を抽出
   c. ストリークを計算（today or yesterday with AC判定）
3. 結果を表形式で表示
4. 各ユーザーのハッシュID をキーに data/streak.json に保存
5. Slack に集計結果を通知
```

---

## Step 4: Slack Incoming Webhook の設定

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

## Step 5: GitHub Actions ワークフロー

### 5.1 AC通知ワークフロー（`.github/workflows/ac-notify.yml`）

```yaml
name: AtCoder AC Notify

on:
  schedule:
    - cron: "*/10 * * * *"   # 10分ごとに実行
  workflow_dispatch:          # 手動実行も可能

permissions:
  contents: write             # data/ ファイルを commit & push するため

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
          MEMBERS_YAML: ${{ secrets.MEMBERS_YAML }}
        run: python scripts/check_ac.py

      - name: Commit and push updated state files
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/last_submission_ids.json data/streak.json
          git diff --cached --quiet || git commit -m "chore: update AC state and streak data"
          git push
```

> **cron の最短間隔は5分**（GitHub Actions の制限）。  
> リアルタイム性が重要な場合は間隔を `*/5` に短縮可能。

### 5.2 Streak集計ワークフロー（`.github/workflows/count-streak.yml`）

```yaml
name: Count Streak

on:
  workflow_dispatch:          # 手動実行のみ

permissions:
  contents: write             # streak.json を commit & push するため

jobs:
  count-streak:
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

      - name: Run streak counter script
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          MEMBERS_YAML: ${{ secrets.MEMBERS_YAML }}
        run: python scripts/count_streak.py

      - name: Commit and push streak data
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/streak.json
          git diff --cached --quiet || git commit -m "chore: update streak data"
          git push
```

> **実行方法**: GitHub のリポジトリページで **Actions** → **Count Streak** → **Run workflow** をクリック

---

## Step 6: 状態管理の仕組み

### 提出追跡ファイル（`data/last_submission_ids.json`）

check_ac.py で新規AC通知を行った最新提出IDを記録（重複通知防止）。

```json
{
  "d412b31893702a6d": 987654321,
  "d412b31893702a6d_epoch": 1658066449,
  "8bf82cf0c769def1": 987654000,
  "8bf82cf0c769def1_epoch": 1658066400
}
```

> キーはユーザーID のハッシュ値（SHA-256先頭16文字）

### Streak管理ファイル（`data/streak.json`）

各ユーザーの現在のストリーク日数と最終AC日を記録。

```json
{
  "d412b31893702a6d_streak": 20,
  "d412b31893702a6d_last_ac_date": "2026-04-20",
  "8bf82cf0c769def1_streak": 0,
  "8bf82cf0c769def1_last_ac_date": "2026-04-18"
}
```

> 記録は check_ac.py の新規AC検出時に段階的に更新される。
> count_streak.py による定期集計で全体を補完・検証。

---

## 実装チェックリスト

- [ ] Slack アプリを作成し Incoming Webhook URL を取得する　← **手動対応が必要**
- [ ] GitHub Secrets に `SLACK_WEBHOOK_URL` を登録する　← **手動対応が必要**
- [ ] GitHub Secrets に `MEMBERS_YAML` を登録する　← **手動対応が必要**
- [x] `scripts/check_ac.py` を実装する
- [x] `scripts/count_streak.py` を実装する
- [x] `utils/` ユーティリティパッケージを作成する
- [x] `.github/workflows/ac-notify.yml` を作成する
- [x] `.github/workflows/count-streak.yml` を作成する
- [x] `data/last_submission_ids.json` の初期ファイル（`{}`）をコミットする
- [x] `data/streak.json` の初期ファイル（`{}`）をコミットする
- [ ] リポジトリを GitHub に push する　← **手動対応が必要**
- [ ] `workflow_dispatch` で手動実行して動作確認する　← **手動対応が必要**
- [ ] cron による定期実行を確認する　← **手動対応が必要**

---

## 手動対応が必要な作業

以下の作業はファイル自動生成では完結しないため、手動で実施してください。

### 1. Slack Incoming Webhook の URL を取得する

1. [https://api.slack.com/apps](https://api.slack.com/apps) にアクセスし、**Create New App** をクリック
2. **From scratch** を選択し、アプリ名（例: `AtCoder Notify`）とワークスペースを設定
3. 左メニューの **Incoming Webhooks** を開き、**Activate Incoming Webhooks** を ON にする
4. **Add New Webhook to Workspace** をクリック
5. 投稿先チャンネルとして `#z-atcoder` を選択し、**Allow** をクリック
6. 生成された Webhook URL（`https://hooks.slack.com/services/XXXXX/YYYYY/ZZZZZ`）をコピーして控えておく

---

### 2. GitHub Secrets に `SLACK_WEBHOOK_URL` を登録する

1. このリポジトリの GitHub ページを開く
2. **Settings** → **Secrets and variables** → **Actions** を開く
3. **New repository secret** をクリック
4. 以下の通り入力して **Add secret** をクリック

```
Name  : SLACK_WEBHOOK_URL
Secret: （手順2でコピーした Webhook URL）
```

---

### 3. GitHub Secrets に `MEMBERS_YAML` を登録する（推奨）

1. このリポジトリの GitHub ページを開く
2. **Settings** → **Secrets and variables** → **Actions** を開く
3. **New repository secret** をクリック
4. 以下の通り入力して **Add secret** をクリック

```
Name  : MEMBERS_YAML
Secret: members:
  - atcoder_id: "your_atcoder_id_1"
    display_name: "表示名1"
  - atcoder_id: "your_atcoder_id_2"
    display_name: "表示名2"
```

> **AtCoder ID の確認方法**: AtCoder のプロフィールページ `https://atcoder.jp/users/<ID>` の `<ID>` 部分

#### 代替案: MEMBERS_JSON を使用する場合

```
Name  : MEMBERS_JSON
Secret: [{"atcoder_id": "your_atcoder_id", "display_name": "表示名"}, ...]
```

> **MEMBERS_YAML が優先されます**。MEMBERS_JSON はフォールバック用の代替形式です。

---

### 4. リポジトリを GitHub に push する

まだリモートリポジトリが存在しない場合は、GitHub でリポジトリを作成してから以下を実行してください。

```bash
cd /Users/mmk02/Downloads/AtCoder
git init
git add .
git commit -m "feat: add AtCoder AC notification system with streak tracking"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

> すでにリモートが設定済みの場合は `git push` のみでOKです。

---

### 5. 動作確認（workflow_dispatch による手動実行）

#### 5.1 AC通知の動作確認

1. GitHub のリポジトリページで **Actions** タブを開く
2. 左側のワークフロー一覧から **AtCoder AC Notify** を選択
3. **Run workflow** → **Run workflow** をクリック
4. ジョブが成功し、`#z-atcoder` チャンネルに通知が届くことを確認する
5. `data/last_submission_ids.json` と `data/streak.json` が自動的に更新・コミットされていることを確認する

> 初回実行時は最近 15 分以内の AC のみ通知されます（過去の大量通知を防ぐため）。

#### 5.2 Streak集計の動作確認

1. GitHub のリポジトリページで **Actions** タブを開く
2. 左側のワークフロー一覧から **Count Streak** を選択
3. **Run workflow** → **Run workflow** をクリック
4. ジョブが成功し、`#z-atcoder` チャンネルに streak レポートが通知されることを確認する
5. `data/streak.json` が更新・コミットされたことを確認する

---

## Streak管理の仕組み

### check_ac.py との連携（段階的更新）

新規AC検出時、以下の処理が自動的に実行される：

1. AC日付を検出
2. 前回のAC日から連続性を判定
3. streak をインクリメント or リセット
4. `data/streak.json` に保存
5. ファイルを commit & push

**メリット**: API制限に関係なく、AC通知の都度ストリーク情報が更新される

### count_streak.py による定期検証

`workflow_dispatch` 手動実行でいつでも全ユーザーの streak を検証可能。

**処理内容**:
- 過去3ヶ月の提出履歴を取得
- 全ユーザーのストリークを再計算
- check_ac.py の段階的更新と整合性を確認
- テーブル形式で display_name とともに表示
- Slack に集計結果を通知

---

## 注意事項

| 項目 | 内容 |
|------|------|
| API レート制限 | AtCoder Problems API は非公式。過度なリクエストは避け、スクリプト実行の間隔は最低5分以上推奨 |
| cron の遅延 | GitHub Actions の cron は負荷状況によって数分遅延することがある |
| 初回実行 | `last_submission_ids.json` が空の場合、過去の提出が大量通知される恐れがあるため、初回実行を 15 分以内に限定している |
| ブランチ保護 | `main` ブランチに保護ルールがある場合、bot による push が弾かれることがある。Actions に `contents: write` 権限を付与し、必要に応じてブランチ保護ルールの例外設定を行う |
| Secrets 管理 | `MEMBERS_YAML` と `SLACK_WEBHOOK_URL` は公開されないように Secrets で保護される。リポジトリを public にしても機密情報は安全に保たれる |
| 新規ユーザー登録 | MEMBERS_YAML に新規ユーザーを追加すると、次回の check_ac.py / count_streak.py 実行から自動的に処理される。`data/streak.json` に新しいハッシュID が登録される |
| ユーザーID のプライバシー | ユーザーID はハッシュ化（SHA-256先頭16文字）されて `data/streak.json` に保存されるため、リポジトリを public にしても直接的なID漏洩はない |
