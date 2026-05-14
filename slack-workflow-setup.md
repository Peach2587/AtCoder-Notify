# Slack Workflow Builder で GitHub Workflow を手動実行

Slack のスラッシュコマンド `/count-streak` を登録して、GitHub Actions の `count-streak.yml` ワークフローを Slack から直接トリガーする手順。

---

## 前提条件

- Slack Workspace の管理者権限がある
- GitHub アカウント（リポジトリ：`mmk02/AtCoder`）へのアクセス権限がある

---

## Step 1: Slack Workspace に GitHub App をインストール

### 1.1 GitHub App を検索

1. Slack Workspace を開く
2. **App** → **App Directory** をクリック
3. 検索ボックスで `GitHub` を検索
4. 公式の **GitHub** app が表示されたらクリック

### 1.2 GitHub App をインストール

1. **Install** をクリック
2. Slack Workspace を選択
3. **Allow** をクリック
4. GitHub のアカウント認証画面にリダイレクト
5. GitHub でログイン（まだの場合）
6. **Slack が GitHub にアクセスすることを許可**

### 1.3 GitHub App の接続設定

1. Slack 内で GitHub App の設定ページが開く
2. 以下の情報を設定：
   - **GitHub アカウント（またはOrg）**: `mmk02`
   - **リポジトリ**: `mmk02/AtCoder`
3. **Save** をクリック

---

## Step 2: Slack Workflow Builder でワークフローを作成

### 2.1 Workflow Builder に移動

1. Slack Workspace の任意のチャンネルを開く
2. メニュー → **Workflow Builder** をクリック
   - または https://slack.com/apps/{workspace-id}/workflow-builder に直接アクセス

### 2.2 新しいワークフローを作成

1. **Create** → **From scratch** をクリック
2. **New workflow** ダイアログが表示されたら以下を入力：
   - **Workflow name**: `Trigger AtCoder Streak Count`
   - **Description**: `GitHub Actions の streak ワークフローを実行`
   - **Save** をクリック

### 2.3 Trigger を設定（スラッシュコマンド）

1. **Add step** をクリック
2. **Trigger** セクション内の **Slash command** を選択
3. **Add trigger** をクリック
4. 以下を入力：
   - **Command**: `count-streak`
   - **Description**: `AtCoder streak を集計・通知`
   - **Usage hint**: `（空のままでOK）`
   - **Add** をクリック

### 2.4 Action を設定（GitHub Workflow 実行）

1. ワークフローエディタで **Add step** をクリック
2. **Action** を選択
3. 検索ボックスで `GitHub` を検索
4. **GitHub: Run workflow** を選択
   - **注**: 古い GitHub App の場合は見当たらないかもしれません。その場合は **Step 2.5** を参照してください

### 2.5 GitHub Action の設定

以下の情報を入力：

| 項目 | 値 |
|------|-----|
| **GitHub App instance** | GitHub（インストールしたアプリ） |
| **Repository owner** | mmk02 |
| **Repository** | AtCoder |
| **Workflow file** | .github/workflows/count-streak.yml |
| **Ref (branch)** | main |

**Save** をクリック

### 2.6 ワークフロー完了時の通知を設定（オプション）

1. **Add step** をクリック
2. **Action** → **Send a message** を選択
3. 以下を設定：
   - **Send message to**: 通知先チャンネル（例：`#z-atcoder`）
   - **Message text**:
     ```
     ✅ Streak ワークフローが実行されました！
     GitHub Actions で集計中です。結果は数秒で Slack に通知されます。
     ```
4. **Save** をクリック

### 2.7 ワークフローを公開

1. ワークフロー作成画面の右上 **Publish** をクリック
2. 確認ダイアログで **Publish** をクリック
3. ✅ ワークフローが公開されました

---

## Step 3: スラッシュコマンドを使用

### 3.1 テスト実行

1. Slack チャンネルで以下を入力：
   ```
   /count-streak
   ```
2. エンター を押す
3. 以下のような応答が表示されます：
   ```
   Running workflow...
   ```

### 3.2 実行状況を確認

1. GitHub のリポジトリページで **Actions** タブを開く
2. **Count Streak** ワークフローが実行中（または完了）か確認
3. 実行完了後、Slack に結果が通知される

---

## トラブルシューティング

### Q1: "GitHub App not configured for this workspace" エラーが表示される

**解決策:**
1. Slack Workspace に GitHub App が正しくインストールされているか確認
2. GitHub App 設定ページで、リポジトリが正しく指定されているか確認
3. 必要に応じて GitHub App を再インストール

### Q2: ワークフローが実行されない / エラーになる

**確認項目:**
1. GitHub リポジトリの `.github/workflows/count-streak.yml` が存在するか
2. `main` ブランチに最新のワークフローファイルが存在するか
3. GitHub App に `Actions` 実行権限があるか

**GitHub App の権限確認:**
1. GitHub Settings → Apps and integrations → Installed GitHub Apps
2. Slack アプリを選択
3. **Permissions** タブで以下の権限があるか確認：
   - `Actions: Read & Write`
   - `Contents: Read`

### Q3: ワークフロー実行後、Slack に通知が来ない

**確認項目:**
1. Workflow Builder で "Send a message" ステップが正しく設定されているか
2. 通知先チャンネルが正しいか
3. GitHub Actions 側で Slack 通知が正しく送信されているか（スクリプトの設定確認）

### Q4: 権限不足で実行できない

**解決策:**
1. Slack Workspace の管理者に、自分が Workflow Builder を使用する権限があるか確認
2. GitHub でリポジトリへのアクセス権限があるか確認
3. Personal Access Token が必要な場合：
   - GitHub Settings → Developer settings → Personal access tokens
   - 新しいトークンを生成（`workflow` スコープを含める）
   - GitHub App に設定

---

## 高度なカスタマイズ

### カスタム通知メッセージ

ワークフロー実行前に確認メッセージを表示：

1. **Add step** → **Action** → **Send a message** を追加
2. 以下をメッセージに含める：
   ```
   🔄 Streak ワークフローをトリガーします...
   実行中... (<@username>)
   ```

### 複数チャンネルへの通知

違うチャンネルへの通知が必要な場合：

1. **Add step** で複数の "Send a message" アクションを追加
2. 各アクションで異なるチャンネルを指定

### 実行条件の追加

特定の時間帯のみ実行するなど、条件を設定：

1. Workflow Builder で **Conditional logic** を使用
2. 例: `時間が 9:00 - 18:00 の場合のみ実行`

---

## 参考リンク

- [Slack Workflow Builder の公式ドキュメント](https://slack.com/help/articles/17541497516403-Using-Workflow-Builder)
- [GitHub / Slack インテグレーション](https://github.com/integrations/slack)
- [GitHub Actions API リファレンス](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)

---

## まとめ

| ステップ | 内容 |
|---------|------|
| ✅ Step 1 | GitHub App を Slack にインストール |
| ✅ Step 2 | Workflow Builder でワークフロー作成 |
| ✅ Step 3 | `/count-streak` コマンドでテスト実行 |

これで `/count-streak` コマンドを Slack から実行できるようになりました！🎉
