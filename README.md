# FinSplit AI

**Describe a group meal in plain English — Claude figures out the fair split.** No forms, no manual line-item entry. Just tell it what happened and it returns an itemized, proportional split with its reasoning shown up front, correctable in plain English.

![FinSplit AI screenshot](docs/screenshot.png)
<!-- Add a screenshot at docs/screenshot.png -->

---

## Why it's different

Tools like Splitwise force you to transcribe a shared meal — which lives in your head as a *story* — into rigid form fields. FinSplit lets you describe it the way you'd say it to a friend:

> "Akhilesh, Kritik, Rujula, Dhruv and Shobhit went to a restaurant. Dhruv and Kritik ate only veg (₹1300). Akhilesh, Rujula and Shobhit had both veg and non-veg (₹2200). Kritik and Shobhit had beers — ₹400 each. Tax was ₹600."

Claude parses the intent, splits tax **proportionally** to what each person ate (not equally — the thing manual splitters get wrong), shows every assumption it made, and lets you fix anything in plain English.

---

## Tech stack

| Layer     | Tech                                     |
| --------- | ---------------------------------------- |
| Backend   | Python · FastAPI                         |
| Frontend  | React · Vite                             |
| Database  | Supabase (Postgres, free tier)           |
| AI        | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Deploy    | Backend → Railway · Frontend → Vercel    |

---

## Local setup

### 1. Clone

```bash
git clone <your-repo-url> finsplit-ai
cd finsplit-ai
```

### 2. Set up the Supabase table

Create a free project at [supabase.com](https://supabase.com), then open **SQL Editor → New query**, paste the contents of [`backend/schema.sql`](backend/schema.sql), and run it. This creates the `splits` table.

Grab your **Project URL** and an **API key** from Settings → API.

### 3. Environment variables

Copy the example and fill in your keys:

```bash
cp .env.example backend/.env
cp .env.example frontend/.env   # only VITE_API_URL is used by the frontend
```

`backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=ey...
```

> If Supabase is left unset the app still works — splits compute and display, only the shareable link is disabled (graceful degradation).

### 4. Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 5. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

---

## Deployment

### Backend → Railway

1. Create a new Railway project from your repo and set the **root directory** to `backend`.
2. Set the start command:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
3. Add environment variables: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, and `FRONTEND_ORIGIN` (your Vercel URL).
4. Deploy and note the public backend URL.

### Frontend → Vercel

1. Import the repo into Vercel and set the **root directory** to `frontend`.
2. Framework preset: **Vite** (build `npm run build`, output `dist`).
3. Add an environment variable `VITE_API_URL` = your Railway backend URL.
4. Deploy. `vercel.json` already rewrites all routes to `index.html` so `/split/:id` deep links work.

---

## API

| Method | Path               | Body / Params                                          | Returns                              |
| ------ | ------------------ | ------------------------------------------------------ | ------------------------------------ |
| POST   | `/api/split`       | `{ description }`                                      | `{ id, result }`                     |
| POST   | `/api/correct`     | `{ original_description, previous_result, correction }`| `{ id, result }`                     |
| GET    | `/api/split/{id}`  | —                                                      | `{ id, result, created_at }` or 404  |

---

## Résumé bullets

- Built FinSplit AI — a full-stack expense splitting app where users describe group meals in plain English and Claude parses intent, calculates proportional splits, and exposes its reasoning transparently
- Designed natural language bill parsing pipeline using Anthropic Claude API; eliminated all manual data entry with a plain-English correction loop
