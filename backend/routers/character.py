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


@router.get("/character/", response_model=None, tags=["Character"])
def get_all_character(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Character)
        character_list = query.all()

        # Serialize with relationships included
        result = []
        for db_character in character_list:
            item_dict = db_character.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)

            # Add many-to-many and one-to-many relationship objects (full details)
            related_scene_list = database.query(Scene).join(characters, Scene.id == characters.c["characters"]).filter(characters.c["scenes"] == db_character.id).all()
            item_dict['characters'] = []
            for related_scene_obj in related_scene_list:
                related_scene_dict = related_scene_obj.__dict__.copy()
                related_scene_dict.pop('_sa_instance_state', None)
                item_dict['characters'].append(related_scene_dict)
            related_animation_list = database.query(Animation).filter(Animation.targetCharacter_id == db_character.id).all()
            item_dict['animations'] = []
            for related_animation_obj in related_animation_list:
                related_animation_dict = related_animation_obj.__dict__.copy()
                related_animation_dict.pop('_sa_instance_state', None)
                item_dict['animations'].append(related_animation_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Character).all()


@router.get("/character/count/", response_model=None, tags=["Character"])
def get_count_character(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Character entities"""
    count = database.query(Character).count()
    return {"count": count}


@router.get("/character/paginated/", response_model=None, tags=["Character"])
def get_paginated_character(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Character entities"""
    total = database.query(Character).count()
    character_list = database.query(Character).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": character_list
        }

    result = []
    for db_character in character_list:
        related_scene_ids = database.query(characters.c["characters"]).filter(characters.c["scenes"] == db_character.id).all()
        animations_ids = database.query(Animation.id).filter(Animation.targetCharacter_id == db_character.id).all()
        item_data = {
            "character": db_character,
            "scene_ids": [x[0] for x in related_scene_ids],
            "animations_ids": [x[0] for x in animations_ids]        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/character/search/", response_model=None, tags=["Character"])
def search_character(
    avatarImageUrl: str = None,
    name: str = None,
    role: str = None,
    voiceActor: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Character entities by attributes"""
    query = database.query(Character)

    if avatarImageUrl is not None:
        query = query.filter(Character.avatarImageUrl.ilike(f"%{avatarImageUrl}%"))
    if name is not None:
        query = query.filter(Character.name.ilike(f"%{name}%"))
    if role is not None:
        query = query.filter(Character.role.ilike(f"%{role}%"))
    if voiceActor is not None:
        query = query.filter(Character.voiceActor.ilike(f"%{voiceActor}%"))

    results = query.all()
    return results


@router.get("/character/{character_id}/", response_model=None, tags=["Character"])
async def get_character(character_id: int, database: Session = Depends(get_db)) -> Character:
    db_character = database.query(Character).filter(Character.id == character_id).first()
    if db_character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    related_scene_ids = database.query(characters.c["characters"]).filter(characters.c["scenes"] == db_character.id).all()
    animations_ids = database.query(Animation.id).filter(Animation.targetCharacter_id == db_character.id).all()
    response_data = {
        "character": db_character,
        "scene_ids": [x[0] for x in related_scene_ids],
        "animations_ids": [x[0] for x in animations_ids]}
    return response_data



@router.post("/character/", response_model=None, tags=["Character"])
async def create_character(character_data: CharacterCreate, database: Session = Depends(get_db)) -> Character:

    if character_data.characters:
        for id in character_data.characters:
            # Entity already validated before creation
            related_scene = database.query(Scene).filter(Scene.id == id).first()
            if not related_scene:
                raise HTTPException(status_code=404, detail=f"Scene with ID {id} not found")

    db_character = Character(
        avatarImageUrl=character_data.avatarImageUrl,        name=character_data.name,        role=character_data.role,        voiceActor=character_data.voiceActor        )

    database.add(db_character)
    database.flush()
    database.refresh(db_character)

    if character_data.animations:
        # Validate that all Animation IDs exist
        for related_animation_id in character_data.animations:
            related_animation = database.query(Animation).filter(Animation.id == related_animation_id).first()
            if not related_animation:
                raise HTTPException(status_code=400, detail=f"Animation with id {related_animation_id} not found")

        # Update the related entities with the new foreign key
        database.query(Animation).filter(Animation.id.in_(character_data.animations)).update(
            {Animation.targetCharacter_id: db_character.id}, synchronize_session=False
        )
        database.flush()


    if character_data.characters:
        for id in character_data.characters:
            # Entity already validated before creation
            related_scene = database.query(Scene).filter(Scene.id == id).first()
            # Create the association
            association = characters.insert().values(scenes=db_character.id, characters=related_scene.id)
            database.execute(association)
            database.flush()


    related_scene_ids = database.query(characters.c["characters"]).filter(characters.c["scenes"] == db_character.id).all()
    animations_ids = database.query(Animation.id).filter(Animation.targetCharacter_id == db_character.id).all()
    response_data = {
        "character": db_character,
        "scene_ids": [x[0] for x in related_scene_ids],
        "animations_ids": [x[0] for x in animations_ids]    }
    database.commit()
    database.refresh(db_character)
    return response_data


@router.post("/character/bulk/", response_model=None, tags=["Character"])
async def bulk_create_character(items: list[CharacterCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Character entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['characters', 'animations']):
        raise HTTPException(status_code=422, detail="Bulk creation of Character with relationships is not supported; use POST /character/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_character = Character(
                avatarImageUrl=item_data.avatarImageUrl,                name=item_data.name,                role=item_data.role,                voiceActor=item_data.voiceActor            )
            database.add(db_character)
            database.flush()  # Get ID without committing
            created_items.append(db_character.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of Character failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Character entities"
    }


@router.delete("/character/bulk/", response_model=None, tags=["Character"])
async def bulk_delete_character(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Character entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_character = database.query(Character).filter(Character.id == item_id).first()
        if db_character:
            conflict = character_delete_conflict(db_character)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete Character " + str(item_id) + ": " + conflict)
            database.delete(db_character)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Character entities"
    }

@router.put("/character/{character_id}/", response_model=None, tags=["Character"])
async def update_character(character_id: int, character_data: CharacterCreate, database: Session = Depends(get_db)) -> Character:
    db_character = database.query(Character).filter(Character.id == character_id).first()
    if db_character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    setattr(db_character, 'avatarImageUrl', character_data.avatarImageUrl)
    setattr(db_character, 'name', character_data.name)
    setattr(db_character, 'role', character_data.role)
    setattr(db_character, 'voiceActor', character_data.voiceActor)
    if character_data.animations is not None:
        requested_animations = set(character_data.animations)
        current_animations = {
            getattr(item, 'id')
            for item in database.query(Animation).filter(Animation.targetCharacter_id == db_character.id).all()
        }
        animations_to_detach = current_animations - requested_animations
        if animations_to_detach:
            database.query(Animation).filter(Animation.id.in_(animations_to_detach)).update(
                {Animation.targetCharacter_id: None}, synchronize_session=False
            )
        animations_to_attach = requested_animations - current_animations
        for related_animation_id in animations_to_attach:
            related_animation = database.query(Animation).filter(Animation.id == related_animation_id).first()
            if not related_animation:
                raise HTTPException(status_code=400, detail="Animation with id " + str(related_animation_id) + " not found")
        if animations_to_attach:
            database.query(Animation).filter(Animation.id.in_(animations_to_attach)).update(
                {Animation.targetCharacter_id: db_character.id}, synchronize_session=False
            )
    if character_data.characters is not None:
        existing_related_scene_ids = [assoc._mapping["characters"] for assoc in database.execute(
            characters.select().where(characters.c["scenes"] == db_character.id))]

        related_scenes_to_remove = set(existing_related_scene_ids) - set(character_data.characters)
        for related_scene_id in related_scenes_to_remove:
            association = characters.delete().where(
                (characters.c["scenes"] == db_character.id) & (characters.c["characters"] == related_scene_id))
            database.execute(association)

        new_related_scene_ids = set(character_data.characters) - set(existing_related_scene_ids)
        for related_scene_id in new_related_scene_ids:
            related_scene = database.query(Scene).filter(Scene.id == related_scene_id).first()
            if related_scene is None:
                raise HTTPException(status_code=404, detail="Scene with ID " + str(related_scene_id) + " not found")
            association = characters.insert().values(characters=related_scene.id, scenes=db_character.id)
            database.execute(association)
    database.commit()
    database.refresh(db_character)

    related_scene_ids = database.query(characters.c["characters"]).filter(characters.c["scenes"] == db_character.id).all()
    animations_ids = database.query(Animation.id).filter(Animation.targetCharacter_id == db_character.id).all()
    response_data = {
        "character": db_character,
        "scene_ids": [x[0] for x in related_scene_ids],
        "animations_ids": [x[0] for x in animations_ids]    }
    return response_data


def character_delete_conflict(db_character, deleting=None, wholes=()):
    """Why this Character cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_character)
        deleting = [db_character] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    return None


@router.delete("/character/{character_id}/", response_model=None, tags=["Character"])
async def delete_character(character_id: int, database: Session = Depends(get_db)):
    db_character = database.query(Character).filter(Character.id == character_id).first()
    if db_character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    conflict = character_delete_conflict(db_character)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete Character " + str(character_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_character = {
        attr.key: getattr(db_character, attr.key)
        for attr in db_character.__mapper__.column_attrs
    }
    database.delete(db_character)
    database.commit()
    return deleted_character

