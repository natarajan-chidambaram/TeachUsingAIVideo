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


@router.get("/scene/", response_model=None, tags=["Scene"])
def get_all_scene(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Scene)
        query = query.options(joinedload(Scene.video))
        scene_list = query.all()

        # Serialize with relationships included
        result = []
        for db_scene in scene_list:
            item_dict = db_scene.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)
            if db_scene.video:
                related_obj = db_scene.video
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['video'] = related_dict
            else:
                item_dict['video'] = None

            # Add many-to-many and one-to-many relationship objects (full details)
            related_character_list = database.query(Character).join(characters, Character.id == characters.c["scenes"]).filter(characters.c["characters"] == db_scene.id).all()
            item_dict['scenes'] = []
            for related_character_obj in related_character_list:
                related_character_dict = related_character_obj.__dict__.copy()
                related_character_dict.pop('_sa_instance_state', None)
                item_dict['scenes'].append(related_character_dict)
            related_animation_list = database.query(Animation).filter(Animation.scene_id == db_scene.id).all()
            item_dict['animations'] = []
            for related_animation_obj in related_animation_list:
                related_animation_dict = related_animation_obj.__dict__.copy()
                related_animation_dict.pop('_sa_instance_state', None)
                item_dict['animations'].append(related_animation_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Scene).all()


