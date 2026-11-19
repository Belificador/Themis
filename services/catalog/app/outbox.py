from __future__ import annotations

from egm_common.outbox import OutboxMixin

from .db import Base


class OutboxEvent(OutboxMixin, Base):
    __tablename__ = "catalog_outbox"
