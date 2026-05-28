from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import Depends, HTTPException, status


Role = Literal[
    "owner",
    "admin",
    "manager",
    "estimator",
    "production",
    "viewer",
    "member",
]

Permission = Literal[
    "companies:create",
    "companies:read",
    "companies:update",
    "companies:delete",
    "users:invite",
    "users:manage_roles",
    "users:deactivate",
    "catalog:read",
    "catalog:write",
    "pricing:read",
    "pricing:update",
    "projects:read",
    "projects:write",
    "quotes:read",
    "quotes:write",
    "cutlists:preview",
    "cutlists:read",
    "cutlists:write",
    "production:read",
    "production:update",
]


ALL_ROLES: tuple[Role, ...] = (
    "owner",
    "admin",
    "manager",
    "estimator",
    "production",
    "viewer",
    "member",
)

ALL_PERMISSIONS: frozenset[Permission] = frozenset(
    (
        "companies:create",
        "companies:read",
        "companies:update",
        "companies:delete",
        "users:invite",
        "users:manage_roles",
        "users:deactivate",
        "catalog:read",
        "catalog:write",
        "pricing:read",
        "pricing:update",
        "projects:read",
        "projects:write",
        "quotes:read",
        "quotes:write",
        "cutlists:preview",
        "cutlists:read",
        "cutlists:write",
        "production:read",
        "production:update",
    )
)

MANAGE_COMPANY_PERMISSIONS: frozenset[Permission] = frozenset(
    (
        "companies:create",
        "companies:read",
        "companies:update",
        "users:invite",
        "users:manage_roles",
        "users:deactivate",
    )
)

PRICING_PERMISSIONS: frozenset[Permission] = frozenset(
    (
        "catalog:read",
        "catalog:write",
        "pricing:read",
        "pricing:update",
    )
)

ESTIMATING_PERMISSIONS: frozenset[Permission] = frozenset(
    (
        "companies:read",
        "catalog:read",
        "pricing:read",
        "projects:read",
        "projects:write",
        "quotes:read",
        "quotes:write",
        "cutlists:preview",
        "cutlists:read",
        "cutlists:write",
    )
)

PRODUCTION_PERMISSIONS: frozenset[Permission] = frozenset(
    (
        "companies:read",
        "catalog:read",
        "projects:read",
        "quotes:read",
        "cutlists:preview",
        "cutlists:read",
        "production:read",
        "production:update",
    )
)

VIEWER_PERMISSIONS: frozenset[Permission] = frozenset(
    (
        "companies:read",
        "catalog:read",
        "pricing:read",
        "projects:read",
        "quotes:read",
        "cutlists:preview",
        "cutlists:read",
        "production:read",
    )
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    "owner": ALL_PERMISSIONS,
    "admin": (ALL_PERMISSIONS - frozenset(("companies:delete",))),
    "manager": ESTIMATING_PERMISSIONS | PRODUCTION_PERMISSIONS | PRICING_PERMISSIONS,
    "estimator": ESTIMATING_PERMISSIONS,
    "production": PRODUCTION_PERMISSIONS,
    "viewer": VIEWER_PERMISSIONS,
    # Legacy role kept so existing users remain valid while the app moves to explicit roles.
    "member": ESTIMATING_PERMISSIONS,
}


def permissions_for_role(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: str, permission: Permission) -> bool:
    return permission in permissions_for_role(role)


def require_permission(permission: Permission) -> Callable:
    from corequote_api.routers.auth import get_current_user

    def dependency(current_user=Depends(get_current_user)):
        role = getattr(current_user, "role", "")
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return current_user

    return dependency
