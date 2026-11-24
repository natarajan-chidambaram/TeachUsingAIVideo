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


@router.get("/subtitle/", response_model=None, tags=["Subtitle"])
def get_all_subtitle(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Subtitle)
        subtitle_list = query.all()

        # Serialize with relationships included
        result = []
        for db_subtitle in subtitle_list:
            item_dict = db_subtitle.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)

            # Add many-to-many and one-to-many relationship objects (full details)
            related_video_list = database.query(Video).join(subtitlevideo, Video.id == subtitlevideo.c["subtitleVideo"]).filter(subtitlevideo.c["subtitles"] == db_subtitle.id).all()
            item_dict['subtitleVideo'] = []
            for related_video_obj in related_video_list:
                related_video_dict = related_video_obj.__dict__.copy()
                related_video_dict.pop('_sa_instance_state', None)
                item_dict['subtitleVideo'].append(related_video_dict)
            related_playersettings_list = database.query(PlayerSettings).filter(PlayerSettings.activeSubtitle_id == db_subtitle.id).all()
            item_dict['playerSettings'] = []
            for related_playersettings_obj in related_playersettings_list:
                related_playersettings_dict = related_playersettings_obj.__dict__.copy()
                related_playersettings_dict.pop('_sa_instance_state', None)
                item_dict['playerSettings'].append(related_playersettings_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Subtitle).all()


