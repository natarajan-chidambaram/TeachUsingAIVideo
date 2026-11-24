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


@router.get("/playersettings/", response_model=None, tags=["PlayerSettings"])
def get_all_playersettings(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(PlayerSettings)
        query = query.options(joinedload(PlayerSettings.activeAudioTrack))
        query = query.options(joinedload(PlayerSettings.activeSubtitle))
        query = query.options(joinedload(PlayerSettings.currentVideo))
        playersettings_list = query.all()

        # Serialize with relationships included
        result = []
        for db_playersettings in playersettings_list:
            item_dict = db_playersettings.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)
            if db_playersettings.activeAudioTrack:
                related_obj = db_playersettings.activeAudioTrack
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['activeAudioTrack'] = related_dict
            else:
                item_dict['activeAudioTrack'] = None
            if db_playersettings.activeSubtitle:
                related_obj = db_playersettings.activeSubtitle
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['activeSubtitle'] = related_dict
            else:
                item_dict['activeSubtitle'] = None
            if db_playersettings.currentVideo:
                related_obj = db_playersettings.currentVideo
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['currentVideo'] = related_dict
            else:
                item_dict['currentVideo'] = None


            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(PlayerSettings).all()


@router.get("/playersettings/count/", response_model=None, tags=["PlayerSettings"])
def get_count_playersettings(database: Session = Depends(get_db)) -> dict:
    """Get the total count of PlayerSettings entities"""
    count = database.query(PlayerSettings).count()
    return {"count": count}


@router.get("/playersettings/paginated/", response_model=None, tags=["PlayerSettings"])
def get_paginated_playersettings(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of PlayerSettings entities"""
    total = database.query(PlayerSettings).count()
    playersettings_list = database.query(PlayerSettings).offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": playersettings_list
    }
@router.get("/playersettings/search/", response_model=None, tags=["PlayerSettings"])
def search_playersettings(
    activeLanguageCode: str = None,
    currentTimeSeconds: int = None,
    isFullScreen: bool = None,
    isLooping: bool = None,
    isMuted: bool = None,
    playbackSpeed: float = None,
    volume: float = None,
    database: Session = Depends(get_db)
) -> list:
    """Search PlayerSettings entities by attributes"""
    query = database.query(PlayerSettings)

    if activeLanguageCode is not None:
        query = query.filter(PlayerSettings.activeLanguageCode.ilike(f"%{activeLanguageCode}%"))
    if currentTimeSeconds is not None:
        query = query.filter(PlayerSettings.currentTimeSeconds == currentTimeSeconds)
    if isFullScreen is not None:
        query = query.filter(PlayerSettings.isFullScreen == isFullScreen)
    if isLooping is not None:
        query = query.filter(PlayerSettings.isLooping == isLooping)
    if isMuted is not None:
        query = query.filter(PlayerSettings.isMuted == isMuted)
    if playbackSpeed is not None:
        query = query.filter(PlayerSettings.playbackSpeed == playbackSpeed)
    if volume is not None:
        query = query.filter(PlayerSettings.volume == volume)

    results = query.all()
    return results


@router.get("/playersettings/{playersettings_id}/", response_model=None, tags=["PlayerSettings"])
async def get_playersettings(playersettings_id: int, database: Session = Depends(get_db)) -> PlayerSettings:
    db_playersettings = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if db_playersettings is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")

    response_data = {
        "playersettings": db_playersettings,
}
    return response_data



@router.post("/playersettings/", response_model=None, tags=["PlayerSettings"])
async def create_playersettings(playersettings_data: PlayerSettingsCreate, database: Session = Depends(get_db)) -> PlayerSettings:

    if playersettings_data.activeAudioTrack :
        related_activeAudioTrack = database.query(AudioTrack).filter(AudioTrack.id == playersettings_data.activeAudioTrack).first()
        if not related_activeAudioTrack:
            raise HTTPException(status_code=400, detail="AudioTrack not found")
    if playersettings_data.activeSubtitle :
        related_activeSubtitle = database.query(Subtitle).filter(Subtitle.id == playersettings_data.activeSubtitle).first()
        if not related_activeSubtitle:
            raise HTTPException(status_code=400, detail="Subtitle not found")
    if playersettings_data.currentVideo :
        related_currentVideo = database.query(Video).filter(Video.id == playersettings_data.currentVideo).first()
        if not related_currentVideo:
            raise HTTPException(status_code=400, detail="Video not found")

    db_playersettings = PlayerSettings(
        activeLanguageCode=playersettings_data.activeLanguageCode,        currentTimeSeconds=playersettings_data.currentTimeSeconds,        isFullScreen=playersettings_data.isFullScreen,        isLooping=playersettings_data.isLooping,        isMuted=playersettings_data.isMuted,        playbackSpeed=playersettings_data.playbackSpeed,        volume=playersettings_data.volume,        activeAudioTrack_id=playersettings_data.activeAudioTrack,        activeSubtitle_id=playersettings_data.activeSubtitle,        currentVideo_id=playersettings_data.currentVideo        )

    database.add(db_playersettings)
    database.flush()
    database.refresh(db_playersettings)





    database.commit()
    database.refresh(db_playersettings)
    return db_playersettings


@router.post("/playersettings/bulk/", response_model=None, tags=["PlayerSettings"])
async def bulk_create_playersettings(items: list[PlayerSettingsCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple PlayerSettings entities at once"""
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_playersettings = PlayerSettings(
                activeLanguageCode=item_data.activeLanguageCode,                currentTimeSeconds=item_data.currentTimeSeconds,                isFullScreen=item_data.isFullScreen,                isLooping=item_data.isLooping,                isMuted=item_data.isMuted,                playbackSpeed=item_data.playbackSpeed,                volume=item_data.volume,                activeAudioTrack_id=item_data.activeAudioTrack,                activeSubtitle_id=item_data.activeSubtitle,                currentVideo_id=item_data.currentVideo            )
            database.add(db_playersettings)
            database.flush()  # Get ID without committing
            created_items.append(db_playersettings.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of PlayerSettings failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} PlayerSettings entities"
    }


