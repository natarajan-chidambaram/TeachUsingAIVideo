import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

logger = logging.getLogger(__name__)
router = APIRouter()

# Playback speeds the player accepts. The list is also used by the frontend
# speed selector, so the two stay in step.
SUPPORTED_PLAYBACK_SPEEDS = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)

# How close a requested speed must be to a supported one to be accepted.
SPEED_TOLERANCE = 0.001


def _playersettings_snapshot(db_playersettings):
    """Serialize a PlayerSettings row (columns only) for an action response."""
    return {
        attr.key: getattr(db_playersettings, attr.key)
        for attr in db_playersettings.__mapper__.column_attrs
    }


def _require_param(params, name):
    """Read a required action parameter, or fail with a clear 400.

    The action buttons post their arguments flat ({"level": 0.5}) but the
    OpenAPI schema also advertises a nested {"params": {...}} body, so both
    shapes are accepted.
    """
    value = None
    if isinstance(params, dict):
        value = params.get(name)
        if value is None:
            nested = params.get("params")
            if isinstance(nested, dict):
                value = nested.get(name)
    if value is None:
        raise HTTPException(
            status_code=400,
            detail=f"Parameter '{name}' is required for this action",
        )
    return value


def _default_audio_track(database, video_id, language_code=None):
    """Pick the audio track to play for a language (default track first)."""
    if video_id is None:
        return None
    query = database.query(AudioTrack).join(
        videos, AudioTrack.id == videos.c["audioTracks"]
    ).filter(videos.c["videos"] == video_id)
    if language_code:
        query = query.filter(AudioTrack.languageCode == language_code)
    tracks = query.order_by(AudioTrack.isDefault.desc(), AudioTrack.id).all()
    return tracks[0] if tracks else None


def _default_subtitle(database, video_id, language_code=None):
    """Pick the subtitle track to show for a language (default track first)."""
    if video_id is None:
        return None
    query = database.query(Subtitle).join(
        subtitlevideo, Subtitle.id == subtitlevideo.c["subtitles"]
    ).filter(subtitlevideo.c["subtitleVideo"] == video_id)
    if language_code:
        query = query.filter(Subtitle.languageCode == language_code)
    tracks = query.order_by(Subtitle.isEnabledByDefault.desc(), Subtitle.id).all()
    return tracks[0] if tracks else None

############################################
#   PlayerSettings Method Endpoints
############################################





