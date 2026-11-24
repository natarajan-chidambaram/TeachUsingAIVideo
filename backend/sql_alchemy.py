import enum
import os
# Both spellings are bound on purpose. Generated code uses the trailing-
# underscore aliases so a modelled class named List, Optional or DateTime
# cannot shadow them. The PLAIN names are imported too because this file is
# routinely edited afterwards by an LLM, which writes ordinary Python and has
# no reason to know about the aliasing convention; without the plain names
# such edits fail to import:
#
#     Mapped_[Optional[int]]        undefined name 'Optional'
#     mapped_column(DateTime())     undefined name 'DateTime'
#
# so every aliased name below is bound both ways.
from typing import List, Optional, List as List_, Optional as Optional_
from sqlalchemy import (
    create_engine, Enum, UniqueConstraint as _UniqueConstraint, event as _sa_event,
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Interval,
    PickleType, String, Table, Text, Time,
    Column as Column_, ForeignKey as ForeignKey_, Table as Table_,
    Text as Text_, Boolean as Boolean_, String as String_, Date as Date_,
    Time as Time_, DateTime as DateTime_, Float as Float_, Integer as Integer_,
    Interval as Interval_, PickleType as PickleType_,
)
from sqlalchemy.orm import (
    column_property, DeclarativeBase, Mapped, Mapped as Mapped_, mapped_column,
    relationship
)
from datetime import datetime as dt_datetime, time as dt_time, date as dt_date, timedelta as dt_timedelta
from uuid import uuid4 as _uuid4


def _new_str_id() -> str:
    """Server-side surrogate for string primary keys named ``id``.

    A string PK has no autoincrement; without a default every INSERT dies
    on NOT NULL (the id is in nobody's hands: create schemas rightly
    exclude the server-owned ``id``, so the server must mint it).
    """
    return _uuid4().hex


def _configure_sqlite_engine(engine):
    """Enforce declared foreign keys on every SQLite connection."""
    if engine.dialect.name == "sqlite":
        @_sa_event.listens_for(engine, "connect")
        def _enable_foreign_keys(connection, _record):
            previous_autocommit = getattr(connection, "autocommit", None)
            if previous_autocommit is not None:
                connection.autocommit = True
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()
                if previous_autocommit is not None:
                    connection.autocommit = previous_autocommit


class Base(DeclarativeBase):
    pass



# Tables definition for many-to-many relationships
characters = Table_(
    "characters",
    Base.metadata,
    Column_("characters", ForeignKey_("scene.id"), primary_key=True),
    Column_("scenes", ForeignKey_("character.id"), primary_key=True),
)
subtitlevideo = Table_(
    "subtitlevideo",
    Base.metadata,
    Column_("subtitles", ForeignKey_("subtitle.id"), primary_key=True),
    Column_("subtitleVideo", ForeignKey_("video.id"), primary_key=True),
)
videos = Table_(
    "videos",
    Base.metadata,
    Column_("audioTracks", ForeignKey_("audiotrack.id"), primary_key=True),
    Column_("videos", ForeignKey_("video.id"), primary_key=True),
)

# Tables definition
class Video(Base):
    __tablename__ = "video"
    id: Mapped_[int] = mapped_column(primary_key=True)
    title: Mapped_[str] = mapped_column(String_(100))
    description: Mapped_[str] = mapped_column(String_(100))
    durationSeconds: Mapped_[int] = mapped_column(Integer_)
    thumbnailUrl: Mapped_[str] = mapped_column(String_(100))
    fileUrl: Mapped_[str] = mapped_column(String_(100))
    learningObjectives: Mapped_[str] = mapped_column(String_(100))
    creationDate: Mapped_[dt_datetime] = mapped_column(DateTime_)
    version: Mapped_[str] = mapped_column(String_(100))

class Subtitle(Base):
    __tablename__ = "subtitle"
    id: Mapped_[int] = mapped_column(primary_key=True)
    languageCode: Mapped_[str] = mapped_column(String_(100))
    format: Mapped_[str] = mapped_column(String_(100))
    fileUrl: Mapped_[str] = mapped_column(String_(100))
    isEnabledByDefault: Mapped_[bool] = mapped_column(Boolean_)

class Scene(Base):
    __tablename__ = "scene"
    id: Mapped_[int] = mapped_column(primary_key=True)
    sequenceIndex: Mapped_[int] = mapped_column(Integer_)
    title: Mapped_[str] = mapped_column(String_(100))
    startTimeSeconds: Mapped_[int] = mapped_column(Integer_)
    endTimeSeconds: Mapped_[int] = mapped_column(Integer_)
    storyboardNotes: Mapped_[str] = mapped_column(String_(100))
    video_id: Mapped_[int] = mapped_column(ForeignKey_("video.id"))

class PlayerSettings(Base):
    __tablename__ = "playersettings"
    id: Mapped_[int] = mapped_column(primary_key=True)
    volume: Mapped_[float] = mapped_column(Float_)
    isFullScreen: Mapped_[bool] = mapped_column(Boolean_)
    playbackSpeed: Mapped_[float] = mapped_column(Float_)
    activeLanguageCode: Mapped_[str] = mapped_column(String_(100))
    isMuted: Mapped_[bool] = mapped_column(Boolean_)
    currentTimeSeconds: Mapped_[int] = mapped_column(Integer_)
    isLooping: Mapped_[bool] = mapped_column(Boolean_)
    activeAudioTrack_id: Mapped_[int] = mapped_column(ForeignKey_("audiotrack.id"), nullable=True)
    activeSubtitle_id: Mapped_[int] = mapped_column(ForeignKey_("subtitle.id"), nullable=True)
    currentVideo_id: Mapped_[int] = mapped_column(ForeignKey_("video.id"), nullable=True)

