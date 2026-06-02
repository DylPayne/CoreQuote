# Companies API Contract

The companies API exposes the authenticated user's tenant record. All endpoints require a bearer token and only return or mutate the caller's own company.

## Permissions

- Read: `companies:read`
- Create and rename: `companies:create` / `companies:update`
- Currency update: `companies:update` plus `owner` role
- Delete: `companies:delete`

The API returns `401` for missing or invalid tokens, `403` for missing permission or non-owner currency changes, and `404` when the requested company is outside the current user's tenant.

## Company Shape

```json
{
  "id": "company-uuid",
  "name": "Core Cabinets",
  "slug": "core-cabinets-a1b2c3",
  "currency_code": "ZAR",
  "created_at": "2026-06-02T10:00:00Z",
  "updated_at": "2026-06-02T10:00:00Z"
}
```

`currency_code` is a three-letter uppercase ISO 4217 code used by quote and pricing screens when formatting money.

## Update Company

```http
PATCH /api/v1/companies/{company_id}
```

Request:

```json
{
  "name": "Core Cabinets Ltd",
  "currency_code": "USD"
}
```

Either field may be supplied. Currency input is normalized to uppercase. Supplying `currency_code` as any role other than `owner` returns:

```json
{
  "detail": "Only company owners can change company currency"
}
```

## Frontend Integration Notes

- Use `GET /api/v1/auth/me` for the current `company_currency_code` during normal app boot.
- Settings screens may call `PATCH /api/v1/companies/{company_id}` to save owner-only currency changes.
- After a successful currency update, refresh local user/company state so library and quote pricing formatters use the new code.
