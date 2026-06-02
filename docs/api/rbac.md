# Role Based Access Control

The API uses company-scoped roles plus named permissions. Endpoints should depend on permissions, not hard-coded role checks, so future frontend screens can use the same contract.

## Roles

| Role | Intended use |
| --- | --- |
| `owner` | Full company control, including destructive company actions. Created by `POST /api/v1/auth/register`. |
| `admin` | Company administration, user administration, pricing, quoting, and production work. Cannot delete the company. |
| `manager` | Operational manager who can update catalog and pricing data, quote work, and production status. Cannot invite users or manage roles. |
| `estimator` | Creates projects, quotes, and cutlist previews. Can read catalog and pricing data but cannot update prices. |
| `production` | Reads quote and cutlist data and updates production status. Cannot update prices or invite users. |
| `viewer` | Read-only access to company, catalog, pricing, project, quote, cutlist, and production data. |
| `member` | Legacy role retained for existing users. Treated like `estimator` until all users are migrated to explicit roles. |

## Permission Matrix

| Permission | owner | admin | manager | estimator | production | viewer | member |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `companies:create` | yes | yes | no | no | no | no | no |
| `companies:read` | yes | yes | yes | yes | yes | yes | yes |
| `companies:update` | yes | yes | no | no | no | no | no |
| `companies:delete` | yes | no | no | no | no | no | no |
| `users:invite` | yes | yes | no | no | no | no | no |
| `users:manage_roles` | yes | yes | no | no | no | no | no |
| `users:deactivate` | yes | yes | no | no | no | no | no |
| `catalog:read` | yes | yes | yes | yes | yes | yes | yes |
| `catalog:write` | yes | yes | yes | no | no | no | no |
| `pricing:read` | yes | yes | yes | yes | no | yes | yes |
| `pricing:update` | yes | yes | yes | no | no | no | no |
| `projects:read` | yes | yes | yes | yes | yes | yes | yes |
| `projects:write` | yes | yes | yes | yes | no | no | yes |
| `quotes:read` | yes | yes | yes | yes | yes | yes | yes |
| `quotes:write` | yes | yes | yes | yes | no | no | yes |
| `cutlists:preview` | yes | yes | yes | yes | yes | yes | yes |
| `cutlists:read` | yes | yes | yes | yes | yes | yes | yes |
| `cutlists:write` | yes | yes | yes | yes | no | no | yes |
| `production:read` | yes | yes | yes | no | yes | yes | no |
| `production:update` | yes | yes | yes | no | yes | no | no |

## Endpoint Rules

- Every authenticated API route should use `require_permission("<permission>")`.
- Every company-owned query must still scope by `current_user.company_id`; RBAC answers what the user may do, not which tenant data they may see.
- Company currency changes require the `owner` role even though `admin` also has `companies:update` for other company details.
- Prefer returning `404` when a user asks for another company's resource, so cross-company resource existence is not leaked.
- Use `403` when the user is authenticated but lacks the required permission for their own company.
- Add or update tests for every permission-protected endpoint.

## Frontend Notes

The frontend can use `GET /api/v1/auth/me` to read the current role. It should hide actions the role cannot perform, but the API remains the source of truth and will return `403` if a hidden action is attempted.
