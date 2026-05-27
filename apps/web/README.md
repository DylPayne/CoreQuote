# CoreQuote Web

Vite React frontend for CoreQuote.

## Auth

The app follows `docs/api/auth.md`:

- register company owners with `POST /api/v1/auth/register`
- log in with `POST /api/v1/auth/login`
- restore stored sessions with `GET /api/v1/auth/me`
- log out with `POST /api/v1/auth/logout`

The returned bearer token is stored in `localStorage` under `corequote.authToken` and is sent as:

```http
Authorization: Bearer <access_token>
```

## Development

Install dependencies from the repo root:

```bash
uv sync
```

Run the API, then start the web app:

```bash
npm run dev
```

By default the frontend calls `http://localhost:8000`. Override this with:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Checks

```bash
npm run lint
npm run build
```
