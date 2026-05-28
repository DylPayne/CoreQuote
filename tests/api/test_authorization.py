from corequote_api.authorization import (
    ALL_ROLES,
    has_permission,
    permissions_for_role,
)


def test_every_declared_role_has_permissions():
    for role in ALL_ROLES:
        assert permissions_for_role(role)


def test_pricing_updates_are_limited_to_pricing_roles():
    assert has_permission("owner", "pricing:update")
    assert has_permission("admin", "pricing:update")
    assert has_permission("manager", "pricing:update")

    assert not has_permission("estimator", "pricing:update")
    assert not has_permission("production", "pricing:update")
    assert not has_permission("viewer", "pricing:update")
    assert not has_permission("member", "pricing:update")


def test_user_invites_are_limited_to_company_admin_roles():
    assert has_permission("owner", "users:invite")
    assert has_permission("admin", "users:invite")

    assert not has_permission("manager", "users:invite")
    assert not has_permission("estimator", "users:invite")
    assert not has_permission("production", "users:invite")
    assert not has_permission("viewer", "users:invite")
    assert not has_permission("member", "users:invite")


def test_unknown_roles_have_no_permissions():
    assert permissions_for_role("contractor") == frozenset()
    assert not has_permission("contractor", "cutlists:preview")
