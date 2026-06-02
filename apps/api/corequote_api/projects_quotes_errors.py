from __future__ import annotations


class WorkspaceError(Exception):
    pass


class WorkspaceNotFound(WorkspaceError):
    pass


class WorkspaceConflict(WorkspaceError):
    pass


class WorkspaceValidationError(WorkspaceError):
    pass
