# Auth API Contract

The auth API is the foundation for the future frontend. It uses opaque bearer tokens backed by the `auth_sessions` table in Postgres.

## Tenant Model

- A `company` is the tenant boundary.
- Every `user` belongs to one `company`.
- The first user created by `POST /api/v1/auth/register` is the company `owner`.
- Role permissions are defined in `docs/api/rbac.md`.
- Library endpoints for boards, hardware, extras, and pricing are defined in `docs/api/libraries.md`.
- Cutlist preview endpoint and runtime metadata are defined in `docs/api/cutlists.md`.
- Future quote, board, hardware, extras, and pricing APIs must scope every query by `current_user.company_id`.
- Quotes should be scoped through their project: `quotes -> projects.company_id`.

## Frontend Flow

1. Register a company owner with `POST /api/v1/auth/register`, or log in with `POST /api/v1/auth/login`.
2. Store the returned `access_token`.
3. Send authenticated requests with:

```http
Authorization: Bearer <access_token>
```

4. On app boot, call `GET /api/v1/auth/me`.
5. If `/me` returns `401`, clear the stored token and show the login screen.
6. Call `POST /api/v1/auth/logout` when the user signs out, then clear the stored token.

## Endpoints

### `POST /api/v1/auth/register`

Creates a company and the first owner user.

Request:

```json
{
  "company_name": "Core Cabinets",
  "name": "Dylan Payne",
  "email": "dylan@example.com",
  "password": "correct-horse-battery-staple"
}
```

Response `201`:

```json
{
  "access_token": "opaque-token-returned-once",
  "token_type": "bearer",
  "expires_at": "2026-06-03T10:00:00Z",
  "user": {
    "id": "user-uuid",
    "company_id": "company-uuid",
    "company_name": "Core Cabinets",
    "company_currency_code": "ZAR",
    "name": "Dylan Payne",
    "email": "dylan@example.com",
    "role": "owner"
  }
}
```

### `POST /api/v1/auth/login`

Creates a new bearer session for an existing user.

### `GET /api/v1/auth/me`

Returns the authenticated user and company context.
The response includes `company_currency_code`, which the frontend should use as its default pricing display currency.

### `POST /api/v1/auth/logout`

Revokes the current bearer session.

## Security Notes

- Tokens are opaque random values. Only SHA-256 token hashes are stored in Postgres.
- Passwords are hashed with PBKDF2-SHA256.
- The raw token is returned only from register/login.
- Production frontend traffic must use HTTPS.
- Later frontend work should avoid putting tokens in URLs or logs.
