# Auth0 Next.js Quickstart Snapshot

## Source

- URL: https://auth0.com/docs/quickstart/webapp/nextjs
- Fetched on: 2026-03-28 (Asia/Tokyo)
- Page title: Add Login to Your Next.js Application - Auth0 Docs
- Canonical URL: https://auth0.com/docs/quickstart/webapp/nextjs

## Page Summary

This guide explains how to add login to a new or existing Next.js app using the Auth0 Next.js v4 SDK.

## What The Page Emphasizes About v4

- No dynamic route handlers are needed.
- Authentication routes are auto-mounted by the proxy.
- `new Auth0Client()` reads environment variables automatically.
- Auth routes now live under `/auth/*` instead of `/api/auth/*`.
- `proxy.ts` is required for authentication flow.
- Login navigation should use anchor tags such as `<a href="/auth/login">`.

## Main Setup Shape

- Create or configure an Auth0 Regular Web Application for local development on `http://localhost:3000`.
- Add project environment variables in `.env.local`.
- Create `src/lib/auth0.ts`.
- Create `src/proxy.ts`.
- Add UI components such as:
  - `src/components/LoginButton.tsx`
  - `src/components/LogoutButton.tsx`
  - `src/components/Profile.tsx`

## Environment Variables Mentioned

- `AUTH0_DOMAIN`
- `AUTH0_CLIENT_ID`
- `AUTH0_CLIENT_SECRET`
- `AUTH0_SECRET`
- `APP_BASE_URL`

The page also shows an AI-assisted quickstart flow that can create the Auth0 application, generate credentials, and write the `.env.local` file automatically.

## Application URLs To Configure In Auth0

- Allowed Callback URLs: `http://localhost:3000/auth/callback`
- Allowed Logout URLs: `http://localhost:3000`
- Allowed Web Origins: `http://localhost:3000`

## Auth Routes Auto-Mounted By The Proxy

- `/auth/login`
- `/auth/logout`
- `/auth/callback`
- `/auth/profile`
- `/auth/access-token`
- `/auth/backchannel-logout`

## Protection Patterns Mentioned

- API route protection uses `withApiAuthRequired`.
- The page includes an `app/api/protected/route.ts` example.
- Session access examples use `auth0.getSession()`.
- `Auth0Provider` is optional in v4. The page says you only need it if you want an initial user available to the `useUser()` hook during server rendering.

## Hackathon Relevance For DeepOps

- This is the most relevant Auth0 entry point for a Next.js-based hackathon frontend or dashboard.
- The v4 `/auth/*` route model is simpler than older `api/auth/*` examples and is the safer reference if we wire Auth0 into this repo later.
- The quickstart is directly aligned with the auth/RBAC role described in `README.md` and `docs/deepops-guide.md`.