@router.get("/subtitle/count/", response_model=None, tags=["Subtitle"])
def get_count_subtitle(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Subtitle entities"""
    count = database.query(Subtitle).count()
    return {"count": count}


@router.get("/subtitle/paginated/", response_model=None, tags=["Subtitle"])
def get_paginated_subtitle(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Subtitle entities"""
    total = database.query(Subtitle).count()
    subtitle_list = database.query(Subtitle).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": subtitle_list
        }

    result = []
    for db_subtitle in subtitle_list:
        related_video_ids = database.query(subtitlevideo.c["subtitleVideo"]).filter(subtitlevideo.c["subtitles"] == db_subtitle.id).all()
        playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.activeSubtitle_id == db_subtitle.id).all()
        item_data = {
            "subtitle": db_subtitle,
            "video_ids": [x[0] for x in related_video_ids],
            "playerSettings_ids": [x[0] for x in playerSettings_ids]        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/subtitle/search/", response_model=None, tags=["Subtitle"])
def search_subtitle(
    fileUrl: str = None,
    format: str = None,
    isEnabledByDefault: bool = None,
    languageCode: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Subtitle entities by attributes"""
    query = database.query(Subtitle)

    if fileUrl is not None:
        query = query.filter(Subtitle.fileUrl.ilike(f"%{fileUrl}%"))
    if format is not None:
        query = query.filter(Subtitle.format.ilike(f"%{format}%"))
    if isEnabledByDefault is not None:
        query = query.filter(Subtitle.isEnabledByDefault == isEnabledByDefault)
    if languageCode is not None:
        query = query.filter(Subtitle.languageCode.ilike(f"%{languageCode}%"))

    results = query.all()
    return results


@router.get("/subtitle/{subtitle_id}/", response_model=None, tags=["Subtitle"])
async def get_subtitle(subtitle_id: int, database: Session = Depends(get_db)) -> Subtitle:
    db_subtitle = database.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if db_subtitle is None:
        raise HTTPException(status_code=404, detail="Subtitle not found")

    related_video_ids = database.query(subtitlevideo.c["subtitleVideo"]).filter(subtitlevideo.c["subtitles"] == db_subtitle.id).all()
    playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.activeSubtitle_id == db_subtitle.id).all()
    response_data = {
        "subtitle": db_subtitle,
        "video_ids": [x[0] for x in related_video_ids],
        "playerSettings_ids": [x[0] for x in playerSettings_ids]}
    return response_data



@router.post("/subtitle/", response_model=None, tags=["Subtitle"])
async def create_subtitle(subtitle_data: SubtitleCreate, database: Session = Depends(get_db)) -> Subtitle:

    if subtitle_data.subtitleVideo:
        for id in subtitle_data.subtitleVideo:
            # Entity already validated before creation
            related_video = database.query(Video).filter(Video.id == id).first()
            if not related_video:
                raise HTTPException(status_code=404, detail=f"Video with ID {id} not found")

    db_subtitle = Subtitle(
        fileUrl=subtitle_data.fileUrl,        format=subtitle_data.format,        isEnabledByDefault=subtitle_data.isEnabledByDefault,        languageCode=subtitle_data.languageCode        )

    database.add(db_subtitle)
    database.flush()
    database.refresh(db_subtitle)

    if subtitle_data.playerSettings:
        # Validate that all PlayerSettings IDs exist
        for related_playersettings_id in subtitle_data.playerSettings:
            related_playersettings = database.query(PlayerSettings).filter(PlayerSettings.id == related_playersettings_id).first()
            if not related_playersettings:
                raise HTTPException(status_code=400, detail=f"PlayerSettings with id {related_playersettings_id} not found")

        # Update the related entities with the new foreign key
        database.query(PlayerSettings).filter(PlayerSettings.id.in_(subtitle_data.playerSettings)).update(
            {PlayerSettings.activeSubtitle_id: db_subtitle.id}, synchronize_session=False
        )
        database.flush()


    if subtitle_data.subtitleVideo:
        for id in subtitle_data.subtitleVideo:
            # Entity already validated before creation
            related_video = database.query(Video).filter(Video.id == id).first()
            # Create the association
            association = subtitlevideo.insert().values(subtitles=db_subtitle.id, subtitleVideo=related_video.id)
            database.execute(association)
            database.flush()


    related_video_ids = database.query(subtitlevideo.c["subtitleVideo"]).filter(subtitlevideo.c["subtitles"] == db_subtitle.id).all()
    playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.activeSubtitle_id == db_subtitle.id).all()
    response_data = {
        "subtitle": db_subtitle,
        "video_ids": [x[0] for x in related_video_ids],
        "playerSettings_ids": [x[0] for x in playerSettings_ids]    }
    database.commit()
    database.refresh(db_subtitle)
    return response_data


@router.post("/subtitle/bulk/", response_model=None, tags=["Subtitle"])
async def bulk_create_subtitle(items: list[SubtitleCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Subtitle entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['subtitleVideo', 'playerSettings']):
        raise HTTPException(status_code=422, detail="Bulk creation of Subtitle with relationships is not supported; use POST /subtitle/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_subtitle = Subtitle(
                fileUrl=item_data.fileUrl,                format=item_data.format,                isEnabledByDefault=item_data.isEnabledByDefault,                languageCode=item_data.languageCode            )
            database.add(db_subtitle)
            database.flush()  # Get ID without committing
            created_items.append(db_subtitle.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of Subtitle failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Subtitle entities"
    }


@router.delete("/subtitle/bulk/", response_model=None, tags=["Subtitle"])
async def bulk_delete_subtitle(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Subtitle entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_subtitle = database.query(Subtitle).filter(Subtitle.id == item_id).first()
        if db_subtitle:
            conflict = subtitle_delete_conflict(db_subtitle)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete Subtitle " + str(item_id) + ": " + conflict)
            database.delete(db_subtitle)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Subtitle entities"
    }

@router.put("/subtitle/{subtitle_id}/", response_model=None, tags=["Subtitle"])
async def update_subtitle(subtitle_id: int, subtitle_data: SubtitleCreate, database: Session = Depends(get_db)) -> Subtitle:
    db_subtitle = database.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if db_subtitle is None:
        raise HTTPException(status_code=404, detail="Subtitle not found")

    setattr(db_subtitle, 'fileUrl', subtitle_data.fileUrl)
    setattr(db_subtitle, 'format', subtitle_data.format)
    setattr(db_subtitle, 'isEnabledByDefault', subtitle_data.isEnabledByDefault)
    setattr(db_subtitle, 'languageCode', subtitle_data.languageCode)
    if subtitle_data.playerSettings is not None:
        requested_playerSettings = set(subtitle_data.playerSettings)
        current_playerSettings = {
            getattr(item, 'id')
            for item in database.query(PlayerSettings).filter(PlayerSettings.activeSubtitle_id == db_subtitle.id).all()
        }
        playerSettings_to_detach = current_playerSettings - requested_playerSettings
        if playerSettings_to_detach:
            database.query(PlayerSettings).filter(PlayerSettings.id.in_(playerSettings_to_detach)).update(
                {PlayerSettings.activeSubtitle_id: None}, synchronize_session=False
            )
        playerSettings_to_attach = requested_playerSettings - current_playerSettings
        for related_playersettings_id in playerSettings_to_attach:
            related_playersettings = database.query(PlayerSettings).filter(PlayerSettings.id == related_playersettings_id).first()
            if not related_playersettings:
                raise HTTPException(status_code=400, detail="PlayerSettings with id " + str(related_playersettings_id) + " not found")
        if playerSettings_to_attach:
            database.query(PlayerSettings).filter(PlayerSettings.id.in_(playerSettings_to_attach)).update(
                {PlayerSettings.activeSubtitle_id: db_subtitle.id}, synchronize_session=False
            )
    if subtitle_data.subtitleVideo is not None:
        existing_related_video_ids = [assoc._mapping["subtitleVideo"] for assoc in database.execute(
            subtitlevideo.select().where(subtitlevideo.c["subtitles"] == db_subtitle.id))]

        related_videos_to_remove = set(existing_related_video_ids) - set(subtitle_data.subtitleVideo)
        for related_video_id in related_videos_to_remove:
            association = subtitlevideo.delete().where(
                (subtitlevideo.c["subtitles"] == db_subtitle.id) & (subtitlevideo.c["subtitleVideo"] == related_video_id))
            database.execute(association)

        new_related_video_ids = set(subtitle_data.subtitleVideo) - set(existing_related_video_ids)
        for related_video_id in new_related_video_ids:
            related_video = database.query(Video).filter(Video.id == related_video_id).first()
            if related_video is None:
                raise HTTPException(status_code=404, detail="Video with ID " + str(related_video_id) + " not found")
            association = subtitlevideo.insert().values(subtitleVideo=related_video.id, subtitles=db_subtitle.id)
            database.execute(association)
    database.commit()
    database.refresh(db_subtitle)

    related_video_ids = database.query(subtitlevideo.c["subtitleVideo"]).filter(subtitlevideo.c["subtitles"] == db_subtitle.id).all()
    playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.activeSubtitle_id == db_subtitle.id).all()
    response_data = {
        "subtitle": db_subtitle,
        "video_ids": [x[0] for x in related_video_ids],
        "playerSettings_ids": [x[0] for x in playerSettings_ids]    }
    return response_data


def subtitle_delete_conflict(db_subtitle, deleting=None, wholes=()):
    """Why this Subtitle cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_subtitle)
        deleting = [db_subtitle] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    return None


@router.delete("/subtitle/{subtitle_id}/", response_model=None, tags=["Subtitle"])
async def delete_subtitle(subtitle_id: int, database: Session = Depends(get_db)):
    db_subtitle = database.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if db_subtitle is None:
        raise HTTPException(status_code=404, detail="Subtitle not found")
    conflict = subtitle_delete_conflict(db_subtitle)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete Subtitle " + str(subtitle_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_subtitle = {
        attr.key: getattr(db_subtitle, attr.key)
        for attr in db_subtitle.__mapper__.column_attrs
    }
    database.delete(db_subtitle)
    database.commit()
    return deleted_subtitle

