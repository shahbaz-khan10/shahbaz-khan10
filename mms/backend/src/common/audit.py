"""Central audit: MMS records its events into the AMS audit log (single trail)."""

import logging

from django.conf import settings

from .ams_client import ams

logger = logging.getLogger("mms.audit")

ALLOWED_ACTIONS = ("create", "update", "delete", "approve")


def record(action: str, entity_type: str, entity_id, label: str, token: str = "", notes: str = ""):
    """Best-effort write to the central AMS audit log.

    Failures are logged, never allowed to break the business operation. Set
    AUDIT_REQUIRED=true to make audit failures raise instead (used by tests).
    """
    if action not in ALLOWED_ACTIONS:
        action = "update"
    try:
        ok = ams.audit(action, entity_type, entity_id, label, token, notes)
    except Exception as exc:  # pragma: no cover
        logger.warning("audit failed (%s): %s", action, exc)
        ok = False
    if not ok and settings.AUDIT_REQUIRED:
        raise RuntimeError(f"AUDIT_REQUIRED: could not write audit entry for {entity_type}:{entity_id}")
    return ok