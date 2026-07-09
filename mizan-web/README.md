# Mizan Web

Front end for **Mizan** — a clinical trial patient-matching web app for coordinators. Shows which eligibility criteria passed, failed, or need more screening, with a full audit trail for every patient–trial recommendation.

Built for the Cursor mobile hackathon. API contract: [mr-mustafa7/Mizan-2/API.md](https://github.com/mr-mustafa7/Mizan-2/blob/main/API.md) (mirrored in [`API.md`](./API.md)).

## Stack

- Next.js 16 (App Router)
- TypeScript
- Tailwind CSS v4

## Getting started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

By default the app uses **mock data** from `public/mocks/` (copied from the Mizan-2 `samples/` directory). To connect to a live backend:

```bash
cp .env.example .env.local
# NEXT_PUBLIC_USE_MOCK_API=false
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Pages

| Route | API endpoints used |
|-------|-------------------|
| `/` | `GET /api/dashboard/coordinator`, `GET /api/dashboard/diagnosis-summary`, `GET /api/matches` |
| `/patients` | `GET /api/patients` |
| `/patients/[id]` | `GET /api/patients/{patient_id}`, `GET /api/matches?patient_id=` |
| `/trials` | `GET /api/trials` |
| `/trials/[id]` | `GET /api/trials/{trial_id}`, `GET /api/matches?trial_id=` |
| `/matches` | `GET /api/matches` |
| `/matches/[patientId]/[trialId]` | `GET /api/matches/{patient_id}/{trial_id}`, `GET /api/matches/{patient_id}/{trial_id}/audit` |
| `/control` | **Behind-the-scenes control panel** — read-only tabs: At-Risk Trials, Patient Eligibility, Audit Trail, Summaries |

## API contract

See [`API.md`](./API.md) — aligned with [Mizan-2](https://github.com/mr-mustafa7/Mizan-2/blob/main/API.md). Mock fixtures live in `public/mocks/`.

## Scripts

```bash
npm run dev      # Start dev server
npm run build    # Production build
npm run start    # Start production server
npm run lint     # ESLint
```
