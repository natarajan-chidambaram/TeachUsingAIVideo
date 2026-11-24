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


@router.get("/audiotrack/", response_model=None, tags=["AudioTrack"])
def get_all_audiotrack(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(AudioTrack)
        audiotrack_list = query.all()

        # Serialize with relationships included
        result = []
        for db_audiotrack in audiotrack_list:
            item_dict = db_audiotrack.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)

            # Add many-to-many and one-to-many relationship objects (full details)
            related_video_list = database.query(Video).join(videos, Video.id == videos.c["videos"]).filter(videos.c["audioTracks"] == db_audiotrack.id).all()
            item_dict['videos'] = []
            for related_video_obj in related_video_list:
                related_video_dict = related_video_obj.__dict__.copy()
                related_video_dict.pop('_sa_instance_state', None)
                item_dict['videos'].append(related_video_dict)
            related_playersettings_list = database.query(PlayerSettings).filter(PlayerSettings.activeAudioTrack_id == db_audiotrack.id).all()
            item_dict['playerSettings'] = []
            for related_playersettings_obj in related_playersettings_list:
                related_playersettings_dict = related_playersettings_obj.__dict__.copy()
                related_playersettings_dict.pop('_sa_instance_state', None)
                item_dict['playerSettings'].append(related_playersettings_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(AudioTrack).all()


@router.get("/audiotrack/count/", response_model=None, tags=["AudioTrack"])
def get_count_audiotrack(database: Session = Depends(get_db)) -> dict:
    """Get the total count of AudioTrack entities"""
    count = database.query(AudioTrack).count()
    return {"count": count}


@router.get("/audiotrack/paginated/", response_model=None, tags=["AudioTrack"])
def get_paginated_audiotrack(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of AudioTrack entities"""
    total = database.query(AudioTrack).count()
    audiotrack_list = database.query(AudioTrack).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": audiotrack_list
        }

    result = []
    for db_audiotrack in audiotrack_list:
        related_video_ids = database.query(videos.c["videos"]).filter(videos.c["audioTracks"] == db_audiotrack.id).all()
        playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.activeAudioTrack_id == db_audiotrack.id).all()
        item_data = {
            "audiotrack": db_audiotrack,
            "video_ids": [x[0] for x in related_video_ids],
            "playerSettings_ids": [x[0] for x in playerSettings_ids]        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/audiotrack/search/", response_model=None, tags=["AudioTrack"])
def search_audiotrack(
    durationSeconds: int = None,
    fileUrl: str = None,
    isDefault: bool = None,
    kind: str = None,
    languageCode: str = None,
    volumeLevelDefault: float = None,
    database: Session = Depends(get_db)
) -> list:
    """Search AudioTrack entities by attributes"""
    query = database.query(AudioTrack)

    if durationSeconds is not None:
        query = query.filter(AudioTrack.durationSeconds == durationSeconds)
    if fileUrl is not None:
        query = query.filter(AudioTrack.fileUrl.ilike(f"%{fileUrl}%"))
    if isDefault is not None:
        query = query.filter(AudioTrack.isDefault == isDefault)
    if kind is not None:
        query = query.filter(AudioTrack.kind.ilike(f"%{kind}%"))
    if languageCode is not None:
        query = query.filter(AudioTrack.languageCode.ilike(f"%{languageCode}%"))
    if volumeLevelDefault is not None:
        query = query.filter(AudioTrack.volumeLevelDefault == volumeLevelDefault)

    results = query.all()
    return results


@router.get("/audiotrack/{audiotrack_id}/", response_model=None, tags=["AudioTrack"])
async def get_audiotrack(audiotrack_id: int, database: Session = Depends(get_db)) -> AudioTrack:
    db_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == audiotrack_id).first()
    if db_audiotrack is None:
        raise HTTPException(status_code=404, detail="AudioTrack not found")

    related_video_ids = database.query(videos.c["videos"]).filter(videos.c["audioTracks"] == db_audiotrack.id).all()
    playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.activeAudioTrack_id == db_audiotrack.id).all()
    response_data = {
        "audiotrack": db_audiotrack,
        "video_ids": [x[0] for x in related_video_ids],
        "playerSettings_ids": [x[0] for x in playerSettings_ids]}
    return response_data



@router.post("/audiotrack/", response_model=None, tags=["AudioTrack"])
async def create_audiotrack(audiotrack_data: AudioTrackCreate, database: Session = Depends(get_db)) -> AudioTrack:

    if audiotrack_data.videos:
        for id in audiotrack_data.videos:
            # Entity already validated before creation
            related_video = database.query(Video).filter(Video.id == id).first()
            if not related_video:
                raise HTTPException(status_code=404, detail=f"Video with ID {id} not found")

    db_audiotrack = AudioTrack(
        durationSeconds=audiotrack_data.durationSeconds,        fileUrl=audiotrack_data.fileUrl,        isDefault=audiotrack_data.isDefault,        kind=audiotrack_data.kind,        languageCode=audiotrack_data.languageCode,        volumeLevelDefault=audiotrack_data.volumeLevelDefault        )

    database.add(db_audiotrack)
    database.flush()
    database.refresh(db_audiotrack)

    if audiotrack_data.playerSettings:
        # Validate that all PlayerSettings IDs exist
        for related_playersettings_id in audiotrack_data.playerSettings:
            related_playersettings = database.query(PlayerSettings).filter(PlayerSettings.id == related_playersettings_id).first()
            if not related_playersettings:
                raise HTTPException(status_code=400, detail=f"PlayerSettings with id {related_playersettings_id} not found")

        # Update the related entities with the new foreign key
        database.query(PlayerSettings).filter(PlayerSettings.id.in_(audiotrack_data.playerSettings)).update(
            {PlayerSettings.activeAudioTrack_id: db_audiotrack.id}, synchronize_session=False
        )
        database.flush()


    if audiotrack_data.videos:
        for id in audiotrack_data.videos:
            # Entity already validated before creation
            related_video = database.query(Video).filter(Video.id == id).first()
            # Create the association
            association = videos.insert().values(audioTracks=db_audiotrack.id, videos=related_video.id)
            database.execute(association)
            database.flush()


    related_video_ids = database.query(videos.c["videos"]).filter(videos.c["audioTracks"] == db_audiotrack.id).all()
    playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.activeAudioTrack_id == db_audiotrack.id).all()
    response_data = {
        "audiotrack": db_audiotrack,
        "video_ids": [x[0] for x in related_video_ids],
        "playerSettings_ids": [x[0] for x in playerSettings_ids]    }
    database.commit()
    database.refresh(db_audiotrack)
    return response_data


@router.post("/audiotrack/bulk/", response_model=None, tags=["AudioTrack"])
async def bulk_create_audiotrack(items: list[AudioTrackCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple AudioTrack entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['videos', 'playerSettings']):
        raise HTTPException(status_code=422, detail="Bulk creation of AudioTrack with relationships is not supported; use POST /audiotrack/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_audiotrack = AudioTrack(
                durationSeconds=item_data.durationSeconds,                fileUrl=item_data.fileUrl,                isDefault=item_data.isDefault,                kind=item_data.kind,                languageCode=item_data.languageCode,                volumeLevelDefault=item_data.volumeLevelDefault            )
            database.add(db_audiotrack)
            database.flush()  # Get ID without committing
            created_items.append(db_audiotrack.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of AudioTrack failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} AudioTrack entities"
    }


@router.delete("/audiotrack/bulk/", response_model=None, tags=["AudioTrack"])
async def bulk_delete_audiotrack(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple AudioTrack entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == item_id).first()
        if db_audiotrack:
            conflict = audiotrack_delete_conflict(db_audiotrack)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete AudioTrack " + str(item_id) + ": " + conflict)
            database.delete(db_audiotrack)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} AudioTrack entities"
    }

@router.put("/audiotrack/{audiotrack_id}/", response_model=None, tags=["AudioTrack"])
async def update_audiotrack(audiotrack_id: int, audiotrack_data: AudioTrackCreate, database: Session = Depends(get_db)) -> AudioTrack:
    db_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == audiotrack_id).first()
    if db_audiotrack is None:
        raise HTTPException(status_code=404, detail="AudioTrack not found")

    setattr(db_audiotrack, 'durationSeconds', audiotrack_data.durationSeconds)
    setattr(db_audiotrack, 'fileUrl', audiotrack_data.fileUrl)
    setattr(db_audiotrack, 'isDefault', audiotrack_data.isDefault)
    setattr(db_audiotrack, 'kind', audiotrack_data.kind)
    setattr(db_audiotrack, 'languageCode', audiotrack_data.languageCode)
    setattr(db_audiotrack, 'volumeLevelDefault', audiotrack_data.volumeLevelDefault)
    if audiotrack_data.playerSettings is not None:
        requested_playerSettings = set(audiotrack_data.playerSettings)
        current_playerSettings = {
            getattr(item, 'id')
            for item in database.query(PlayerSettings).filter(PlayerSettings.activeAudioTrack_id == db_audiotrack.id).all()
        }
        playerSettings_to_detach = current_playerSettings - requested_playerSettings
        if playerSettings_to_detach:
            database.query(PlayerSettings).filter(PlayerSettings.id.in_(playerSettings_to_detach)).update(
                {PlayerSettings.activeAudioTrack_id: None}, synchronize_session=False
            )
        playerSettings_to_attach = requested_playerSettings - current_playerSettings
        for related_playersettings_id in playerSettings_to_attach:
            related_playersettings = database.query(PlayerSettings).filter(PlayerSettings.id == related_playersettings_id).first()
            if not related_playersettings:
                raise HTTPException(status_code=400, detail="PlayerSettings with id " + str(related_playersettings_id) + " not found")
        if playerSettings_to_attach:
            database.query(PlayerSettings).filter(PlayerSettings.id.in_(playerSettings_to_attach)).update(
                {PlayerSettings.activeAudioTrack_id: db_audiotrack.id}, synchronize_session=False
            )
    if audiotrack_data.videos is not None:
        existing_related_video_ids = [assoc._mapping["videos"] for assoc in database.execute(
            videos.select().where(videos.c["audioTracks"] == db_audiotrack.id))]

        related_videos_to_remove = set(existing_related_video_ids) - set(audiotrack_data.videos)
        for related_video_id in related_videos_to_remove:
            association = videos.delete().where(
                (videos.c["audioTracks"] == db_audiotrack.id) & (videos.c["videos"] == related_video_id))
            database.execute(association)

        new_related_video_ids = set(audiotrack_data.videos) - set(existing_related_video_ids)
        for related_video_id in new_related_video_ids:
            related_video = database.query(Video).filter(Video.id == related_video_id).first()
            if related_video is None:
                raise HTTPException(status_code=404, detail="Video with ID " + str(related_video_id) + " not found")
            association = videos.insert().values(videos=related_video.id, audioTracks=db_audiotrack.id)
            database.execute(association)
    database.commit()
    database.refresh(db_audiotrack)

    related_video_ids = database.query(videos.c["videos"]).filter(videos.c["audioTracks"] == db_audiotrack.id).all()
    playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.activeAudioTrack_id == db_audiotrack.id).all()
    response_data = {
        "audiotrack": db_audiotrack,
        "video_ids": [x[0] for x in related_video_ids],
        "playerSettings_ids": [x[0] for x in playerSettings_ids]    }
    return response_data


def audiotrack_delete_conflict(db_audiotrack, deleting=None, wholes=()):
    """Why this AudioTrack cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_audiotrack)
        deleting = [db_audiotrack] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    return None


@router.delete("/audiotrack/{audiotrack_id}/", response_model=None, tags=["AudioTrack"])
async def delete_audiotrack(audiotrack_id: int, database: Session = Depends(get_db)):
    db_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == audiotrack_id).first()
    if db_audiotrack is None:
        raise HTTPException(status_code=404, detail="AudioTrack not found")
    conflict = audiotrack_delete_conflict(db_audiotrack)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete AudioTrack " + str(audiotrack_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_audiotrack = {
        attr.key: getattr(db_audiotrack, attr.key)
        for attr in db_audiotrack.__mapper__.column_attrs
    }
    database.delete(db_audiotrack)
    database.commit()
    return deleted_audiotrack