@router.post("/character/{character_id}/characters/{scene_id}/", response_model=None, tags=["Character Relationships"])
async def add_characters_to_character(character_id: int, scene_id: int, database: Session = Depends(get_db)):
    """Add a Scene to this Character's characters relationship"""
    db_character = database.query(Character).filter(Character.id == character_id).first()
    if db_character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    related_scene = database.query(Scene).filter(Scene.id == scene_id).first()
    if related_scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Check if relationship already exists
    existing = database.query(characters).filter(
        (characters.c["scenes"] == character_id) &
        (characters.c["characters"] == scene_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")

    # Create the association
    association = characters.insert().values(scenes=character_id, characters=scene_id)
    database.execute(association)
    database.commit()

    return {"message": "Scene added to characters successfully"}


@router.delete("/character/{character_id}/characters/{scene_id}/", response_model=None, tags=["Character Relationships"])
async def remove_characters_from_character(character_id: int, scene_id: int, database: Session = Depends(get_db)):
    """Remove a Scene from this Character's characters relationship"""
    db_character = database.query(Character).filter(Character.id == character_id).first()
    if db_character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    # Check if relationship exists
    existing = database.query(characters).filter(
        (characters.c["scenes"] == character_id) &
        (characters.c["characters"] == scene_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")


    # Delete the association
    association = characters.delete().where(
        (characters.c["scenes"] == character_id) &
        (characters.c["characters"] == scene_id)
    )
    database.execute(association)
    database.commit()

    return {"message": "Scene removed from characters successfully"}


@router.get("/character/{character_id}/characters/", response_model=None, tags=["Character Relationships"])
async def get_characters_of_character(character_id: int, database: Session = Depends(get_db)):
    """Get all Scene entities related to this Character through characters"""
    db_character = database.query(Character).filter(Character.id == character_id).first()
    if db_character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    related_scene_ids = database.query(characters.c["characters"]).filter(characters.c["scenes"] == character_id).all()
    related_scene_list = database.query(Scene).filter(Scene.id.in_([id[0] for id in related_scene_ids])).all()

    return {
        "character_id": character_id,
        "characters_count": len(related_scene_list),
        "characters": related_scene_list
    }


@router.get("/character/{character_id}/animations/", response_model=None, tags=["Character Relationships"])
async def get_animations_of_character(character_id: int, database: Session = Depends(get_db)):
    """Get all Animation entities related to this Character through animations"""
    db_character = database.query(Character).filter(Character.id == character_id).first()
    if db_character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    animations_list = database.query(Animation).filter(Animation.targetCharacter_id == character_id).all()

    return {
        "character_id": character_id,
        "animations_count": len(animations_list),
        "animations": animations_list
    }


