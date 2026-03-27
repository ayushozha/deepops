# DeepOps フロントエンド実装要件

## 概要

Next.js (App Router) + Tailwind CSS v4 を使用。ダークテーマ固定、ハッカー風の紺×白デザイン。

このドキュメントは、現行の FastAPI バックエンド実装を変更せずに成立するフロントエンド要件を定義する。

---

## ルーティング構成

| パス | 役割 |
|------|------|
| `/` | プロジェクト紹介ページ（Pitch） |
| `/dashboard` | リアルタイム運用ダッシュボード |

---

## `/` — ランディングページ

### レイアウト

- ヘッダー: プロジェクト名 `DeepOps` + GitHub リポジトリリンク (`https://github.com/ayushozha/deepops`)
- ボディ: プロジェクトのピッチコンテンツ
  - キャッチコピー: "Self-healing codebases powered by deep agents"
  - アーキテクチャ概要（テキストまたは図）
  - 使用スポンサーツール一覧（Airbyte, Aerospike, Macroscope, Kiro, Auth0, Bland AI, TrueFoundry, Overmind）
  - `/dashboard` への CTA ボタン

---

## `/dashboard` — 運用ダッシュボード

### デザイン仕様

- 背景色: `#0a1628`（深紺）
- アクセントカラー: `#00d4ff`（シアン）、`#ffffff`（白）
- フォント: モノスペース系（Geist Mono）
- パーティション: 白の細いボーダー (`border-white/20`) でパネルを区切る
- セベリティカラー:
  - `critical` → `#ff4444`（赤）
  - `high` → `#ff8800`（オレンジ）
  - `medium` → `#ffcc00`（黄）
  - `low` → `#00ff88`（緑）
  - `pending` → `#888888`（グレー）

### レイアウト（3カラム）

```
┌─────────────────────────────────────────────────────────┐
│  HEADER: DeepOps  [status badge]  [GitHub link]         │
├──────────────────┬──────────────────────────────────────┤
│                  │                                       │
│  LEFT PANEL      │  RIGHT PANEL                         │
│  インシデントログ  │  AI生成 Diff ビューア                 │
│  (スクロール可)   │                                       │
│                  │                                       │
│                  ├──────────────────────────────────────┤
│                  │  RIGHT BOTTOM                        │
│                  │  [APPROVE]  [REJECT]                 │
└──────────────────┴──────────────────────────────────────┘
```

---

## コンポーネント詳細

### ヘッダー

- 左上: `DeepOps` ロゴ（テキスト、モノスペース）
- 中央: バックエンド接続状況バッジ
  - `GET /api/health` が成功している間は `● LIVE`
  - 失敗時は `● DEGRADED` または `● OFFLINE`
- 右: GitHub リポジトリリンク（アイコン付き）

### 左パネル — インシデントログ

**データソース**

- 初期表示: `GET /api/incidents`
- 追加更新: `GET /api/incidents/stream` (SSE)
- 補完更新: フロント側で定期再取得を行う
  - 推奨: 5 秒から 10 秒間隔
  - 推奨タイミング: 初回表示、SSE 再接続後、Window focus 復帰時、承認実行後

**理由**

現行バックエンドでは `incident.created` / `incident.updated` は配信されるが、エージェント内部の一部遷移は SSE に流れない。そのため、SSE のみを信頼せず、定期再取得を前提とする。

**表示項目（1件ごと）**

- セベリティバッジ（色付き）: `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` / `PENDING`
- インシデント ID（短縮表示）
- ステータス
  - 主要表示対象: `stored` / `diagnosing` / `fixing` / `gating` / `awaiting_approval` / `deploying` / `resolved` / `blocked` / `failed`
  - 履歴データによっては `detected` が timeline 内に入ることがある
- サービス名 + 環境
- エラータイプ + エラーメッセージ（1 行省略）
- タイムスタンプ（相対時間: "2m ago"）
  - 表示元は `updated_at_ms` 優先、なければ `created_at_ms`
- クリックで選択 → 右パネルに詳細表示

**一覧の並び順**

