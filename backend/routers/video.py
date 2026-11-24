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


@router.get("/video/", response_model=None, tags=["Video"])
def get_all_video(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Video)
        video_list = query.all()

        # Serialize with relationships included
        result = []
        for db_video in video_list:
            item_dict = db_video.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)

            # Add many-to-many and one-to-many relationship objects (full details)
            related_subtitle_list = database.query(Subtitle).join(subtitlevideo, Subtitle.id == subtitlevideo.c["subtitles"]).filter(subtitlevideo.c["subtitleVideo"] == db_video.id).all()
            item_dict['subtitles'] = []
            for related_subtitle_obj in related_subtitle_list:
                related_subtitle_dict = related_subtitle_obj.__dict__.copy()
                related_subtitle_dict.pop('_sa_instance_state', None)
                item_dict['subtitles'].append(related_subtitle_dict)
            related_audiotrack_list = database.query(AudioTrack).join(videos, AudioTrack.id == videos.c["audioTracks"]).filter(videos.c["videos"] == db_video.id).all()
            item_dict['audioTracks'] = []
            for related_audiotrack_obj in related_audiotrack_list:
                related_audiotrack_dict = related_audiotrack_obj.__dict__.copy()
                related_audiotrack_dict.pop('_sa_instance_state', None)
                item_dict['audioTracks'].append(related_audiotrack_dict)
            related_playersettings_list = database.query(PlayerSettings).filter(PlayerSettings.currentVideo_id == db_video.id).all()
            item_dict['playerSettings'] = []
            for related_playersettings_obj in related_playersettings_list:
                related_playersettings_dict = related_playersettings_obj.__dict__.copy()
                related_playersettings_dict.pop('_sa_instance_state', None)
                item_dict['playerSettings'].append(related_playersettings_dict)
            related_scene_list = database.query(Scene).filter(Scene.video_id == db_video.id).all()
            item_dict['scenes'] = []
            for related_scene_obj in related_scene_list:
                related_scene_dict = related_scene_obj.__dict__.copy()
                related_scene_dict.pop('_sa_instance_state', None)
                item_dict['scenes'].append(related_scene_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Video).all()