@router.post("/playersettings/{playersettings_id}/methods/changeLanguage/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_changeLanguage(
    playersettings_id: int,  # the PlayerSettings that changeLanguage runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Execute the changeLanguage method on a PlayerSettings instance.

    Parameters:
    - languageCode: str
    """
    # PlayerSettings.changeLanguage: load the instance
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    # PlayerSettings.changeLanguage
    language_code = _require_param(params, "languageCode")
    if not isinstance(language_code, str) or not language_code.strip():
        raise HTTPException(status_code=400, detail="Parameter 'languageCode' must be a non-empty string")
    language_code = language_code.strip()

    video_id = _playersettings_object.currentVideo_id

    # The language must be one the current video actually offers.
    if video_id is not None:
        available = {
            code for (code,) in database.query(AudioTrack.languageCode).join(
                videos, AudioTrack.id == videos.c["audioTracks"]
            ).filter(videos.c["videos"] == video_id).distinct().all()
        } | {
            code for (code,) in database.query(Subtitle.languageCode).join(
                subtitlevideo, Subtitle.id == subtitlevideo.c["subtitles"]
            ).filter(subtitlevideo.c["subtitleVideo"] == video_id).distinct().all()
        }
        if available and language_code not in available:
            raise HTTPException(
                status_code=400,
                detail="Language '" + language_code + "' is not available for this video",
            )

    _playersettings_object.activeLanguageCode = language_code

    audio_track = _default_audio_track(database, video_id, language_code)
    subtitle = _default_subtitle(database, video_id, language_code)
    _playersettings_object.activeAudioTrack_id = audio_track.id if audio_track else None
    _playersettings_object.activeSubtitle_id = subtitle.id if subtitle else None

    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "activeLanguageCode": _playersettings_object.activeLanguageCode,
        "activeAudioTrack": _playersettings_snapshot(audio_track) if audio_track else None,
        "activeSubtitle": _playersettings_snapshot(subtitle) if subtitle else None,
    }






@router.post("/playersettings/{playersettings_id}/methods/changeAudioLanguage/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_changeAudioLanguage(
    playersettings_id: int,  # the PlayerSettings that changeAudioLanguage runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Switch the narration (audio) language without touching the subtitles.

    Parameters:
    - languageCode: str
    """
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    language_code = _require_param(params, "languageCode")
    if not isinstance(language_code, str) or not language_code.strip():
        raise HTTPException(status_code=400, detail="Parameter 'languageCode' must be a non-empty string")
    language_code = language_code.strip()

    video_id = _playersettings_object.currentVideo_id
    if video_id is not None:
        offered = {
            code for (code,) in database.query(AudioTrack.languageCode).join(
                videos, AudioTrack.id == videos.c["audioTracks"]
            ).filter(videos.c["videos"] == video_id).distinct().all()
        }
        if offered and language_code not in offered:
            raise HTTPException(
                status_code=400,
                detail="Audio language '" + language_code + "' is not available for this video",
            )

    audio_track = _default_audio_track(database, video_id, language_code)
    _playersettings_object.activeAudioTrack_id = audio_track.id if audio_track else None
    _playersettings_object.activeLanguageCode = language_code

    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "activeLanguageCode": _playersettings_object.activeLanguageCode,
        "activeAudioTrack": _playersettings_snapshot(audio_track) if audio_track else None,
    }


@router.post("/playersettings/{playersettings_id}/methods/changeSubtitleLanguage/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_changeSubtitleLanguage(
    playersettings_id: int,  # the PlayerSettings that changeSubtitleLanguage runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Switch the subtitle language without touching the narration audio.

    Parameters:
    - languageCode: str
    """
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    language_code = _require_param(params, "languageCode")
    if not isinstance(language_code, str) or not language_code.strip():
        raise HTTPException(status_code=400, detail="Parameter 'languageCode' must be a non-empty string")
    language_code = language_code.strip()

    video_id = _playersettings_object.currentVideo_id
    if video_id is not None:
        offered = {
            code for (code,) in database.query(Subtitle.languageCode).join(
                subtitlevideo, Subtitle.id == subtitlevideo.c["subtitles"]
            ).filter(subtitlevideo.c["subtitleVideo"] == video_id).distinct().all()
        }
        if offered and language_code not in offered:
            raise HTTPException(
                status_code=400,
                detail="Subtitle language '" + language_code + "' is not available for this video",
            )

    subtitle = _default_subtitle(database, video_id, language_code)
    _playersettings_object.activeSubtitle_id = subtitle.id if subtitle else None

    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "activeSubtitle": _playersettings_snapshot(subtitle) if subtitle else None,
    }


@router.post("/playersettings/{playersettings_id}/methods/loadVideo/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_loadVideo(
    playersettings_id: int,  # the PlayerSettings that loadVideo runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Execute the loadVideo method on a PlayerSettings instance.

    Parameters:
    - videoId: int
    """
    # PlayerSettings.loadVideo: load the instance
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    # PlayerSettings.loadVideo
    video_id = _require_param(params, "videoId")
    if isinstance(video_id, bool) or not isinstance(video_id, int):
        raise HTTPException(status_code=400, detail="Parameter 'videoId' must be an integer video id")
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail=f"Video with id {video_id} not found")

    _playersettings_object.currentVideo_id = db_video.id
    _playersettings_object.currentTimeSeconds = 0
    _playersettings_object.isFullScreen = False

    audio_track = _default_audio_track(database, db_video.id)
    subtitle = _default_subtitle(database, db_video.id)
    _playersettings_object.activeAudioTrack_id = audio_track.id if audio_track else None
    _playersettings_object.activeSubtitle_id = subtitle.id if subtitle else None
    if audio_track:
        _playersettings_object.activeLanguageCode = audio_track.languageCode
    elif subtitle:
        _playersettings_object.activeLanguageCode = subtitle.languageCode

    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "video": {
            "id": db_video.id,
            "title": db_video.title,
            "description": db_video.description,
            "fileUrl": db_video.fileUrl,
            "thumbnailUrl": db_video.thumbnailUrl,
            "durationSeconds": db_video.durationSeconds,
            "learningObjectives": db_video.learningObjectives,
        },
        "activeAudioTrack": _playersettings_snapshot(audio_track) if audio_track else None,
        "activeSubtitle": _playersettings_snapshot(subtitle) if subtitle else None,
    }






