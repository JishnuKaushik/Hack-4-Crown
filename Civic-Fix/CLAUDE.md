# CLAUDE.md — CivicFix (Team Neural Forge, Hack-4-Crown)

## What this is
CivicFix: citizen submits a photo + location → Gemini vision LLM classifies
category/severity as JSON → report lands on an authority map dashboard with a
status badge. This is the 24-hour MVP slice, not the full pitch-deck vision.

## Rules for you (Claude Code)
1. **Explain every file you create in one sentence** before/after creating it.
2. **Never add an npm package without telling me why** — one line, before installing.
3. **Keep components small.** One responsibility per file.
4. **After every feature, give me the exact command(s) to test it locally.**
5. **No unexplained magic.** We are beginners — if you use a pattern we
   haven't asked about (e.g. middleware, edge runtime, server actions vs API
   routes), name it and say why in one line.
6. **Plan Mode first for anything non-trivial.** For any feature beyond a
   one-line fix: propose a plan, wait for "address notes, then implement,"
   THEN write code. Do not implement on the first pass unless told to.
7. **One task per prompt.** Don't build ahead of what was asked.
8. Do not fabricate library APIs, Supabase SQL syntax, or Gemini SDK calls —
   if unsure, say so and ask to verify against docs instead of guessing.

## Stack (locked — do not substitute without asking)
| Layer | Choice |
|---|---|
| Framework | Next.js 16 (App Router, TypeScript). `npm run dev` uses `--webpack`,
  not Turbopack — see "Known environment gotchas" below, user-approved
  2026-08-14 after Turbopack proved unusable for local dev on this machine. |
| Styling | Tailwind CSS |
| DB | Supabase Postgres + PostGIS (`geography(Point,4326)`) |
| Auth | Supabase Auth (magic link) — nice-to-have, not MVP-blocking |
| AI | Gemini `gemini-2.5-flash-lite` via `@google/genai` (NOT the legacy `@google/generative-ai`) |
| AI fallback | Groq, OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`) |
| Maps | MapLibre GL via `react-map-gl` (no token/card, NOT Mapbox) |
| Deploy | Vercel (NOT Netlify — deck is stale on this) |
| Storage | Base64 image straight to Gemini for MVP. Supabase Storage only if we
  need to persist/display the image later. |

## Known environment gotchas (Next.js 16 / App Router)
- Route params are **async** now — `params` must be awaited in route handlers/pages.
- `middleware.ts` is renamed `proxy.ts` in this version — confirm current
  naming before writing one; don't assume from older tutorials.
- Any lib touching `window` (MapLibre/react-map-gl) MUST be loaded via
  `next/dynamic(() => import(...), { ssr: false })`, and its CSS imported
  explicitly, or the build crashes with `window is not defined`.
- Data caching is opt-in in Next 16 — don't assume old fetch-caching defaults.
- **This machine has two Node.js installs; MSYS2's is broken for native
  addons.** `where node` resolves `E:\MSYS2\ucrt64\bin\node.exe` (v24.14.0)
  ahead of the official `C:\Program Files\nodejs\node.exe` (v24.18.0) on
  PATH. Any napi-rs native `.node` addon (confirmed: `@tailwindcss/oxide-win32-x64-msvc`,
  used by Tailwind v4's PostCSS pipeline under both Turbopack and webpack)
  panics under the MSYS2 build with `Node-API symbol has not been loaded`
  (Rust abort, exit code `0xc0000409`) — the addon itself is fine, verified
  by a bare `require()` under the official node. Turbopack is worse: even
  when launched with the official node, its CSS-loader step spawns a new
  child process that re-resolves `node` from PATH and hits the broken MSYS2
  build again; `next dev --webpack` processes CSS in-process so it only
  needs the parent's node to be correct.
  **Fixed 2026-08-14** by reordering the System PATH (admin-elevated) so
  `C:\Program Files\nodejs` precedes `E:\MSYS2\ucrt64\bin` — new terminals
  pick this up automatically.
  **However, this does NOT fully fix Turbopack.** Retested after confirming
  the corrected PATH was active in-session: `next dev` (Turbopack, no
  `--webpack`) still panics identically at the same CSS-loader step, even
  with the official node guaranteed as both parent and PATH-resolved node.
  So Turbopack's crash isn't just a wrong-node-on-PATH problem — its
  IPC-based worker-spawn mechanism for evaluating the Tailwind v4 PostCSS
  loader appears to be broken on Windows on this Next.js 16.3.0 build,
  independent of which Node install runs it. `next dev --webpack` (in-process
  CSS, no IPC worker) is unaffected and is the only combination confirmed
  working end-to-end (`GET /` → 200) in dev mode on this machine right now.
  **Local dev must use `next dev --webpack`** until this Turbopack bug is
  otherwise resolved (retry Turbopack after a Next.js patch release, or file
  upstream). Production builds (`next build`, e.g. on Vercel's Linux
  infrastructure) are a different code path and not confirmed to hit this —
  don't assume they're affected without checking.
  See DEVLOG.md for the full investigation.

## Gemini call shape (verified against `@google/genai` v2.16.0 — re-check if broken)
```ts
import { GoogleGenAI, Type } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const response = await ai.models.generateContent({
  model: "gemini-2.5-flash-lite",
  contents: [
    { inlineData: { mimeType: "image/jpeg", data: base64Image } },
    { text: "Classify this civic issue." },
  ],
  config: {
    responseMimeType: "application/json",
    responseSchema: {
      type: Type.OBJECT,
      properties: {
        category: { type: Type.STRING },
        severity: { type: Type.STRING },
        priority_score: { type: Type.NUMBER },
        summary: { type: Type.STRING },
      },
      required: ["category", "severity", "priority_score", "summary"],
    },
  },
});
// response.text -> JSON string
```
`responseMimeType`/`responseSchema` live under `config`, not top-level. Don't
"fix" this into a different shape without checking current docs.

## Environment variables (never hardcode, always read from `.env.local`)
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=      # server-side only, never expose to client
GEMINI_API_KEY=
GROQ_API_KEY=                   # fallback, optional
```
Give me `.env.local.example` (no real values) whenever you introduce a new key.

## DB shape (source of truth — confirm before altering)
`reports` table: `id`, `created_at`, `category` (text), `severity` (text),
`priority` (int), `status` (text, default `'reported'`), `note` (text),
`image_url` (text, nullable), `location` (`geography(Point,4326)`), GIST index
on `location`.

## MVP scope — build this, nothing more, until it works end-to-end
1. Report page: photo upload → base64, note textarea, map pin picker, submit.
2. `POST /api/report`: base64 image → Gemini (with `responseSchema`) → insert
   row into Supabase.
3. `/dashboard`: map with pins colored by severity, table, stat cards
   (counts by category/status).
4. Status badge per report (`Reported → In Progress → Resolved`), editable
   from the dashboard.

Nice-to-have (only after the 4 above work, deployed, end-to-end):
`ST_DWithin` nearby-duplicate clustering, department-routing lookup table,
Supabase Auth citizen/authority split.

Explicitly out of scope for this build: voice input, semantic dedup, SMS,
multi-language, payments, native mobile.

## Commit discipline
Commit after every working feature (not every file). If a feature breaks
something that worked, say so before moving on — don't silently paper over it.

## Repo integrity note (hackathon rule)
This repo starts fresh at Hour 0 of the event. Do not carry over
CivicFix-specific feature code written before the event starts — only
generic framework/boilerplate scaffolding is allowed pre-event per the
Hack-4-Crown rules.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