@router.get("/video/count/", response_model=None, tags=["Video"])
def get_count_video(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Video entities"""
    count = database.query(Video).count()
    return {"count": count}


@router.get("/video/paginated/", response_model=None, tags=["Video"])
def get_paginated_video(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Video entities"""
    total = database.query(Video).count()
    video_list = database.query(Video).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": video_list
        }

    result = []
    for db_video in video_list:
        related_subtitle_ids = database.query(subtitlevideo.c["subtitles"]).filter(subtitlevideo.c["subtitleVideo"] == db_video.id).all()
        related_audiotrack_ids = database.query(videos.c["audioTracks"]).filter(videos.c["videos"] == db_video.id).all()
        playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.currentVideo_id == db_video.id).all()
        scenes_ids = database.query(Scene.id).filter(Scene.video_id == db_video.id).all()
        item_data = {
            "video": db_video,
            "subtitle_ids": [x[0] for x in related_subtitle_ids],
            "audiotrack_ids": [x[0] for x in related_audiotrack_ids],
            "playerSettings_ids": [x[0] for x in playerSettings_ids],            "scenes_ids": [x[0] for x in scenes_ids]        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/video/search/", response_model=None, tags=["Video"])
def search_video(
    description: str = None,
    durationSeconds: int = None,
    fileUrl: str = None,
    learningObjectives: str = None,
    thumbnailUrl: str = None,
    title: str = None,
    version: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Video entities by attributes"""
    query = database.query(Video)

    if description is not None:
        query = query.filter(Video.description.ilike(f"%{description}%"))
    if durationSeconds is not None:
        query = query.filter(Video.durationSeconds == durationSeconds)
    if fileUrl is not None:
        query = query.filter(Video.fileUrl.ilike(f"%{fileUrl}%"))
    if learningObjectives is not None:
        query = query.filter(Video.learningObjectives.ilike(f"%{learningObjectives}%"))
    if thumbnailUrl is not None:
        query = query.filter(Video.thumbnailUrl.ilike(f"%{thumbnailUrl}%"))
    if title is not None:
        query = query.filter(Video.title.ilike(f"%{title}%"))
    if version is not None:
        query = query.filter(Video.version.ilike(f"%{version}%"))

    results = query.all()
    return results


@router.get("/video/{video_id}/", response_model=None, tags=["Video"])
async def get_video(video_id: int, database: Session = Depends(get_db)) -> Video:
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    related_subtitle_ids = database.query(subtitlevideo.c["subtitles"]).filter(subtitlevideo.c["subtitleVideo"] == db_video.id).all()
    related_audiotrack_ids = database.query(videos.c["audioTracks"]).filter(videos.c["videos"] == db_video.id).all()
    playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.currentVideo_id == db_video.id).all()
    scenes_ids = database.query(Scene.id).filter(Scene.video_id == db_video.id).all()
    response_data = {
        "video": db_video,
        "subtitle_ids": [x[0] for x in related_subtitle_ids],
        "audiotrack_ids": [x[0] for x in related_audiotrack_ids],
        "playerSettings_ids": [x[0] for x in playerSettings_ids],        "scenes_ids": [x[0] for x in scenes_ids]}
    return response_data



@router.post("/video/", response_model=None, tags=["Video"])
async def create_video(video_data: VideoCreate, database: Session = Depends(get_db)) -> Video:

    if video_data.subtitles:
        for id in video_data.subtitles:
            # Entity already validated before creation
            related_subtitle = database.query(Subtitle).filter(Subtitle.id == id).first()
            if not related_subtitle:
                raise HTTPException(status_code=404, detail=f"Subtitle with ID {id} not found")
    if video_data.audioTracks:
        for id in video_data.audioTracks:
            # Entity already validated before creation
            related_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == id).first()
            if not related_audiotrack:
                raise HTTPException(status_code=404, detail=f"AudioTrack with ID {id} not found")

    db_video = Video(
        creationDate=video_data.creationDate,        description=video_data.description,        durationSeconds=video_data.durationSeconds,        fileUrl=video_data.fileUrl,        learningObjectives=video_data.learningObjectives,        thumbnailUrl=video_data.thumbnailUrl,        title=video_data.title,        version=video_data.version        )

    database.add(db_video)
    database.flush()
    database.refresh(db_video)

    if video_data.playerSettings:
        # Validate that all PlayerSettings IDs exist
        for related_playersettings_id in video_data.playerSettings:
            related_playersettings = database.query(PlayerSettings).filter(PlayerSettings.id == related_playersettings_id).first()
            if not related_playersettings:
                raise HTTPException(status_code=400, detail=f"PlayerSettings with id {related_playersettings_id} not found")

        # Update the related entities with the new foreign key
        database.query(PlayerSettings).filter(PlayerSettings.id.in_(video_data.playerSettings)).update(
            {PlayerSettings.currentVideo_id: db_video.id}, synchronize_session=False
        )
        database.flush()
    if video_data.scenes:
        # Validate that all Scene IDs exist
        for related_scene_id in video_data.scenes:
            related_scene = database.query(Scene).filter(Scene.id == related_scene_id).first()
            if not related_scene:
                raise HTTPException(status_code=400, detail=f"Scene with id {related_scene_id} not found")

        # Update the related entities with the new foreign key
        database.query(Scene).filter(Scene.id.in_(video_data.scenes)).update(
            {Scene.video_id: db_video.id}, synchronize_session=False
        )
        database.flush()


    if video_data.subtitles:
        for id in video_data.subtitles:
            # Entity already validated before creation
            related_subtitle = database.query(Subtitle).filter(Subtitle.id == id).first()
            # Create the association
            association = subtitlevideo.insert().values(subtitleVideo=db_video.id, subtitles=related_subtitle.id)
            database.execute(association)
            database.flush()
    if video_data.audioTracks:
        for id in video_data.audioTracks:
            # Entity already validated before creation
            related_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == id).first()
            # Create the association
            association = videos.insert().values(videos=db_video.id, audioTracks=related_audiotrack.id)
            database.execute(association)
            database.flush()


    related_subtitle_ids = database.query(subtitlevideo.c["subtitles"]).filter(subtitlevideo.c["subtitleVideo"] == db_video.id).all()
    related_audiotrack_ids = database.query(videos.c["audioTracks"]).filter(videos.c["videos"] == db_video.id).all()
    playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.currentVideo_id == db_video.id).all()
    scenes_ids = database.query(Scene.id).filter(Scene.video_id == db_video.id).all()
    response_data = {
        "video": db_video,
        "subtitle_ids": [x[0] for x in related_subtitle_ids],
        "audiotrack_ids": [x[0] for x in related_audiotrack_ids],
        "playerSettings_ids": [x[0] for x in playerSettings_ids],        "scenes_ids": [x[0] for x in scenes_ids]    }
    database.commit()
    database.refresh(db_video)
    return response_data


@router.post("/video/bulk/", response_model=None, tags=["Video"])
async def bulk_create_video(items: list[VideoCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Video entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['subtitles', 'audioTracks', 'playerSettings', 'scenes']):
        raise HTTPException(status_code=422, detail="Bulk creation of Video with relationships is not supported; use POST /video/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_video = Video(
                creationDate=item_data.creationDate,                description=item_data.description,                durationSeconds=item_data.durationSeconds,                fileUrl=item_data.fileUrl,                learningObjectives=item_data.learningObjectives,                thumbnailUrl=item_data.thumbnailUrl,                title=item_data.title,                version=item_data.version            )
            database.add(db_video)
            database.flush()  # Get ID without committing
            created_items.append(db_video.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of Video failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Video entities"
    }


@router.delete("/video/bulk/", response_model=None, tags=["Video"])
async def bulk_delete_video(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Video entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_video = database.query(Video).filter(Video.id == item_id).first()
        if db_video:
            conflict = video_delete_conflict(db_video)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete Video " + str(item_id) + ": " + conflict)
            database.delete(db_video)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Video entities"
    }

@router.put("/video/{video_id}/", response_model=None, tags=["Video"])
async def update_video(video_id: int, video_data: VideoCreate, database: Session = Depends(get_db)) -> Video:
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    setattr(db_video, 'creationDate', video_data.creationDate)
    setattr(db_video, 'description', video_data.description)
    setattr(db_video, 'durationSeconds', video_data.durationSeconds)
    setattr(db_video, 'fileUrl', video_data.fileUrl)
    setattr(db_video, 'learningObjectives', video_data.learningObjectives)
    setattr(db_video, 'thumbnailUrl', video_data.thumbnailUrl)
    setattr(db_video, 'title', video_data.title)
    setattr(db_video, 'version', video_data.version)
    if video_data.playerSettings is not None:
        requested_playerSettings = set(video_data.playerSettings)
        current_playerSettings = {
            getattr(item, 'id')
            for item in database.query(PlayerSettings).filter(PlayerSettings.currentVideo_id == db_video.id).all()
        }
        playerSettings_to_detach = current_playerSettings - requested_playerSettings
        if playerSettings_to_detach:
            database.query(PlayerSettings).filter(PlayerSettings.id.in_(playerSettings_to_detach)).update(
                {PlayerSettings.currentVideo_id: None}, synchronize_session=False
            )
        playerSettings_to_attach = requested_playerSettings - current_playerSettings
        for related_playersettings_id in playerSettings_to_attach:
            related_playersettings = database.query(PlayerSettings).filter(PlayerSettings.id == related_playersettings_id).first()
            if not related_playersettings:
                raise HTTPException(status_code=400, detail="PlayerSettings with id " + str(related_playersettings_id) + " not found")
        if playerSettings_to_attach:
            database.query(PlayerSettings).filter(PlayerSettings.id.in_(playerSettings_to_attach)).update(
                {PlayerSettings.currentVideo_id: db_video.id}, synchronize_session=False
            )
    if video_data.scenes is not None:
        requested_scenes = set(video_data.scenes)
        current_scenes = {
            getattr(item, 'id')
            for item in database.query(Scene).filter(Scene.video_id == db_video.id).all()
        }
        scenes_to_detach = current_scenes - requested_scenes
        if scenes_to_detach:
            raise HTTPException(status_code=409, detail="Scene " + ", ".join(str(item) for item in sorted(scenes_to_detach)) + " requires a video: reassign it instead of removing it")
        scenes_to_attach = requested_scenes - current_scenes
        for related_scene_id in scenes_to_attach:
            related_scene = database.query(Scene).filter(Scene.id == related_scene_id).first()
            if not related_scene:
                raise HTTPException(status_code=400, detail="Scene with id " + str(related_scene_id) + " not found")
        if scenes_to_attach:
            database.query(Scene).filter(Scene.id.in_(scenes_to_attach)).update(
                {Scene.video_id: db_video.id}, synchronize_session=False
            )
    if video_data.subtitles is not None:
        existing_related_subtitle_ids = [assoc._mapping["subtitles"] for assoc in database.execute(
            subtitlevideo.select().where(subtitlevideo.c["subtitleVideo"] == db_video.id))]

        related_subtitles_to_remove = set(existing_related_subtitle_ids) - set(video_data.subtitles)
        for related_subtitle_id in related_subtitles_to_remove:
            association = subtitlevideo.delete().where(
                (subtitlevideo.c["subtitleVideo"] == db_video.id) & (subtitlevideo.c["subtitles"] == related_subtitle_id))
            database.execute(association)

        new_related_subtitle_ids = set(video_data.subtitles) - set(existing_related_subtitle_ids)
        for related_subtitle_id in new_related_subtitle_ids:
            related_subtitle = database.query(Subtitle).filter(Subtitle.id == related_subtitle_id).first()
            if related_subtitle is None:
                raise HTTPException(status_code=404, detail="Subtitle with ID " + str(related_subtitle_id) + " not found")
            association = subtitlevideo.insert().values(subtitles=related_subtitle.id, subtitleVideo=db_video.id)
            database.execute(association)
    if video_data.audioTracks is not None:
        existing_related_audiotrack_ids = [assoc._mapping["audioTracks"] for assoc in database.execute(
            videos.select().where(videos.c["videos"] == db_video.id))]

        related_audiotracks_to_remove = set(existing_related_audiotrack_ids) - set(video_data.audioTracks)
        for related_audiotrack_id in related_audiotracks_to_remove:
            association = videos.delete().where(
                (videos.c["videos"] == db_video.id) & (videos.c["audioTracks"] == related_audiotrack_id))
            database.execute(association)

        new_related_audiotrack_ids = set(video_data.audioTracks) - set(existing_related_audiotrack_ids)
        for related_audiotrack_id in new_related_audiotrack_ids:
            related_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == related_audiotrack_id).first()
            if related_audiotrack is None:
                raise HTTPException(status_code=404, detail="AudioTrack with ID " + str(related_audiotrack_id) + " not found")
            association = videos.insert().values(audioTracks=related_audiotrack.id, videos=db_video.id)
            database.execute(association)
    database.commit()
    database.refresh(db_video)

    related_subtitle_ids = database.query(subtitlevideo.c["subtitles"]).filter(subtitlevideo.c["subtitleVideo"] == db_video.id).all()
    related_audiotrack_ids = database.query(videos.c["audioTracks"]).filter(videos.c["videos"] == db_video.id).all()
    playerSettings_ids = database.query(PlayerSettings.id).filter(PlayerSettings.currentVideo_id == db_video.id).all()
    scenes_ids = database.query(Scene.id).filter(Scene.video_id == db_video.id).all()
    response_data = {
        "video": db_video,
        "subtitle_ids": [x[0] for x in related_subtitle_ids],
        "audiotrack_ids": [x[0] for x in related_audiotrack_ids],
        "playerSettings_ids": [x[0] for x in playerSettings_ids],        "scenes_ids": [x[0] for x in scenes_ids]    }
    return response_data


def video_delete_conflict(db_video, deleting=None, wholes=()):
    """Why this Video cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_video)
        deleting = [db_video] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    if any(whole is db_video for whole in wholes):
        return "Video " + str(getattr(db_video, 'id')) + " is one of its own parts"
    from routers.scene import scene_delete_conflict
    parts_scenes = db_video.scenes
    for part in (list(parts_scenes) if isinstance(parts_scenes, list) else [item for item in [parts_scenes] if item is not None]):
        conflict = scene_delete_conflict(part, deleting, wholes + (db_video,))
        if conflict:
            return "Scene " + str(getattr(part, 'id')) + " would be deleted with it, and " + conflict
    return None


@router.delete("/video/{video_id}/", response_model=None, tags=["Video"])
async def delete_video(video_id: int, database: Session = Depends(get_db)):
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    conflict = video_delete_conflict(db_video)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete Video " + str(video_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_video = {
        attr.key: getattr(db_video, attr.key)
        for attr in db_video.__mapper__.column_attrs
    }
    database.delete(db_video)
    database.commit()
    return deleted_video

