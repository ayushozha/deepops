# DeepOps OAuth Requirements

## Goal

DeepOps の Person B フロントエンドで Auth0 を使った OAuth ログインを有効化し、`/dashboard` を認証済みユーザー向けの画面として運用できる状態にする。

この要件は **2026-03-28** 時点の Auth0 Next.js quickstart snapshot を前提にしている。
参照元は [docs/hackathon-context/auth0-nextjs-quickstart.md](../hackathon-context/auth0-nextjs-quickstart.md)。

## Current State

- `frontend/` は Next.js App Router 構成だが、Auth0 SDK は未導入。
- `frontend/proxy.ts` が存在せず、Auth0 v4 の `/auth/*` ルートは未マウント。
- `frontend` には login / logout / profile UI がない。
- `server/integrations/auth0_client.py` は backend 側の Auth0 API wrapper を持つが、これはブラウザ OAuth セッションを提供しない。
- backend API は現状 JWT / session を検証していないため、今回の要件はまず **Next.js 側の OAuth 利用開始** を成立させる範囲を主対象とする。

## Source Constraints From The Quickstart

- Auth0 Next.js SDK v4 を使う。
- 認証ルートは `/api/auth/*` ではなく `/auth/*` を使う。
- dynamic route handler は作らない。
- `proxy.ts` が必須。
- ログイン導線は `<a href="/auth/login">` のような anchor ベースを優先する。
- callback URL は `http://localhost:3000/auth/callback` を前提にする。

## Auth0 Tenant Configuration

Auth0 側では DeepOps 用の Regular Web Application を作成し、最低限以下を設定する。

- Allowed Callback URLs: `http://localhost:3000/auth/callback`
- Allowed Logout URLs: `http://localhost:3000`
- Allowed Web Origins: `http://localhost:3000`

必要に応じて staging / preview URL を追加してよいが、ローカル開発の基準値は上記で固定する。

## Environment Variables

### Frontend

`frontend/.env.local` に最低限以下を置く。

```env
AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
AUTH0_SECRET=
APP_BASE_URL=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

将来 backend API に access token を渡す場合は以下を追加できる。

```env
AUTH0_AUDIENCE=
AUTH0_SCOPE=openid profile email
```

### Backend

既存 backend と Auth0 設定を揃えるため、repo root の `.env` では少なくとも以下を整合させる。

```env
AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
AUTH0_AUDIENCE=
AUTH0_REDIRECT_URI=http://localhost:3000/auth/callback
AUTH0_ORGANIZATION_ID=
AUTH0_APPROVAL_CONNECTION=
AUTH0_MANAGEMENT_AUDIENCE=
```

重要なのは `AUTH0_REDIRECT_URI` を **`/auth/callback`** に合わせること。既存の古い `/api/auth/callback` 前提は採用しない。

## Required Frontend Changes

### 1. Auth0 SDK foundation

以下を実装する。

- `frontend/package.json`
  - `@auth0/nextjs-auth0` を追加する。
- `frontend/lib/auth0.ts`
  - `new Auth0Client()` を export する。
- `frontend/proxy.ts`
  - Auth0 v4 quickstart に沿って proxy を有効化し、`/auth/*` ルートを使えるようにする。

### 2. Auth routes and session usage

Next.js 側で以下のルートが機能する状態にする。

- `/auth/login`
- `/auth/logout`
- `/auth/callback`
- `/auth/profile`

App Router では server component / route handler から `auth0.getSession()` を使える状態にする。

### 3. Auth UI

以下を追加する。

- ログインボタン
- ログアウトボタン
- 認証済みユーザーの表示名または email
- 必要なら avatar placeholder

UI の最小要件は以下。

- `/` は公開ページのままにする
- `/` から login を開始できる
- `/dashboard` は未ログイン時に login CTA を表示する
- `/dashboard` はログイン済み時に本来の dashboard UI を表示する

## Dashboard Authorization Rules

OAuth を有効にする際の最低ルールは以下とする。

- `APPROVE` / `REJECT` ボタンは認証済みユーザーにのみ表示する
- 未認証時は read-only もしくは login prompt にする
- role / permission ベースの厳格な RBAC は次段階でよいが、session の有無による UI 制御は今回必須

将来的に approver 権限まで扱う場合は、Auth0 の role / permission claim を `session.user` から解釈する追加仕様を別要件で定義する。

## File Layout Requirement

この repo では `src/` ディレクトリを使っていないため、quickstart の `src/...` は以下へ読み替える。

- `src/lib/auth0.ts` -> `frontend/lib/auth0.ts`
- `src/proxy.ts` -> `frontend/proxy.ts`
- `src/components/LoginButton.tsx` -> `frontend/components/auth/LoginButton.tsx`
- `src/components/LogoutButton.tsx` -> `frontend/components/auth/LogoutButton.tsx`
- `src/components/Profile.tsx` -> `frontend/components/auth/Profile.tsx`

## Integration Notes For DeepOps

- 既存 backend の `server/integrations/auth0_client.py` は approval / management API 用なので、frontend OAuth セッション管理とは責務が違う。
- `frontend/next.config.ts` の backend proxy はそのまま必要。Auth0 の `/auth/*` ルートと `/api/*` の FastAPI proxy を混同しない。
- OAuth を有効にしても、backend API 自体はまだ bearer token を検証しない。完全な API 保護は別実装。

## Acceptance Criteria

- `frontend` で Auth0 SDK v4 が導入されている
- `frontend/proxy.ts` が存在し、`/auth/login` と `/auth/logout` が動作する
- ローカルで `http://localhost:3000/auth/callback` に戻ってこられる
- `/dashboard` で session を判定して login CTA または dashboard を出し分けられる
- 認証済みユーザー名または email が UI で確認できる
- `APPROVE` / `REJECT` ボタンは未認証ユーザーに出ない
- `npm run build` と `npm run lint` が通る

## Out Of Scope

- FastAPI 側の JWT 検証
- Auth0 role / permission を使った本格 RBAC
- Social login provider の個別設定
- production domain の最終確定
