# Aperture — Frontend

A Next.js 16 (App Router) + Tailwind v4 + Framer Motion frontend for the
hybrid recommendation engine in `../backend`. Dark, glassmorphic "cinema
projector" theme — see `app/globals.css` for the full design-token rationale.

## Setup

```bash
npm install
cp .env.local.example .env.local   # points at http://localhost:8000/api/v1 by default
npm run dev
```

Requires the backend (`../backend`) running and seeded — see the root
[README](../README.md) for backend setup. Without it, pages will render but
data fetches will fail gracefully (empty rails, no crash).

## Structure

- `app/` — routes (App Router): home, login, register, search, watchlist,
  profile (Taste DNA), movie/[id] (detail page)
- `components/` — `Header`, `HeroBanner` (canvas particle field),
  `MovieCard` (3D tilt hover), `MovieRail` (horizontal scroll + skeletons),
  `MoodPicker` (AI mood search)
- `lib/api.ts` — typed fetch client, one function per backend endpoint
- `lib/auth-context.tsx` — React context for JWT-based auth (token in
  `localStorage`, attached as a Bearer header on every request)
- `lib/types.ts` — TypeScript types mirroring the backend's Pydantic schemas

## Design notes

- **Fonts**: Bebas Neue (display, via `next/font/google`) + Inter (body).
  Requires network access to `fonts.googleapis.com` at build time; if your
  environment blocks that domain, swap `app/layout.tsx`'s font imports for a
  system font stack (the CSS variables already have fallbacks defined in
  `globals.css`).
- **Signature element**: the Taste DNA "constellation" (`app/profile/page.tsx`)
  — genre breakdown rendered as glowing radial nodes rather than a generic
  bar chart, reusing the same amber accent and line-as-connection motif as
  the particle field in the hero.
- **Motion**: kept deliberate rather than scattered — a page-load fade on
  forms, 3D tilt + scale on card hover, skeleton shimmer while loading. All
  motion respects `prefers-reduced-motion` (see `globals.css`).

## Building

```bash
npm run build
```

Note: building requires fetching font manifests from Google Fonts at build
time. If you're building in a network-restricted environment (e.g. certain
CI sandboxes), temporarily swap the `next/font/google` imports in
`app/layout.tsx` for plain CSS font stacks, build, then revert — this is
purely an environment limitation, not a code issue.

## What's not wired up yet

- Admin analytics dashboard UI (the backend endpoints under `/admin/analytics/*`
  work; no page renders them yet)
- WebSocket live-trending updates (the backend socket exists; the frontend
  doesn't open a connection to it yet)
- Google OAuth button (backend `/auth/google` isn't implemented yet either)
- Voice search (would call the existing `/search` endpoint with transcribed
  text via the Web Speech API — no backend changes needed, just a mic button
  and `SpeechRecognition` wiring in `app/search/page.tsx`)
