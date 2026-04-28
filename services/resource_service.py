import logging
from datetime import datetime
from database.db import get_session
from database.models import ResourceInventory, Department
from services.audit_service import log_action

logger = logging.getLogger(__name__)


# ── Resource CRUD ────────────────────────────────────────

def save_resource(data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        resource_id = data.pop("id", None)
        
        if resource_id:
            resource = session.get(ResourceInventory, resource_id)
            for key, value in data.items():
                if hasattr(resource, key):
                    setattr(resource, key, value)
            resource.last_updated = datetime.utcnow()
        else:
            resource = ResourceInventory(**data)
            resource.last_updated = datetime.utcnow()
            session.add(resource)
            
        session.commit()
        
        log_action(user_id, "CREATE" if not resource_id else "UPDATE",
                  "resource_inventory", resource.id if resource.id else 0,
                  new_values=data)
                  
        return True, "Resource saved"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_resource(resource_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        resource = session.get(ResourceInventory, resource_id)
        if not resource:
            return False, "Resource not found"
            
        old_values = {"resource_type": resource.resource_type, "category": resource.category}
        session.delete(resource)
        session.commit()
        
        log_action(user_id, "DELETE", "resource_inventory", resource_id, old_values=old_values)
        return True, "Resource deleted"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_resources(category: str | None = None, department_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(ResourceInventory)
        
        if category:
            query = query.filter_by(category=category)
        if department_id:
            query = query.filter_by(department_id=department_id)
            
        resources = query.all()
        
        return [
            {
                "id": r.id,
                "resource_type": r.resource_type,
                "category": r.category,
                "available_quantity": r.available_quantity,
                "allocated_quantity": r.allocated_quantity or 0,
                "unit": r.unit,
                "location": r.location,
                "department_id": r.department_id,
                "department_name": r.department.name if r.department else "",
                "last_updated": r.last_updated.isoformat() if r.last_updated else None,
            }
            for r in resources
        ]
    finally:
        session.close()


# ── Resource Allocation ─────────────────────────────────

def allocate_resource(resource_id: int, quantity: float, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        resource = session.get(ResourceInventory, resource_id)
        if not resource:
            return False, "Resource not found"
            
        available = resource.available_quantity
        current_allocated = resource.allocated_quantity or 0
        
        if available < quantity:
            return False, f"Insufficient available quantity (have {available})"
            
        resource.allocated_quantity = current_allocated + quantity
        resource.last_updated = datetime.utcnow()
        session.commit()
        
        log_action(user_id, "UPDATE", "resource_inventory", resource_id,
                  new_values={"allocated_quantity": resource.allocated_quantity})
                  
        return True, f"Allocated {quantity} {resource.unit}"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def release_resource(resource_id: int, quantity: float, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        resource = session.get(ResourceInventory, resource_id)
        if not resource:
            return False, "Resource not found"
            
        current_allocated = resource.allocated_quantity or 0
        
        if current_allocated < quantity:
            return False, f"Cannot release {quantity} (allocated: {current_allocated})"
            
        resource.allocated_quantity = current_allocated - quantity
        resource.last_updated = datetime.utcnow()
        session.commit()
        
        log_action(user_id, "UPDATE", "resource_inventory", resource_id,
                  new_values={"allocated_quantity": resource.allocated_quantity})
                  
        return True, f"Released {quantity} {resource.unit}"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


# ── Resource Availability Check ──────────────────────────────

def check_availability(resource_type: str, quantity_needed: float) -> list[dict]:
    session = get_session()
    try:
        resources = session.query(ResourceInventory).filter_by(
            resource_type=resource_type
        ).all()
        
        available = []
        for r in resources:
            qty_available = r.available_quantity - (r.allocated_quantity or 0)
            if qty_available >= quantity_needed:
                available.append({
                    "id": r.id,
                    "location": r.location,
                    "quantity_available": qty_available,
                    "unit": r.unit,
                    "department_name": r.department.name if r.department else "",
                })
                
        return available
    finally:
        session.close()


def get_resource_summary() -> dict:
    session = get_session()
    try:
        resources = session.query(ResourceInventory).all()
        
        total_available = sum(r.available_quantity for r in resources)
        total_allocated = sum(r.allocated_quantity or 0 for r in resources)
        
        by_category = {}
        for r in resources:
            cat = r.category
            if cat not in by_category:
                by_category[cat] = {"available": 0, "allocated": 0}
            by_category[cat]["available"] += r.available_quantity
            by_category[cat]["allocated"] += r.allocated_quantity or 0
            
        return {
            "total_items": len(resources),
            "total_available": total_available,
            "total_allocated": total_allocated,
            "by_category": by_category,
        }
    finally:
        session.close()