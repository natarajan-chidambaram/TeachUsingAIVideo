import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic_classes import *
from sql_alchemy import *
from database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/video/{video_id}/languages/", response_model=None, tags=["Video Relationships"]
)
async def get_languages_of_video(video_id: int, database: Session = Depends(get_db)):
    """List the languages a Video is available in.

    Each entry carries the language code plus the AudioTrack and Subtitle rows
    that implement it, so the frontend can populate a language switcher and
    swap the media sources without a second round trip.
    """
    db_video = database.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    audio_tracks = (
        database.query(AudioTrack)
        .join(videos, AudioTrack.id == videos.c["audioTracks"])
        .filter(videos.c["videos"] == video_id)
        .all()
    )
    subtitles = (
        database.query(Subtitle)
        .join(subtitlevideo, Subtitle.id == subtitlevideo.c["subtitles"])
        .filter(subtitlevideo.c["subtitleVideo"] == video_id)
        .all()
    )

    def _snapshot(obj):
        return {
            attr.key: getattr(obj, attr.key) for attr in obj.__mapper__.column_attrs
        }

    # Keep a stable, human-friendly order: the default language first, then
    # the remaining codes alphabetically.
    default_codes = []
    for track in audio_tracks:
        if track.isDefault and track.languageCode not in default_codes:
            default_codes.append(track.languageCode)
    for subtitle in subtitles:
        if subtitle.isEnabledByDefault and subtitle.languageCode not in default_codes:
            default_codes.append(subtitle.languageCode)

    language_codes = set(track.languageCode for track in audio_tracks)
    language_codes |= set(subtitle.languageCode for subtitle in subtitles)
    ordered_codes = [code for code in default_codes if code in language_codes]
    ordered_codes += sorted(
        code for code in language_codes if code not in ordered_codes
    )

    languages = []
    for code in ordered_codes:
        matching_tracks = [t for t in audio_tracks if t.languageCode == code]
        matching_subtitles = [s for s in subtitles if s.languageCode == code]
        languages.append(
            {
                "languageCode": code,
                "isDefault": bool(matching_tracks and matching_tracks[0].isDefault)
                or bool(
                    matching_subtitles and matching_subtitles[0].isEnabledByDefault
                ),
                "audioTracks": [_snapshot(track) for track in matching_tracks],
                "subtitles": [_snapshot(subtitle) for subtitle in matching_subtitles],
            }
        )

    return {
        "video_id": video_id,
        "title": db_video.title,
        "languages": languages,
        "languageCodes": ordered_codes,
        "languages_count": len(languages),
    }
