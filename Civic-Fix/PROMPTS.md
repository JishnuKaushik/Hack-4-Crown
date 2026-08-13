# CivicFix — Ordered Claude Code Prompts

Paste these into the Claude Code extension **one at a time, in order**. Wait
for each to finish and verify it works (run the test command it gives you)
before moving to the next. Don't batch these.

For anything marked **[PLAN FIRST]**: send it, read the plan Claude proposes,
correct it if wrong, reply "address all notes, don't implement yet" if it
missed something, and only then say "implement it."

---

### 0. Repo init (do this once, Hour 0 of the event — not before)
```
npx create-next-app@latest civicfix --typescript --tailwind --app --turbopack --eslint --yes
cd civicfix
git init
git add .
git commit -m "init: fresh create-next-app scaffold"
```
Then drop `CLAUDE.md` and `.gitignore` (from this scaffold) into the repo
root before your first Claude Code prompt.

---

### 1. Sanity check
```
Confirm this create-next-app project runs. Show me the folder structure and
explain app/layout.tsx and app/page.tsx in one line each. Don't change
anything yet.
```
Test: `npm run dev`, open `localhost:3000`.

---

### 2. Supabase schema
```
Give me the SQL to run in the Supabase SQL editor to:
(a) enable the PostGIS extension
(b) create a `reports` table with: id (uuid, pk, default gen_random_uuid()),
    created_at (timestamptz, default now()), category (text), severity (text),
    priority int, status text default 'reported', note text,
    image_url text (nullable), and a PostGIS geography(Point,4326) column
    named `location`.
(c) add a GIST index on `location`.
Explain each statement in one line. Don't touch app code in this step.
```
Test: run in Supabase SQL editor, then `select * from reports;` returns empty
table with correct columns.

---

### 3. Env template
```
Give me the .env.local.example template for: NEXT_PUBLIC_SUPABASE_URL,
NEXT_PUBLIC_SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY,
GROQ_API_KEY. One line each explaining what it's for and where I get it.
```
Then manually copy to `.env.local`, fill in real values. Confirm `.env.local`
is gitignored before pasting any real keys.

---

### 4. AI classification route **[PLAN FIRST]**
```
Plan mode: design an API route app/api/report/route.ts that accepts a
base64 image + lat/lng + note, calls Gemini gemini-2.5-flash-lite with
responseMimeType: "application/json" and a responseSchema returning
{category, severity, priority_score, summary}, then inserts the result plus
location into the Supabase `reports` table. Don't implement yet — show me
the plan first.
```
Then:
```
Address my notes, then implement the route. Use @google/genai
(import GoogleGenAI). Read GEMINI_API_KEY and Supabase keys from
.env.local. Give me the exact curl/test command to hit this route locally.
```
Test: run the command it gives you, confirm a row appears in Supabase.

---

### 5. Report submission form
```
Create app/report/page.tsx: a mobile-friendly form with a photo file input
(convert to base64 client-side), a note textarea, and a submit handler that
POSTs to /api/report and displays the returned category/severity/priority.
Tailwind styling, clean and modern, no external form libraries.
```
Test: submit a real photo from the browser, confirm the classification
renders on screen.

---

### 6. Map location picker
```
Add a map location picker to the report form using react-map-gl with
MapLibre (NOT Mapbox — no token needed). Load it via next/dynamic with
ssr: false to avoid the "window is not defined" App Router crash. Import the
MapLibre CSS. Let the user click/drag a pin; pass the resulting lat/lng into
the form's submit payload.
```
Test: click the map, confirm lat/lng populates before submit; refresh page,
confirm no SSR crash in the console.

---

### 7. Authority dashboard
```
Create app/dashboard/page.tsx: fetch all reports from Supabase, render a
MapLibre map with pins colored by severity, a table below listing all
reports, and stat cards showing counts by category and by status. Add a
dropdown per table row to update a report's status
(Reported → In Progress → Resolved) via a Supabase update call.
```
Test: change a status in the dropdown, refresh, confirm it persisted.

---

### 8. Nearby-duplicate clustering (nice-to-have — only after 1–7 work end-to-end)
```
Write a Supabase SQL function that, given a report's location and category,
finds other reports within 100 meters of the same category using
ST_DWithin. Then update the dashboard to group these into one "incident"
card with a report count, instead of listing duplicates separately.
```

---

### 9. Seed data
```
Give me SQL to insert 10 realistic sample reports
(potholes/garbage/streetlights/water) with lat/lng scattered around
[YOUR DEMO CITY COORDINATES], varied severity and status values, so the
dashboard map looks alive for the demo.
```

---

### 10. Deploy fix (use as needed, paste actual error)
```
The Vercel build failed with this error:
[paste full error text here]
Explain the cause in one sentence and give the exact fix. Don't rewrite
unrelated files.
```

---

## Reminders while running these
- Commit to git after each numbered step that works.
- If Claude proposes a new npm package, it must justify it in one line first
  — reject silently-added dependencies.
- If a checkpoint (Hour 6: report saves to DB with AI category; Hour 14:
  dashboard end-to-end) slips, cut nice-to-haves before cutting sleep.
- Re-verify the exact Gemini model ID in AI Studio the week of the event —
  Google rotates Flash/Flash-Lite generations.