@router.post("/playersettings/{playersettings_id}/methods/pause/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_pause(
    playersettings_id: int,  # the PlayerSettings that pause runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Execute the pause method on a PlayerSettings instance.

    PlayerSettings.pause() is declared with no parameters, and the button sends none.
    An empty request body must succeed - default any value the spec leaves open, never demand it.
    """
    # PlayerSettings.pause: load the instance
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    # PlayerSettings.pause
    # Pausing keeps the playhead where it is; the model has no "isPlaying" flag,
    # so the paused state is reported and the position is preserved.
    if _playersettings_object.currentTimeSeconds < 0:
        _playersettings_object.currentTimeSeconds = 0
    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "action": "pause",
        "isPlaying": False,
        "currentTimeSeconds": _playersettings_object.currentTimeSeconds,
    }






@router.post("/playersettings/{playersettings_id}/methods/play/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_play(
    playersettings_id: int,  # the PlayerSettings that play runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Execute the play method on a PlayerSettings instance.

    PlayerSettings.play() is declared with no parameters, and the button sends none.
    An empty request body must succeed - default any value the spec leaves open, never demand it.
    """
    # PlayerSettings.play: load the instance
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    # PlayerSettings.play
    # Playing resumes from the stored playhead. Looping is a persisted player
    # preference, so it is preserved as-is.
    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "action": "play",
        "isPlaying": True,
        "currentTimeSeconds": _playersettings_object.currentTimeSeconds,
        "isLooping": _playersettings_object.isLooping,
    }






@router.post("/playersettings/{playersettings_id}/methods/seek/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_seek(
    playersettings_id: int,  # the PlayerSettings that seek runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Execute the seek method on a PlayerSettings instance.

    Parameters:
    - timeSeconds: int
    """
    # PlayerSettings.seek: load the instance
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    # PlayerSettings.seek
    time_seconds = _require_param(params, "timeSeconds")
    if isinstance(time_seconds, bool) or not isinstance(time_seconds, int):
        raise HTTPException(status_code=400, detail="Parameter 'timeSeconds' must be an integer number of seconds")
    if time_seconds < 0:
        raise HTTPException(status_code=400, detail="Parameter 'timeSeconds' must not be negative")

    # A seek past the end of the loaded video is refused rather than silently
    # clamped, so the caller learns the position does not exist.
    db_video = _playersettings_object.currentVideo
    if db_video is not None and time_seconds > db_video.durationSeconds:
        raise HTTPException(
            status_code=400,
            detail="Cannot seek to " + str(time_seconds) + "s: the video is only "
            + str(db_video.durationSeconds) + "s long",
        )

    _playersettings_object.currentTimeSeconds = time_seconds
    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "action": "seek",
        "currentTimeSeconds": _playersettings_object.currentTimeSeconds,
    }






@router.post("/playersettings/{playersettings_id}/methods/setPlaybackSpeed/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_setPlaybackSpeed(
    playersettings_id: int,  # the PlayerSettings that setPlaybackSpeed runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Execute the setPlaybackSpeed method on a PlayerSettings instance.

    Parameters:
    - speed: float
    """
    # PlayerSettings.setPlaybackSpeed: load the instance
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    # PlayerSettings.setPlaybackSpeed
    speed = _require_param(params, "speed")
    if isinstance(speed, bool) or not isinstance(speed, (int, float)):
        raise HTTPException(status_code=400, detail="Parameter 'speed' must be a number")
    speed = float(speed)
    if speed <= 0:
        raise HTTPException(status_code=400, detail="Playback speed must be greater than 0")
    if not any(abs(speed - supported) <= SPEED_TOLERANCE for supported in SUPPORTED_PLAYBACK_SPEEDS):
        raise HTTPException(
            status_code=400,
            detail="Unsupported playback speed " + str(speed) + ". Supported speeds: "
            + ", ".join(str(value) for value in SUPPORTED_PLAYBACK_SPEEDS),
        )

    _playersettings_object.playbackSpeed = speed
    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "action": "setPlaybackSpeed",
        "playbackSpeed": _playersettings_object.playbackSpeed,
    }