@router.get("/scene/count/", response_model=None, tags=["Scene"])
def get_count_scene(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Scene entities"""
    count = database.query(Scene).count()
    return {"count": count}


@router.get("/scene/paginated/", response_model=None, tags=["Scene"])
def get_paginated_scene(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Scene entities"""
    total = database.query(Scene).count()
    scene_list = database.query(Scene).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": scene_list
        }

    result = []
    for db_scene in scene_list:
        related_character_ids = database.query(characters.c["scenes"]).filter(characters.c["characters"] == db_scene.id).all()
        animations_ids = database.query(Animation.id).filter(Animation.scene_id == db_scene.id).all()
        item_data = {
            "scene": db_scene,
            "character_ids": [x[0] for x in related_character_ids],
            "animations_ids": [x[0] for x in animations_ids]        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/scene/search/", response_model=None, tags=["Scene"])
def search_scene(
    endTimeSeconds: int = None,
    sequenceIndex: int = None,
    startTimeSeconds: int = None,
    storyboardNotes: str = None,
    title: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Scene entities by attributes"""
    query = database.query(Scene)

    if endTimeSeconds is not None:
        query = query.filter(Scene.endTimeSeconds == endTimeSeconds)
    if sequenceIndex is not None:
        query = query.filter(Scene.sequenceIndex == sequenceIndex)
    if startTimeSeconds is not None:
        query = query.filter(Scene.startTimeSeconds == startTimeSeconds)
    if storyboardNotes is not None:
        query = query.filter(Scene.storyboardNotes.ilike(f"%{storyboardNotes}%"))
    if title is not None:
        query = query.filter(Scene.title.ilike(f"%{title}%"))

    results = query.all()
    return results


@router.get("/scene/{scene_id}/", response_model=None, tags=["Scene"])
async def get_scene(scene_id: int, database: Session = Depends(get_db)) -> Scene:
    db_scene = database.query(Scene).filter(Scene.id == scene_id).first()
    if db_scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    related_character_ids = database.query(characters.c["scenes"]).filter(characters.c["characters"] == db_scene.id).all()
    animations_ids = database.query(Animation.id).filter(Animation.scene_id == db_scene.id).all()
    response_data = {
        "scene": db_scene,
        "character_ids": [x[0] for x in related_character_ids],
        "animations_ids": [x[0] for x in animations_ids]}
    return response_data



@router.post("/scene/", response_model=None, tags=["Scene"])
async def create_scene(scene_data: SceneCreate, database: Session = Depends(get_db)) -> Scene:

    if scene_data.video is not None:
        related_video = database.query(Video).filter(Video.id == scene_data.video).first()
        if not related_video:
            raise HTTPException(status_code=400, detail="Video not found")
    else:
        raise HTTPException(status_code=400, detail="Video ID is required")
    if scene_data.scenes:
        for id in scene_data.scenes:
            # Entity already validated before creation
            related_character = database.query(Character).filter(Character.id == id).first()
            if not related_character:
                raise HTTPException(status_code=404, detail=f"Character with ID {id} not found")

    db_scene = Scene(
        endTimeSeconds=scene_data.endTimeSeconds,        sequenceIndex=scene_data.sequenceIndex,        startTimeSeconds=scene_data.startTimeSeconds,        storyboardNotes=scene_data.storyboardNotes,        title=scene_data.title,        video_id=scene_data.video        )

    database.add(db_scene)
    database.flush()
    database.refresh(db_scene)

    if scene_data.animations:
        # Validate that all Animation IDs exist
        for related_animation_id in scene_data.animations:
            related_animation = database.query(Animation).filter(Animation.id == related_animation_id).first()
            if not related_animation:
                raise HTTPException(status_code=400, detail=f"Animation with id {related_animation_id} not found")

        # Update the related entities with the new foreign key
        database.query(Animation).filter(Animation.id.in_(scene_data.animations)).update(
            {Animation.scene_id: db_scene.id}, synchronize_session=False
        )
        database.flush()


    if scene_data.scenes:
        for id in scene_data.scenes:
            # Entity already validated before creation
            related_character = database.query(Character).filter(Character.id == id).first()
            # Create the association
            association = characters.insert().values(characters=db_scene.id, scenes=related_character.id)
            database.execute(association)
            database.flush()


    related_character_ids = database.query(characters.c["scenes"]).filter(characters.c["characters"] == db_scene.id).all()
    animations_ids = database.query(Animation.id).filter(Animation.scene_id == db_scene.id).all()
    response_data = {
        "scene": db_scene,
        "character_ids": [x[0] for x in related_character_ids],
        "animations_ids": [x[0] for x in animations_ids]    }
    database.commit()
    database.refresh(db_scene)
    return response_data


@router.post("/scene/bulk/", response_model=None, tags=["Scene"])
async def bulk_create_scene(items: list[SceneCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Scene entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['scenes', 'animations']):
        raise HTTPException(status_code=422, detail="Bulk creation of Scene with relationships is not supported; use POST /scene/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item
            if not item_data.video:
                raise ValueError("Video ID is required")

            db_scene = Scene(
                endTimeSeconds=item_data.endTimeSeconds,                sequenceIndex=item_data.sequenceIndex,                startTimeSeconds=item_data.startTimeSeconds,                storyboardNotes=item_data.storyboardNotes,                title=item_data.title,                video_id=item_data.video            )
            database.add(db_scene)
            database.flush()  # Get ID without committing
            created_items.append(db_scene.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of Scene failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Scene entities"
    }


@router.delete("/scene/bulk/", response_model=None, tags=["Scene"])
async def bulk_delete_scene(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Scene entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_scene = database.query(Scene).filter(Scene.id == item_id).first()
        if db_scene:
            conflict = scene_delete_conflict(db_scene)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete Scene " + str(item_id) + ": " + conflict)
            database.delete(db_scene)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Scene entities"
    }

@router.put("/scene/{scene_id}/", response_model=None, tags=["Scene"])
async def update_scene(scene_id: int, scene_data: SceneCreate, database: Session = Depends(get_db)) -> Scene:
    db_scene = database.query(Scene).filter(Scene.id == scene_id).first()
    if db_scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    setattr(db_scene, 'endTimeSeconds', scene_data.endTimeSeconds)
    setattr(db_scene, 'sequenceIndex', scene_data.sequenceIndex)
    setattr(db_scene, 'startTimeSeconds', scene_data.startTimeSeconds)
    setattr(db_scene, 'storyboardNotes', scene_data.storyboardNotes)
    setattr(db_scene, 'title', scene_data.title)
    if scene_data.video is not None:
        related_video = database.query(Video).filter(Video.id == scene_data.video).first()
        if not related_video:
            raise HTTPException(status_code=400, detail="Video not found")
        setattr(db_scene, 'video_id', scene_data.video)
    if scene_data.animations is not None:
        requested_animations = set(scene_data.animations)
        current_animations = {
            getattr(item, 'id')
            for item in database.query(Animation).filter(Animation.scene_id == db_scene.id).all()
        }
        animations_to_detach = current_animations - requested_animations
        if animations_to_detach:
            raise HTTPException(status_code=409, detail="Animation " + ", ".join(str(item) for item in sorted(animations_to_detach)) + " requires a scene: reassign it instead of removing it")
        animations_to_attach = requested_animations - current_animations
        for related_animation_id in animations_to_attach:
            related_animation = database.query(Animation).filter(Animation.id == related_animation_id).first()
            if not related_animation:
                raise HTTPException(status_code=400, detail="Animation with id " + str(related_animation_id) + " not found")
        if animations_to_attach:
            database.query(Animation).filter(Animation.id.in_(animations_to_attach)).update(
                {Animation.scene_id: db_scene.id}, synchronize_session=False
            )
    if scene_data.scenes is not None:
        existing_related_character_ids = [assoc._mapping["scenes"] for assoc in database.execute(
            characters.select().where(characters.c["characters"] == db_scene.id))]

        related_characters_to_remove = set(existing_related_character_ids) - set(scene_data.scenes)
        for related_character_id in related_characters_to_remove:
            association = characters.delete().where(
                (characters.c["characters"] == db_scene.id) & (characters.c["scenes"] == related_character_id))
            database.execute(association)

        new_related_character_ids = set(scene_data.scenes) - set(existing_related_character_ids)
        for related_character_id in new_related_character_ids:
            related_character = database.query(Character).filter(Character.id == related_character_id).first()
            if related_character is None:
                raise HTTPException(status_code=404, detail="Character with ID " + str(related_character_id) + " not found")
            association = characters.insert().values(scenes=related_character.id, characters=db_scene.id)
            database.execute(association)
    database.commit()
    database.refresh(db_scene)

    related_character_ids = database.query(characters.c["scenes"]).filter(characters.c["characters"] == db_scene.id).all()
    animations_ids = database.query(Animation.id).filter(Animation.scene_id == db_scene.id).all()
    response_data = {
        "scene": db_scene,
        "character_ids": [x[0] for x in related_character_ids],
        "animations_ids": [x[0] for x in animations_ids]    }
    return response_data


def scene_delete_conflict(db_scene, deleting=None, wholes=()):
    """Why this Scene cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_scene)
        deleting = [db_scene] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    if any(whole is db_scene for whole in wholes):
        return "Scene " + str(getattr(db_scene, 'id')) + " is one of its own parts"
    from routers.animation import animation_delete_conflict
    parts_animations = db_scene.animations
    for part in (list(parts_animations) if isinstance(parts_animations, list) else [item for item in [parts_animations] if item is not None]):
        conflict = animation_delete_conflict(part, deleting, wholes + (db_scene,))
        if conflict:
            return "Animation " + str(getattr(part, 'id')) + " would be deleted with it, and " + conflict
    return None


@router.delete("/scene/{scene_id}/", response_model=None, tags=["Scene"])
async def delete_scene(scene_id: int, database: Session = Depends(get_db)):
    db_scene = database.query(Scene).filter(Scene.id == scene_id).first()
    if db_scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    conflict = scene_delete_conflict(db_scene)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete Scene " + str(scene_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_scene = {
        attr.key: getattr(db_scene, attr.key)
        for attr in db_scene.__mapper__.column_attrs
    }
    database.delete(db_scene)
    database.commit()
    return deleted_scene

