from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from qwenpaw.enterprise.audit.emit import emit_audit_event
from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome
from qwenpaw.enterprise.audit.repository import AuditRepository

from .models import AuditExportRequest, RetentionPolicy
from .service import ComplianceService


def create_compliance_router() -> APIRouter:
    router = APIRouter(prefix="/compliance", tags=["compliance"])

    @router.get("/retention/policy", response_model=RetentionPolicy)
    def retention_policy() -> RetentionPolicy:
        return RetentionPolicy()

    @router.post("/audit/export")
    async def export_audit(req: AuditExportRequest, request: Request) -> Response:
        runtime = getattr(request.app.state, "enterprise_runtime", None)
        storage = getattr(runtime, "storage", None)
        if storage is None or getattr(storage, "session_factory", None) is None:
            raise HTTPException(
                status_code=503,
                detail="audit storage unavailable (SQL backend required)",
            )
        service = ComplianceService(AuditRepository(storage))
        content, media_type, filename = await service.export_audit(req)
        await emit_audit_event(
            request,
            AuditEventType.COMPLIANCE_EXPORTED,
            action="audit_export",
            outcome=AuditOutcome.SUCCESS,
            resource_type="audit",
            payload={
                "format": req.format.value,
                "limit": req.limit,
                "tenant_id": req.tenant_id or "",
                "filename": filename,
                "event_type": req.event_type or "",
                "start_time": req.start_time.isoformat() if req.start_time else "",
                "end_time": req.end_time.isoformat() if req.end_time else "",
            },
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return router