@router.post("/video/{video_id}/subtitles/{subtitle_id}/", response_model=None, tags=["Video Relationships"])
async def add_subtitles_to_video(video_id: int, subtitle_id: int, database: Session = Depends(get_db)):
    """Add a Subtitle to this Video's subtitles relationship"""
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    related_subtitle = database.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if related_subtitle is None:
        raise HTTPException(status_code=404, detail="Subtitle not found")

    # Check if relationship already exists
    existing = database.query(subtitlevideo).filter(
        (subtitlevideo.c["subtitleVideo"] == video_id) &
        (subtitlevideo.c["subtitles"] == subtitle_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")

    # Create the association
    association = subtitlevideo.insert().values(subtitleVideo=video_id, subtitles=subtitle_id)
    database.execute(association)
    database.commit()

    return {"message": "Subtitle added to subtitles successfully"}


@router.delete("/video/{video_id}/subtitles/{subtitle_id}/", response_model=None, tags=["Video Relationships"])
async def remove_subtitles_from_video(video_id: int, subtitle_id: int, database: Session = Depends(get_db)):
    """Remove a Subtitle from this Video's subtitles relationship"""
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check if relationship exists
    existing = database.query(subtitlevideo).filter(
        (subtitlevideo.c["subtitleVideo"] == video_id) &
        (subtitlevideo.c["subtitles"] == subtitle_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")


    # Delete the association
    association = subtitlevideo.delete().where(
        (subtitlevideo.c["subtitleVideo"] == video_id) &
        (subtitlevideo.c["subtitles"] == subtitle_id)
    )
    database.execute(association)
    database.commit()

    return {"message": "Subtitle removed from subtitles successfully"}


@router.get("/video/{video_id}/subtitles/", response_model=None, tags=["Video Relationships"])
async def get_subtitles_of_video(video_id: int, database: Session = Depends(get_db)):
    """Get all Subtitle entities related to this Video through subtitles"""
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    related_subtitle_ids = database.query(subtitlevideo.c["subtitles"]).filter(subtitlevideo.c["subtitleVideo"] == video_id).all()
    related_subtitle_list = database.query(Subtitle).filter(Subtitle.id.in_([id[0] for id in related_subtitle_ids])).all()

    return {
        "video_id": video_id,
        "subtitles_count": len(related_subtitle_list),
        "subtitles": related_subtitle_list
    }

@router.post("/video/{video_id}/audioTracks/{audiotrack_id}/", response_model=None, tags=["Video Relationships"])
async def add_audioTracks_to_video(video_id: int, audiotrack_id: int, database: Session = Depends(get_db)):
    """Add a AudioTrack to this Video's audioTracks relationship"""
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    related_audiotrack = database.query(AudioTrack).filter(AudioTrack.id == audiotrack_id).first()
    if related_audiotrack is None:
        raise HTTPException(status_code=404, detail="AudioTrack not found")

    # Check if relationship already exists
    existing = database.query(videos).filter(
        (videos.c["videos"] == video_id) &
        (videos.c["audioTracks"] == audiotrack_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")

    # Create the association
    association = videos.insert().values(videos=video_id, audioTracks=audiotrack_id)
    database.execute(association)
    database.commit()

    return {"message": "AudioTrack added to audioTracks successfully"}


@router.delete("/video/{video_id}/audioTracks/{audiotrack_id}/", response_model=None, tags=["Video Relationships"])
async def remove_audioTracks_from_video(video_id: int, audiotrack_id: int, database: Session = Depends(get_db)):
    """Remove a AudioTrack from this Video's audioTracks relationship"""
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check if relationship exists
    existing = database.query(videos).filter(
        (videos.c["videos"] == video_id) &
        (videos.c["audioTracks"] == audiotrack_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")


    # Delete the association
    association = videos.delete().where(
        (videos.c["videos"] == video_id) &
        (videos.c["audioTracks"] == audiotrack_id)
    )
    database.execute(association)
    database.commit()

    return {"message": "AudioTrack removed from audioTracks successfully"}


@router.get("/video/{video_id}/audioTracks/", response_model=None, tags=["Video Relationships"])
async def get_audioTracks_of_video(video_id: int, database: Session = Depends(get_db)):
    """Get all AudioTrack entities related to this Video through audioTracks"""
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    related_audiotrack_ids = database.query(videos.c["audioTracks"]).filter(videos.c["videos"] == video_id).all()
    related_audiotrack_list = database.query(AudioTrack).filter(AudioTrack.id.in_([id[0] for id in related_audiotrack_ids])).all()

    return {
        "video_id": video_id,
        "audioTracks_count": len(related_audiotrack_list),
        "audioTracks": related_audiotrack_list
    }


@router.get("/video/{video_id}/playerSettings/", response_model=None, tags=["Video Relationships"])
async def get_playerSettings_of_video(video_id: int, database: Session = Depends(get_db)):
    """Get all PlayerSettings entities related to this Video through playerSettings"""
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    playerSettings_list = database.query(PlayerSettings).filter(PlayerSettings.currentVideo_id == video_id).all()

    return {
        "video_id": video_id,
        "playerSettings_count": len(playerSettings_list),
        "playerSettings": playerSettings_list
    }

@router.get("/video/{video_id}/scenes/", response_model=None, tags=["Video Relationships"])
async def get_scenes_of_video(video_id: int, database: Session = Depends(get_db)):
    """Get all Scene entities related to this Video through scenes"""
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    scenes_list = database.query(Scene).filter(Scene.video_id == video_id).all()

    return {
        "video_id": video_id,
        "scenes_count": len(scenes_list),
        "scenes": scenes_list
    }