@router.post("/audiotrack/{audiotrack_id}/videos/{video_id}/", response_model=None, tags=["AudioTrack Relationships"])
async def add_videos_to_audiotrack(audiotrack_id: int, video_id: int, database: Session = Depends(get_db)):
    """Add a Video to this AudioTrack's videos relationship"""
    db_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == audiotrack_id).first()
    if db_audiotrack is None:
        raise HTTPException(status_code=404, detail="AudioTrack not found")

    related_video = database.query(Video).filter(Video.id == video_id).first()
    if related_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check if relationship already exists
    existing = database.query(videos).filter(
        (videos.c["audioTracks"] == audiotrack_id) &
        (videos.c["videos"] == video_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")

    # Create the association
    association = videos.insert().values(audioTracks=audiotrack_id, videos=video_id)
    database.execute(association)
    database.commit()

    return {"message": "Video added to videos successfully"}


@router.delete("/audiotrack/{audiotrack_id}/videos/{video_id}/", response_model=None, tags=["AudioTrack Relationships"])
async def remove_videos_from_audiotrack(audiotrack_id: int, video_id: int, database: Session = Depends(get_db)):
    """Remove a Video from this AudioTrack's videos relationship"""
    db_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == audiotrack_id).first()
    if db_audiotrack is None:
        raise HTTPException(status_code=404, detail="AudioTrack not found")

    # Check if relationship exists
    existing = database.query(videos).filter(
        (videos.c["audioTracks"] == audiotrack_id) &
        (videos.c["videos"] == video_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")


    # Delete the association
    association = videos.delete().where(
        (videos.c["audioTracks"] == audiotrack_id) &
        (videos.c["videos"] == video_id)
    )
    database.execute(association)
    database.commit()

    return {"message": "Video removed from videos successfully"}


@router.get("/audiotrack/{audiotrack_id}/videos/", response_model=None, tags=["AudioTrack Relationships"])
async def get_videos_of_audiotrack(audiotrack_id: int, database: Session = Depends(get_db)):
    """Get all Video entities related to this AudioTrack through videos"""
    db_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == audiotrack_id).first()
    if db_audiotrack is None:
        raise HTTPException(status_code=404, detail="AudioTrack not found")

    related_video_ids = database.query(videos.c["videos"]).filter(videos.c["audioTracks"] == audiotrack_id).all()
    related_video_list = database.query(Video).filter(Video.id.in_([id[0] for id in related_video_ids])).all()

    return {
        "audiotrack_id": audiotrack_id,
        "videos_count": len(related_video_list),
        "videos": related_video_list
    }


@router.get("/audiotrack/{audiotrack_id}/playerSettings/", response_model=None, tags=["AudioTrack Relationships"])
async def get_playerSettings_of_audiotrack(audiotrack_id: int, database: Session = Depends(get_db)):
    """Get all PlayerSettings entities related to this AudioTrack through playerSettings"""
    db_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == audiotrack_id).first()
    if db_audiotrack is None:
        raise HTTPException(status_code=404, detail="AudioTrack not found")

    playerSettings_list = database.query(PlayerSettings).filter(PlayerSettings.activeAudioTrack_id == audiotrack_id).all()

    return {
        "audiotrack_id": audiotrack_id,
        "playerSettings_count": len(playerSettings_list),
        "playerSettings": playerSettings_list
    }


