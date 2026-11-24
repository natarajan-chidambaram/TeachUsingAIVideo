from datetime import datetime, date, time
from typing import Any, List, Optional, Union, Set
from enum import Enum
from pydantic import BaseModel, field_validator


############################################
# Enumerations are defined here
############################################

############################################
# Classes are defined here
############################################
class VideoCreate(BaseModel):
    creationDate: datetime
    description: str
    durationSeconds: int
    fileUrl: str
    learningObjectives: str
    thumbnailUrl: str
    title: str
    version: str
    playerSettings: Optional[List[int]] = None  # 1:N Relationship
    subtitles: Optional[List[int]] = None  # N:M Relationship (optional)
    scenes: Optional[List[int]] = None  # 1:N Relationship
    audioTracks: Optional[List[int]] = None  # N:M Relationship (optional)


class SubtitleCreate(BaseModel):
    fileUrl: str
    format: str
    isEnabledByDefault: bool
    languageCode: str
    playerSettings: Optional[List[int]] = None  # 1:N Relationship
    subtitleVideo: Optional[List[int]] = None  # N:M Relationship (optional)


class SceneCreate(BaseModel):
    endTimeSeconds: int
    sequenceIndex: int
    startTimeSeconds: int
    storyboardNotes: str
    title: str
    scenes: Optional[List[int]] = None  # N:M Relationship (optional)
    animations: Optional[List[int]] = None  # 1:N Relationship
    video: int  # N:1 Relationship (mandatory)


class PlayerSettingsCreate(BaseModel):
    activeLanguageCode: str
    currentTimeSeconds: int
    isFullScreen: bool
    isLooping: bool
    isMuted: bool
    playbackSpeed: float
    volume: float
    activeAudioTrack: Optional[int] = None  # N:1 Relationship (optional)
    activeSubtitle: Optional[int] = None  # N:1 Relationship (optional)
    currentVideo: Optional[int] = None  # N:1 Relationship (optional)


class CharacterCreate(BaseModel):
    avatarImageUrl: str
    name: str
    role: str
    voiceActor: str
    characters: Optional[List[int]] = None  # N:M Relationship (optional)
    animations: Optional[List[int]] = None  # 1:N Relationship


class AudioTrackCreate(BaseModel):
    durationSeconds: int
    fileUrl: str
    isDefault: bool
    kind: str
    languageCode: str
    volumeLevelDefault: float
    playerSettings: Optional[List[int]] = None  # 1:N Relationship
    videos: Optional[List[int]] = None  # N:M Relationship (optional)


class AnimationCreate(BaseModel):
    animationType: str
    endTimeSeconds: int
    parameters: str
    startTimeSeconds: int
    targetObjectId: Optional[str] = None
    scene: int  # N:1 Relationship (mandatory)
    targetCharacter: Optional[int] = None  # N:1 Relationship (optional)