@router.delete("/playersettings/bulk/", response_model=None, tags=["PlayerSettings"])
async def bulk_delete_playersettings(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple PlayerSettings entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_playersettings = database.query(PlayerSettings).filter(PlayerSettings.id == item_id).first()
        if db_playersettings:
            conflict = playersettings_delete_conflict(db_playersettings)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete PlayerSettings " + str(item_id) + ": " + conflict)
            database.delete(db_playersettings)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} PlayerSettings entities"
    }

@router.put("/playersettings/{playersettings_id}/", response_model=None, tags=["PlayerSettings"])
async def update_playersettings(playersettings_id: int, playersettings_data: PlayerSettingsCreate, database: Session = Depends(get_db)) -> PlayerSettings:
    db_playersettings = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if db_playersettings is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")

    setattr(db_playersettings, 'activeLanguageCode', playersettings_data.activeLanguageCode)
    setattr(db_playersettings, 'currentTimeSeconds', playersettings_data.currentTimeSeconds)
    setattr(db_playersettings, 'isFullScreen', playersettings_data.isFullScreen)
    setattr(db_playersettings, 'isLooping', playersettings_data.isLooping)
    setattr(db_playersettings, 'isMuted', playersettings_data.isMuted)
    setattr(db_playersettings, 'playbackSpeed', playersettings_data.playbackSpeed)
    setattr(db_playersettings, 'volume', playersettings_data.volume)
    if playersettings_data.activeAudioTrack is not None:
        related_activeAudioTrack = database.query(AudioTrack).filter(AudioTrack.id == playersettings_data.activeAudioTrack).first()
        if not related_activeAudioTrack:
            raise HTTPException(status_code=400, detail="AudioTrack not found")
        setattr(db_playersettings, 'activeAudioTrack_id', playersettings_data.activeAudioTrack)
    else:
        setattr(db_playersettings, 'activeAudioTrack_id', None)
    if playersettings_data.activeSubtitle is not None:
        related_activeSubtitle = database.query(Subtitle).filter(Subtitle.id == playersettings_data.activeSubtitle).first()
        if not related_activeSubtitle:
            raise HTTPException(status_code=400, detail="Subtitle not found")
        setattr(db_playersettings, 'activeSubtitle_id', playersettings_data.activeSubtitle)
    else:
        setattr(db_playersettings, 'activeSubtitle_id', None)
    if playersettings_data.currentVideo is not None:
        related_currentVideo = database.query(Video).filter(Video.id == playersettings_data.currentVideo).first()
        if not related_currentVideo:
            raise HTTPException(status_code=400, detail="Video not found")
        setattr(db_playersettings, 'currentVideo_id', playersettings_data.currentVideo)
    else:
        setattr(db_playersettings, 'currentVideo_id', None)
    database.commit()
    database.refresh(db_playersettings)

    return db_playersettings


def playersettings_delete_conflict(db_playersettings, deleting=None, wholes=()):
    """Why this PlayerSettings cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_playersettings)
        deleting = [db_playersettings] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    return None


@router.delete("/playersettings/{playersettings_id}/", response_model=None, tags=["PlayerSettings"])
async def delete_playersettings(playersettings_id: int, database: Session = Depends(get_db)):
    db_playersettings = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if db_playersettings is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    conflict = playersettings_delete_conflict(db_playersettings)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete PlayerSettings " + str(playersettings_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_playersettings = {
        attr.key: getattr(db_playersettings, attr.key)
        for attr in db_playersettings.__mapper__.column_attrs
    }
    database.delete(db_playersettings)
    database.commit()
    return deleted_playersettings



