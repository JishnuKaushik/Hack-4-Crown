# DEVLOG.md — CivicFix

## 2026-08-14 — Repo scaffold (step 0 of PROMPTS.md)
**Done:** Ran `create-next-app` (TypeScript, Tailwind, App Router, Turbopack,
ESLint) and merged its output into this folder, keeping the existing
`CLAUDE.md` / `.gitignore` / `PROMPTS.md` untouched. `npm install` completed
clean (364 packages, 0 vulnerabilities). Civic-Fix stays a plain subfolder
of the single Hack-4-Crown repo — no nested `.git` (explicit user decision:
one repo, two project folders).

**Root cause fixes:**
- **Bug:** `npm run dev` (and `next dev --webpack`) crashed with a Rust
  panic — `Node-API symbol has not been loaded` — aborting the whole
  process (exit `0xc0000409`), sometimes on boot, sometimes on first page
  compile.
- **Cause:** Two Node.js installs exist on this machine.
  `E:\MSYS2\ucrt64\bin\node.exe` (v24.14.0) was resolving first on PATH,
  and that MSYS2-packaged Node build cannot correctly load napi-rs native
  addons — confirmed by directly `require()`-ing
  `@tailwindcss/oxide-win32-x64-msvc`'s `.node` binary: it loads fine under
  the official `C:\Program Files\nodejs\node.exe` (v24.18.0) and crashes
  under the MSYS2 build. Turbopack made it worse even when launched
  correctly, because its CSS-loader step spawns a *new* child process that
  re-resolves `node` from PATH rather than reusing the parent's
  `process.execPath`, landing on the broken MSYS2 build again. `next dev
  --webpack` processes CSS in-process, so it only needed the parent's node
  to be correct — which made it the cleanest way to isolate the bug, but
  wasn't itself the fix.
- **Fix (partial):** Reordered the **System (Machine) PATH** (required
  Administrator elevation, approved live via UAC by the user) so
  `C:\Program Files\nodejs` precedes `E:\MSYS2\ucrt64\bin`. Machine-level,
  not repo-level — new terminals pick it up automatically; already-open
  shells need restarting. This fully fixed `next dev --webpack`.
  **It did not fully fix Turbopack.** Re-tested with the corrected PATH
  confirmed active in-session (verified via `where node`/explicit prepend):
  `next dev` (Turbopack, the locked-stack default) still panics identically
  at the same CSS-loader step. The panic trace shows an IPC pipe to a
  spawned worker process being forcibly closed mid-handshake — this looks
  like a Turbopack-specific worker-spawn bug on Windows for this Next 16.3.0
  build, not merely "wrong node on PATH." webpack processes CSS in-process
  (no IPC worker), which is why it's unaffected.
- Full gotcha writeup: `CLAUDE.md` → "Known environment gotchas".

**Assumptions:** None beyond the repo-structure decision (confirmed with
user) and treating `next dev --webpack` as the practical local-dev default
until Turbopack's Windows bug is resolved upstream — flagged to user,
awaiting direction on whether to change `package.json`'s dev script (would
deviate from the CLAUDE.md-locked Turbopack default) or keep documenting
the manual `--webpack` flag per-invocation.

**Known Issues:**
- Turbopack (`next dev` without `--webpack`) crashes 100% of the time on
  this machine, root cause not fully resolved (looks upstream, not a repo
  bug) — impact: locked-stack default is currently unusable for local dev
  here; webpack fallback works fine. Not yet confirmed whether `next build`
  (production, e.g. Vercel Linux) hits the same path.
- If a *new* teammate machine hits the same panic, check for a similar
  dual-Node-install PATH conflict first, but confirm with a clean
  `--webpack` test too — PATH alone did not fully explain what we saw here.

**Next:** Step 1 of `PROMPTS.md` — sanity check (`npm run dev`, confirm
`localhost:3000` renders, explain `app/layout.tsx` / `app/page.tsx`).
