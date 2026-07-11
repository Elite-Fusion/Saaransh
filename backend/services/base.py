"""
Service-layer base class.

The service layer is the only part of the codebase that talks to the
database. Routes hand it request data; the service hands back ORM
objects (or domain errors) without ever knowing about HTTP. This
separation is the prerequisite for two upcoming features:

  1. **AI integration (Phase 6+).** The Gemini provider will call the
     same service methods the route layer calls. If a service imported
     ``fastapi`` or ``starlette`` it could not be reused by an
     LLM-driven call site that has no HTTP request to bind to.

  2. **Async I/O, alternate sessions, batch jobs.** A service that
     takes a ``Session`` in its constructor can be driven by any
     caller — a worker, a script, a test — that has a session. It is
     not coupled to FastAPI's ``Depends`` machinery.

Rules encoded by this module:

  * A service **must not** import anything from ``fastapi`` or
    ``starlette``. (Enforced by a static check — see
    :mod:`backend.tests.test_service_independence`.)
  * A service **must** receive its database session in the
    constructor, not via a global or a module-level singleton.
  * A service **must** raise domain exceptions (``CaseNotFoundError``)
    for control flow — never return ``None`` as an error signal and
    never raise ``HTTPException`` (which is a FastAPI concern).
"""
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class BaseService(ABC):
    """Abstract base for every service in the project.

    Concrete services inherit this class and implement their public
    methods. The base class guarantees two things:

    * A ``session`` attribute is always available, typed as a
      SQLAlchemy ``Session`` (read-only at the type level — services
      should not assign to ``self.session``).
    * The constructor signature is stable: ``(session: Session)``.
      AI providers, scripts, and tests can all instantiate any
      service with a single argument.
    """

    __slots__ = ("_session",)

    def __init__(self, session: "Session") -> None:
        self._session = session

    @property
    def session(self) -> "Session":
        """The SQLAlchemy session this service is bound to.

        Exposed read-only via a property to discourage services from
        swapping sessions mid-call. If you need a different session,
        build a new service instance.
        """
        return self._session

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__} session={self._session!r}>"