- バックエンドの一覧は `created_at_ms` 昇順で返る
- UI は新しいものを上に見せるため、クライアント側で `updated_at_ms desc` または `created_at_ms desc` に並べ替えて表示する

**リアルタイム更新**

- `EventSource` を使用する
- `addEventListener("incident.created", ...)`
- `addEventListener("incident.updated", ...)`
- `addEventListener("pipeline.heartbeat", ...)`
- `pipeline.heartbeat` は接続維持用なので UI 更新には使わない
- `incident.created` / `incident.updated` では `event.data.incident` をローカル state にマージする

### 右パネル — AI生成 Diff ビューア

**データソース**

- 基本: 選択中インシデントの `fix.diff_preview`
- 必要に応じて `GET /api/incidents/{id}` で選択中インシデントだけ再取得してもよい

**表示内容**

- 変更ファイル一覧 (`fix.files_changed`)
- Unified diff 形式で表示
  - 追加行: 緑背景 (`+`)
  - 削除行: 赤背景 (`-`)
  - コンテキスト行: グレー
- `fix.spec_markdown` をアコーディオンで表示
- `diagnosis.root_cause` と `diagnosis.confidence` を表示
- 任意表示
  - `diagnosis.suggested_fix`
  - `fix.test_plan`
  - `approval.channel` (`voice_call` など)

**未選択時**

- "インシデントを選択してください" プレースホルダー

### 右下 — 承認ボタン

**表示条件**

- 選択中インシデントの `approval.status === "pending"`
- かつ `status === "awaiting_approval"`

**ボタン**

- `APPROVE` ボタン: 緑系、クリックで `POST /api/approval/{incident_id}/decision` に `{ "approved": true }`
- `REJECT` ボタン: 赤系、クリックで `POST /api/approval/{incident_id}/decision` に `{ "approved": false }`

**承認後の処理**

- API レスポンスの `incident` をそのまま state に反映する
- 必要に応じて `GET /api/incidents/{id}` を再取得して整合を取る

**補足**

- `low` / `medium` は自動承認で `resolved` まで進むことがあるため、常に承認ボタンが出るとは限らない
- `high` / `critical` は `approval.channel === "voice_call"` になることがある
- 承認済み / 却下済み時はステータス表示のみとし、ボタンは非表示にする

---

## バックエンド API 一覧

| メソッド | エンドポイント | 用途 |
|---------|--------------|------|
| `GET` | `/api/incidents` | インシデント一覧取得（`?status=&limit=50`） |
| `GET` | `/api/incidents/{id}` | インシデント詳細取得 |
| `GET` | `/api/incidents/stream` | SSE リアルタイムストリーム |
| `POST` | `/api/approval/{id}/decision` | 承認 / 却下（`{ approved: bool }`） |
| `GET` | `/api/health` | バックエンド死活確認 |

### API 実装メモ

- `GET /api/incidents` はサマリではなく、完全な `Incident[]` を返す
- `GET /api/incidents/{id}` は完全な `Incident` を返す
- `POST /api/approval/{id}/decision` は bare incident ではなく、ラップ済みオブジェクトを返す

```typescript
type ApprovalDecisionResponse = {
  processed: boolean;
  incident: Incident;
  flow: {
    action: string;
    mode: string;
    reason: string;
    next_status: string | null;
    requires_human: boolean;
    should_call_human: boolean;
  };
  policy: {
    severity: string;
    required: boolean;
    mode: string;
    status: string;
    route: string;
    next_action: string;
    channel: string | null;
    decider: string | null;
    reason: string;
    requires_phone_escalation: boolean;
  };
  auth0_context: Record<string, unknown>;
  explanations: Record<string, unknown>;
  execution_package?: Record<string, unknown> | null;
  hotfix_package?: Record<string, unknown> | null;
  human_input?: Record<string, unknown> | null;
};
```

---

## SSE イベント構造

`/api/incidents/stream` はカスタム event 名を使う。

- `incident.created`
- `incident.updated`
- `pipeline.heartbeat`