@router.post("/subtitle/{subtitle_id}/subtitleVideo/{video_id}/", response_model=None, tags=["Subtitle Relationships"])
async def add_subtitleVideo_to_subtitle(subtitle_id: int, video_id: int, database: Session = Depends(get_db)):
    """Add a Video to this Subtitle's subtitleVideo relationship"""
    db_subtitle = database.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if db_subtitle is None:
        raise HTTPException(status_code=404, detail="Subtitle not found")

    related_video = database.query(Video).filter(Video.id == video_id).first()
    if related_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check if relationship already exists
    existing = database.query(subtitlevideo).filter(
        (subtitlevideo.c["subtitles"] == subtitle_id) &
        (subtitlevideo.c["subtitleVideo"] == video_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")

    # Create the association
    association = subtitlevideo.insert().values(subtitles=subtitle_id, subtitleVideo=video_id)
    database.execute(association)
    database.commit()

    return {"message": "Video added to subtitleVideo successfully"}


@router.delete("/subtitle/{subtitle_id}/subtitleVideo/{video_id}/", response_model=None, tags=["Subtitle Relationships"])
async def remove_subtitleVideo_from_subtitle(subtitle_id: int, video_id: int, database: Session = Depends(get_db)):
    """Remove a Video from this Subtitle's subtitleVideo relationship"""
    db_subtitle = database.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if db_subtitle is None:
        raise HTTPException(status_code=404, detail="Subtitle not found")

    # Check if relationship exists
    existing = database.query(subtitlevideo).filter(
        (subtitlevideo.c["subtitles"] == subtitle_id) &
        (subtitlevideo.c["subtitleVideo"] == video_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")


    # Delete the association
    association = subtitlevideo.delete().where(
        (subtitlevideo.c["subtitles"] == subtitle_id) &
        (subtitlevideo.c["subtitleVideo"] == video_id)
    )
    database.execute(association)
    database.commit()

    return {"message": "Video removed from subtitleVideo successfully"}


@router.get("/subtitle/{subtitle_id}/subtitleVideo/", response_model=None, tags=["Subtitle Relationships"])
async def get_subtitleVideo_of_subtitle(subtitle_id: int, database: Session = Depends(get_db)):
    """Get all Video entities related to this Subtitle through subtitleVideo"""
    db_subtitle = database.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if db_subtitle is None:
        raise HTTPException(status_code=404, detail="Subtitle not found")

    related_video_ids = database.query(subtitlevideo.c["subtitleVideo"]).filter(subtitlevideo.c["subtitles"] == subtitle_id).all()
    related_video_list = database.query(Video).filter(Video.id.in_([id[0] for id in related_video_ids])).all()

    return {
        "subtitle_id": subtitle_id,
        "subtitleVideo_count": len(related_video_list),
        "subtitleVideo": related_video_list
    }


@router.get("/subtitle/{subtitle_id}/playerSettings/", response_model=None, tags=["Subtitle Relationships"])
async def get_playerSettings_of_subtitle(subtitle_id: int, database: Session = Depends(get_db)):
    """Get all PlayerSettings entities related to this Subtitle through playerSettings"""
    db_subtitle = database.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if db_subtitle is None:
        raise HTTPException(status_code=404, detail="Subtitle not found")

    playerSettings_list = database.query(PlayerSettings).filter(PlayerSettings.activeSubtitle_id == subtitle_id).all()

    return {
        "subtitle_id": subtitle_id,
        "playerSettings_count": len(playerSettings_list),
        "playerSettings": playerSettings_list
    }