@router.post("/scene/{scene_id}/scenes/{character_id}/", response_model=None, tags=["Scene Relationships"])
async def add_scenes_to_scene(scene_id: int, character_id: int, database: Session = Depends(get_db)):
    """Add a Character to this Scene's scenes relationship"""
    db_scene = database.query(Scene).filter(Scene.id == scene_id).first()
    if db_scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    related_character = database.query(Character).filter(Character.id == character_id).first()
    if related_character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    # Check if relationship already exists
    existing = database.query(characters).filter(
        (characters.c["characters"] == scene_id) &
        (characters.c["scenes"] == character_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")

    # Create the association
    association = characters.insert().values(characters=scene_id, scenes=character_id)
    database.execute(association)
    database.commit()

    return {"message": "Character added to scenes successfully"}


@router.delete("/scene/{scene_id}/scenes/{character_id}/", response_model=None, tags=["Scene Relationships"])
async def remove_scenes_from_scene(scene_id: int, character_id: int, database: Session = Depends(get_db)):
    """Remove a Character from this Scene's scenes relationship"""
    db_scene = database.query(Scene).filter(Scene.id == scene_id).first()
    if db_scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Check if relationship exists
    existing = database.query(characters).filter(
        (characters.c["characters"] == scene_id) &
        (characters.c["scenes"] == character_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")


    # Delete the association
    association = characters.delete().where(
        (characters.c["characters"] == scene_id) &
        (characters.c["scenes"] == character_id)
    )
    database.execute(association)
    database.commit()

    return {"message": "Character removed from scenes successfully"}


@router.get("/scene/{scene_id}/scenes/", response_model=None, tags=["Scene Relationships"])
async def get_scenes_of_scene(scene_id: int, database: Session = Depends(get_db)):
    """Get all Character entities related to this Scene through scenes"""
    db_scene = database.query(Scene).filter(Scene.id == scene_id).first()
    if db_scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    related_character_ids = database.query(characters.c["scenes"]).filter(characters.c["characters"] == scene_id).all()
    related_character_list = database.query(Character).filter(Character.id.in_([id[0] for id in related_character_ids])).all()

    return {
        "scene_id": scene_id,
        "scenes_count": len(related_character_list),
        "scenes": related_character_list
    }


@router.get("/scene/{scene_id}/animations/", response_model=None, tags=["Scene Relationships"])
async def get_animations_of_scene(scene_id: int, database: Session = Depends(get_db)):
    """Get all Animation entities related to this Scene through animations"""
    db_scene = database.query(Scene).filter(Scene.id == scene_id).first()
    if db_scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    animations_list = database.query(Animation).filter(Animation.scene_id == scene_id).all()

    return {
        "scene_id": scene_id,
        "animations_count": len(animations_list),
        "animations": animations_list
    }