```typescript
type IncidentStreamEvent = {
  event: string;
  sent_at_ms: number;
  incident_id: string | null;
  status: string | null;
  severity: string | null;
  updated_at_ms: number | null;
  timeline_event: {
    at_ms: number;
    status: string;
    actor: string;
    message: string;
    sponsor?: string;
    metadata?: Record<string, unknown> | null;
  } | null;
  incident: Incident | null;
  ok?: true; // heartbeat のみ
};
```

実装上は `event.data` を `JSON.parse()` し、`incident` が存在する場合だけ state 更新対象とする。

---

## インシデントデータ構造（主要フィールド）

```typescript
type Incident = {
  incident_id: string;
  status:
    | "detected"
    | "stored"
    | "diagnosing"
    | "fixing"
    | "gating"
    | "awaiting_approval"
    | "deploying"
    | "resolved"
    | "blocked"
    | "failed";
  severity: "pending" | "low" | "medium" | "high" | "critical";
  service: string;
  environment: string;
  created_at_ms: number;
  updated_at_ms: number;
  resolution_time_ms?: number | null;
  source: {
    provider?: string;
    path?: string;
    error_type: string;
    error_message: string;
    source_file: string;
    timestamp_ms?: number;
    fingerprint?: string | null;
  };
  diagnosis: {
    status: "pending" | "running" | "complete" | "failed";
    root_cause: string | null;
    suggested_fix?: string | null;
    affected_components?: string[] | null;
    confidence: number | null;
    severity_reasoning?: string | null;
  };
  fix: {
    status: "pending" | "running" | "complete" | "failed";
    diff_preview: string | null;
    files_changed: string[];
    spec_markdown: string | null;
    test_plan?: string[];
  };
  approval: {
    required: boolean;
    mode: string;
    status: "pending" | "approved" | "rejected" | string;
    channel: string | null;
    decider: string | null;
    bland_call_id: string | null;
    notes: string | null;
    decision_at_ms: number | null;
  };
  deployment?: {
    provider?: string;
    status?: string;
    service_name?: string | null;
    environment?: string | null;
    commit_sha?: string | null;
    deploy_url?: string | null;
    started_at_ms?: number | null;
    completed_at_ms?: number | null;
    failure_reason?: string | null;
  };
  timeline: Array<{
    at_ms: number;
    status: string;
    actor: string;
    message: string;
    sponsor?: string;
    metadata?: Record<string, unknown> | null;
  }>;
};
```

---

## 実装ファイル構成

```
frontend/app/
  layout.tsx          # 共通レイアウト（フォント、グローバルCSS）
  globals.css         # カラー変数、ハッカー風テーマ定義
  page.tsx            # / ランディングページ
  dashboard/
    page.tsx          # /dashboard メインページ
    components/
      IncidentList.tsx     # 左パネル: インシデントログ
      DiffViewer.tsx       # 右パネル: Diffビューア
      ApprovalButtons.tsx  # 右下: 承認/却下ボタン
      SeverityBadge.tsx    # セベリティバッジ（共通）
      StatusBadge.tsx      # ステータスバッジ（共通）
    hooks/
      useIncidents.ts      # 一覧取得 + SSE購読 + 定期再取得
      useApproval.ts       # 承認/却下アクション + response.incident 反映
```

---

## 環境変数

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 注意事項

- ダークテーマのみ（ライトテーマ不要）
- `globals.css` の `prefers-color-scheme` メディアクエリは削除し、固定ダーク背景にする
- SSE は `EventSource` API で実装し、`addEventListener` でカスタム event 名を購読する
- コンポーネントアンマウント時に `EventSource.close()` を呼ぶ
- `pipeline.heartbeat` は無視する
- 承認ボタンはダブルクリック防止のため送信中は `disabled` にする
- バックエンドに CORS 設定が見当たらないため、ローカル開発では `next.config.ts` の `rewrites` または同等のプロキシを前提にする
- 一覧 API は昇順なので、表示順はフロント側で整える
- SSE だけでは全ステータス遷移を捕まえきれないため、定期再取得を前提にする
