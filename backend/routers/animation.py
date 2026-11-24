import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from pydantic_classes import *
from sql_alchemy import *
from database import get_db, integrity_error_detail
from bal_stdlib import *

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/animation/", response_model=None, tags=["Animation"])
def get_all_animation(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Animation)
        query = query.options(joinedload(Animation.scene))
        query = query.options(joinedload(Animation.targetCharacter))
        animation_list = query.all()

        # Serialize with relationships included
        result = []
        for db_animation in animation_list:
            item_dict = db_animation.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)
            if db_animation.scene:
                related_obj = db_animation.scene
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['scene'] = related_dict
            else:
                item_dict['scene'] = None
            if db_animation.targetCharacter:
                related_obj = db_animation.targetCharacter
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['targetCharacter'] = related_dict
            else:
                item_dict['targetCharacter'] = None


            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Animation).all()


@router.get("/animation/count/", response_model=None, tags=["Animation"])
def get_count_animation(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Animation entities"""
    count = database.query(Animation).count()
    return {"count": count}


@router.get("/animation/paginated/", response_model=None, tags=["Animation"])
def get_paginated_animation(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Animation entities"""
    total = database.query(Animation).count()
    animation_list = database.query(Animation).offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": animation_list
    }
@router.get("/animation/search/", response_model=None, tags=["Animation"])
def search_animation(
    animationType: str = None,
    endTimeSeconds: int = None,
    parameters: str = None,
    startTimeSeconds: int = None,
    targetObjectId: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Animation entities by attributes"""
    query = database.query(Animation)

    if animationType is not None:
        query = query.filter(Animation.animationType.ilike(f"%{animationType}%"))
    if endTimeSeconds is not None:
        query = query.filter(Animation.endTimeSeconds == endTimeSeconds)
    if parameters is not None:
        query = query.filter(Animation.parameters.ilike(f"%{parameters}%"))
    if startTimeSeconds is not None:
        query = query.filter(Animation.startTimeSeconds == startTimeSeconds)
    if targetObjectId is not None:
        query = query.filter(Animation.targetObjectId.ilike(f"%{targetObjectId}%"))

    results = query.all()
    return results


@router.get("/animation/{animation_id}/", response_model=None, tags=["Animation"])
async def get_animation(animation_id: int, database: Session = Depends(get_db)) -> Animation:
    db_animation = database.query(Animation).filter(Animation.id == animation_id).first()
    if db_animation is None:
        raise HTTPException(status_code=404, detail="Animation not found")

    response_data = {
        "animation": db_animation,
}
    return response_data



@router.post("/animation/", response_model=None, tags=["Animation"])
async def create_animation(animation_data: AnimationCreate, database: Session = Depends(get_db)) -> Animation:

    if animation_data.scene is not None:
        related_scene = database.query(Scene).filter(Scene.id == animation_data.scene).first()
        if not related_scene:
            raise HTTPException(status_code=400, detail="Scene not found")
    else:
        raise HTTPException(status_code=400, detail="Scene ID is required")
    if animation_data.targetCharacter :
        related_targetCharacter = database.query(Character).filter(Character.id == animation_data.targetCharacter).first()
        if not related_targetCharacter:
            raise HTTPException(status_code=400, detail="Character not found")

    db_animation = Animation(
        animationType=animation_data.animationType,        endTimeSeconds=animation_data.endTimeSeconds,        parameters=animation_data.parameters,        startTimeSeconds=animation_data.startTimeSeconds,        targetObjectId=animation_data.targetObjectId,        scene_id=animation_data.scene,        targetCharacter_id=animation_data.targetCharacter        )

    database.add(db_animation)
    database.flush()
    database.refresh(db_animation)





    database.commit()
    database.refresh(db_animation)
    return db_animation


@router.post("/animation/bulk/", response_model=None, tags=["Animation"])
async def bulk_create_animation(items: list[AnimationCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Animation entities at once"""
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item
            if not item_data.scene:
                raise ValueError("Scene ID is required")

            db_animation = Animation(
                animationType=item_data.animationType,                endTimeSeconds=item_data.endTimeSeconds,                parameters=item_data.parameters,                startTimeSeconds=item_data.startTimeSeconds,                targetObjectId=item_data.targetObjectId,                scene_id=item_data.scene,                targetCharacter_id=item_data.targetCharacter            )
            database.add(db_animation)
            database.flush()  # Get ID without committing
            created_items.append(db_animation.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of Animation failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Animation entities"
    }


@router.delete("/animation/bulk/", response_model=None, tags=["Animation"])
async def bulk_delete_animation(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Animation entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_animation = database.query(Animation).filter(Animation.id == item_id).first()
        if db_animation:
            conflict = animation_delete_conflict(db_animation)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete Animation " + str(item_id) + ": " + conflict)
            database.delete(db_animation)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Animation entities"
    }

@router.put("/animation/{animation_id}/", response_model=None, tags=["Animation"])
async def update_animation(animation_id: int, animation_data: AnimationCreate, database: Session = Depends(get_db)) -> Animation:
    db_animation = database.query(Animation).filter(Animation.id == animation_id).first()
    if db_animation is None:
        raise HTTPException(status_code=404, detail="Animation not found")

    setattr(db_animation, 'animationType', animation_data.animationType)
    setattr(db_animation, 'endTimeSeconds', animation_data.endTimeSeconds)
    setattr(db_animation, 'parameters', animation_data.parameters)
    setattr(db_animation, 'startTimeSeconds', animation_data.startTimeSeconds)
    setattr(db_animation, 'targetObjectId', animation_data.targetObjectId)
    if animation_data.scene is not None:
        related_scene = database.query(Scene).filter(Scene.id == animation_data.scene).first()
        if not related_scene:
            raise HTTPException(status_code=400, detail="Scene not found")
        setattr(db_animation, 'scene_id', animation_data.scene)
    if animation_data.targetCharacter is not None:
        related_targetCharacter = database.query(Character).filter(Character.id == animation_data.targetCharacter).first()
        if not related_targetCharacter:
            raise HTTPException(status_code=400, detail="Character not found")
        setattr(db_animation, 'targetCharacter_id', animation_data.targetCharacter)
    else:
        setattr(db_animation, 'targetCharacter_id', None)
    database.commit()
    database.refresh(db_animation)

    return db_animation


def animation_delete_conflict(db_animation, deleting=None, wholes=()):
    """Why this Animation cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_animation)
        deleting = [db_animation] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    return None


@router.delete("/animation/{animation_id}/", response_model=None, tags=["Animation"])
async def delete_animation(animation_id: int, database: Session = Depends(get_db)):
    db_animation = database.query(Animation).filter(Animation.id == animation_id).first()
    if db_animation is None:
        raise HTTPException(status_code=404, detail="Animation not found")
    conflict = animation_delete_conflict(db_animation)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete Animation " + str(animation_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_animation = {
        attr.key: getattr(db_animation, attr.key)
        for attr in db_animation.__mapper__.column_attrs
    }
    database.delete(db_animation)
    database.commit()
    return deleted_animation



