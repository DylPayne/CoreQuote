from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from corequote_api.auth import (
    AuthStore,
    EmailAlreadyRegistered,
    InvalidCredentials,
)
from corequote_api.schemas import (
    AuthLoginRequest,
    AuthLogoutResponse,
    AuthRegisterRequest,
    AuthTokenResponse,
    AuthUserResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_store() -> AuthStore:
    return AuthStore()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    store: Annotated[AuthStore, Depends(get_auth_store)],
) -> AuthUserResponse:
    token = _require_bearer_token(credentials)
    user = store.get_user_for_token(token)
    if not user:
        raise _unauthorized()
    return AuthUserResponse.model_validate(user)


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a company owner",
    description=(
        "Creates a new company and its first owner user. Frontends should call this for the "
        "initial sign-up flow, store the returned bearer token, and include it as "
        "`Authorization: Bearer <access_token>` on authenticated API requests."
    ),
    responses={
        201: {"description": "Company, owner user, and bearer session were created."},
        409: {"description": "The email address is already registered."},
    },
)
def register(payload: AuthRegisterRequest, store: Annotated[AuthStore, Depends(get_auth_store)]) -> AuthTokenResponse:
    try:
        session = store.register_company_owner(
            company_name=payload.company_name,
            name=payload.name,
            email=payload.email,
            password=payload.password,
        )
    except EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc

    return AuthTokenResponse(
        access_token=session.access_token,
        expires_at=session.expires_at,
        user=AuthUserResponse.model_validate(session.user),
    )


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Log in",
    description=(
        "Validates an existing user's email and password, then creates a new bearer session. "
        "Frontends should store the returned token securely and use it for subsequent calls."
    ),
    responses={
        200: {"description": "Login succeeded and a bearer token was returned."},
        401: {"description": "Email or password is invalid, or the user is inactive."},
    },
)
def login(payload: AuthLoginRequest, store: Annotated[AuthStore, Depends(get_auth_store)]) -> AuthTokenResponse:
    try:
        session = store.login(email=payload.email, password=payload.password)
    except InvalidCredentials as exc:
        raise _unauthorized("Invalid email or password") from exc

    return AuthTokenResponse(
        access_token=session.access_token,
        expires_at=session.expires_at,
        user=AuthUserResponse.model_validate(session.user),
    )


@router.get(
    "/me",
    response_model=AuthUserResponse,
    summary="Get the current user",
    description=(
        "Returns the user represented by the bearer token. Frontends should call this after "
        "loading stored auth state to restore the signed-in user and company context."
    ),
    responses={
        200: {"description": "The bearer token is valid."},
        401: {"description": "The token is missing, expired, revoked, or invalid."},
    },
)
def me(current_user: Annotated[AuthUserResponse, Depends(get_current_user)]) -> AuthUserResponse:
    return current_user


@router.post(
    "/logout",
    response_model=AuthLogoutResponse,
    summary="Log out",
    description=(
        "Revokes the current bearer session. Frontends should delete the stored token after "
        "this call succeeds."
    ),
    responses={
        200: {"description": "The current bearer session was revoked."},
        401: {"description": "The token is missing, expired, revoked, or invalid."},
    },
)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    store: Annotated[AuthStore, Depends(get_auth_store)],
) -> AuthLogoutResponse:
    token = _require_bearer_token(credentials)
    if not store.get_user_for_token(token):
        raise _unauthorized()
    store.revoke_session(token)
    return AuthLogoutResponse(status="ok")


def _require_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    return credentials.credentials


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
