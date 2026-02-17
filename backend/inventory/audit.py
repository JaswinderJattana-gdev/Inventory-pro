from .models import AuditLog

def log(actor, action: str, entity_type: str, entity_id: int, message: str = ""):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        message=message[:255],
    )