class Character(Base):
    __tablename__ = "character"
    id: Mapped_[int] = mapped_column(primary_key=True)
    name: Mapped_[str] = mapped_column(String_(100))
    role: Mapped_[str] = mapped_column(String_(100))
    avatarImageUrl: Mapped_[str] = mapped_column(String_(100))
    voiceActor: Mapped_[str] = mapped_column(String_(100))

class AudioTrack(Base):
    __tablename__ = "audiotrack"
    id: Mapped_[int] = mapped_column(primary_key=True)
    languageCode: Mapped_[str] = mapped_column(String_(100))
    kind: Mapped_[str] = mapped_column(String_(100))
    fileUrl: Mapped_[str] = mapped_column(String_(100))
    durationSeconds: Mapped_[int] = mapped_column(Integer_)
    volumeLevelDefault: Mapped_[float] = mapped_column(Float_)
    isDefault: Mapped_[bool] = mapped_column(Boolean_)

class Animation(Base):
    __tablename__ = "animation"
    id: Mapped_[int] = mapped_column(primary_key=True)
    animationType: Mapped_[str] = mapped_column(String_(100))
    startTimeSeconds: Mapped_[int] = mapped_column(Integer_)
    endTimeSeconds: Mapped_[int] = mapped_column(Integer_)
    parameters: Mapped_[str] = mapped_column(String_(100))
    targetObjectId: Mapped_[Optional_[str]] = mapped_column(String_(100), nullable=True)
    scene_id: Mapped_[int] = mapped_column(ForeignKey_("scene.id"))
    targetCharacter_id: Mapped_[int] = mapped_column(ForeignKey_("character.id"), nullable=True)


#--- Relationships of the video table
Video.audioTracks: Mapped_[List_["AudioTrack"]] = relationship("AudioTrack", secondary=videos, back_populates="videos")
Video.playerSettings: Mapped_[List_["PlayerSettings"]] = relationship("PlayerSettings", back_populates="currentVideo", foreign_keys=[PlayerSettings.currentVideo_id])
Video.scenes: Mapped_[List_["Scene"]] = relationship("Scene", back_populates="video", foreign_keys=[Scene.video_id], cascade="all, delete-orphan")
Video.subtitles: Mapped_[List_["Subtitle"]] = relationship("Subtitle", secondary=subtitlevideo, back_populates="subtitleVideo")

#--- Relationships of the subtitle table
Subtitle.playerSettings: Mapped_[List_["PlayerSettings"]] = relationship("PlayerSettings", back_populates="activeSubtitle", foreign_keys=[PlayerSettings.activeSubtitle_id])
Subtitle.subtitleVideo: Mapped_[List_["Video"]] = relationship("Video", secondary=subtitlevideo, back_populates="subtitles")

#--- Relationships of the scene table
Scene.animations: Mapped_[List_["Animation"]] = relationship("Animation", back_populates="scene", foreign_keys=[Animation.scene_id], cascade="all, delete-orphan")
Scene.scenes: Mapped_[List_["Character"]] = relationship("Character", secondary=characters, back_populates="characters")

Scene.video: Mapped_["Video"] = relationship("Video", back_populates="scenes", uselist=False, foreign_keys=[Scene.video_id])

#--- Relationships of the playersettings table

PlayerSettings.activeAudioTrack: Mapped_["AudioTrack"] = relationship("AudioTrack", back_populates="playerSettings", uselist=False, foreign_keys=[PlayerSettings.activeAudioTrack_id])

PlayerSettings.activeSubtitle: Mapped_["Subtitle"] = relationship("Subtitle", back_populates="playerSettings", uselist=False, foreign_keys=[PlayerSettings.activeSubtitle_id])

PlayerSettings.currentVideo: Mapped_["Video"] = relationship("Video", back_populates="playerSettings", uselist=False, foreign_keys=[PlayerSettings.currentVideo_id])

#--- Relationships of the character table
Character.animations: Mapped_[List_["Animation"]] = relationship("Animation", back_populates="targetCharacter", foreign_keys=[Animation.targetCharacter_id])
Character.characters: Mapped_[List_["Scene"]] = relationship("Scene", secondary=characters, back_populates="scenes")

#--- Relationships of the audiotrack table
AudioTrack.playerSettings: Mapped_[List_["PlayerSettings"]] = relationship("PlayerSettings", back_populates="activeAudioTrack", foreign_keys=[PlayerSettings.activeAudioTrack_id])
AudioTrack.videos: Mapped_[List_["Video"]] = relationship("Video", secondary=videos, back_populates="audioTracks")

#--- Relationships of the animation table

Animation.scene: Mapped_["Scene"] = relationship("Scene", back_populates="animations", uselist=False, foreign_keys=[Animation.scene_id])

Animation.targetCharacter: Mapped_["Character"] = relationship("Character", back_populates="animations", uselist=False, foreign_keys=[Animation.targetCharacter_id])

# Database connection (override the default with the DATABASE_URL environment variable)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/Class_Diagram.db")  # SQLite connection
engine = create_engine(DATABASE_URL)
_configure_sqlite_engine(engine)

if __name__ == "__main__":
    # Create tables in the database only when this module is executed directly,
    # so importing it never touches the database as a side effect.
    if DATABASE_URL.startswith("sqlite"):
        os.makedirs("data", exist_ok=True)  # folder for the default SQLite database
    Base.metadata.create_all(engine, checkfirst=True)