@router.post("/playersettings/{playersettings_id}/methods/setVolume/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_setVolume(
    playersettings_id: int,  # the PlayerSettings that setVolume runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Execute the setVolume method on a PlayerSettings instance.

    Parameters:
    - level: float
    """
    # PlayerSettings.setVolume: load the instance
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    # PlayerSettings.setVolume
    level = _require_param(params, "level")
    if isinstance(level, bool) or not isinstance(level, (int, float)):
        raise HTTPException(status_code=400, detail="Parameter 'level' must be a number")
    level = float(level)
    if level < 0.0 or level > 1.0:
        raise HTTPException(status_code=400, detail="Volume level must be between 0.0 and 1.0")

    _playersettings_object.volume = level
    # A volume of zero means silence, which is the muted state.
    _playersettings_object.isMuted = level == 0.0
    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "action": "setVolume",
        "volume": _playersettings_object.volume,
        "isMuted": _playersettings_object.isMuted,
    }






@router.post("/playersettings/{playersettings_id}/methods/stop/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_stop(
    playersettings_id: int,  # the PlayerSettings that stop runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Execute the stop method on a PlayerSettings instance.

    PlayerSettings.stop() is declared with no parameters, and the button sends none.
    An empty request body must succeed - default any value the spec leaves open, never demand it.
    """
    # PlayerSettings.stop: load the instance
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    # PlayerSettings.stop
    # Stopping rewinds the playhead to the beginning and leaves the video loaded.
    _playersettings_object.currentTimeSeconds = 0
    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "action": "stop",
        "isPlaying": False,
        "currentTimeSeconds": _playersettings_object.currentTimeSeconds,
    }






@router.post("/playersettings/{playersettings_id}/methods/toggleFullScreen/", response_model=None, tags=["PlayerSettings Methods"])
async def execute_playersettings_toggleFullScreen(
    playersettings_id: int,  # the PlayerSettings that toggleFullScreen runs on
    params: dict = Body(default=None),
    database: Session = Depends(get_db)
):
    """Execute the toggleFullScreen method on a PlayerSettings instance.

    PlayerSettings.toggleFullScreen() is declared with no parameters, and the button sends none.
    An empty request body must succeed - default any value the spec leaves open, never demand it.
    """
    # PlayerSettings.toggleFullScreen: load the instance
    _playersettings_object = database.query(PlayerSettings).filter(PlayerSettings.id == playersettings_id).first()
    if _playersettings_object is None:
        raise HTTPException(status_code=404, detail="PlayerSettings not found")
    # PlayerSettings.toggleFullScreen
    _playersettings_object.isFullScreen = not bool(_playersettings_object.isFullScreen)
    database.commit()
    database.refresh(_playersettings_object)
    return {
        "playersettings": _playersettings_snapshot(_playersettings_object),
        "action": "toggleFullScreen",
        "isFullScreen": _playersettings_object.isFullScreen,
    }

