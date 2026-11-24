"""Seed data for the cartoon-style Newton's three laws of motion lesson.

The lesson is the thing the whole application exists to play, so it is
seeded on first start: one Video, the three Scenes (inertia, F = m*a,
action-reaction), the cartoon Characters, AudioTracks and Subtitles in two
languages, and the PlayerSettings that drives the player.

Seeding is idempotent: it looks the lesson up by title and does nothing when
it is already there.
"""

import logging
from datetime import datetime

from sql_alchemy import (
    Animation,
    AudioTrack,
    Base,
    Character,
    PlayerSettings,
    Scene,
    Subtitle,
    Video,
    characters,
    subtitlevideo,
    videos,
)

logger = logging.getLogger(__name__)

LESSON_TITLE = "Newton's Three Laws of Motion - Cartoon Adventure"

# The cartoon video and its poster live next to the app so the player can
# stream them without an external host.
MEDIA_BASE = "/media"

LANGUAGES = [
    {
        "code": "en",
        "label": "English",
        "audio": {
            "fileUrl": f"{MEDIA_BASE}/audio/newtons-laws-en.mp3",
            "kind": "dubbed",
        },
        "subtitle": {
            "fileUrl": f"{MEDIA_BASE}/subtitles/newtons-laws-en.vtt",
            "format": "vtt",
        },
    },
    {
        "code": "es",
        "label": "Espanol",
        "audio": {
            "fileUrl": f"{MEDIA_BASE}/audio/newtons-laws-es.mp3",
            "kind": "dubbed",
        },
        "subtitle": {
            "fileUrl": f"{MEDIA_BASE}/subtitles/newtons-laws-es.vtt",
            "format": "vtt",
        },
    },
    {
        "code": "fr",
        "label": "Francais",
        "audio": {
            "fileUrl": f"{MEDIA_BASE}/audio/newtons-laws-fr.mp3",
            "kind": "dubbed",
        },
        "subtitle": {
            "fileUrl": f"{MEDIA_BASE}/subtitles/newtons-laws-fr.vtt",
            "format": "vtt",
        },
    },
    {
        "code": "de",
        "label": "Deutsch",
        "audio": {
            "fileUrl": f"{MEDIA_BASE}/audio/newtons-laws-de.mp3",
            "kind": "dubbed",
        },
        "subtitle": {
            "fileUrl": f"{MEDIA_BASE}/subtitles/newtons-laws-de.vtt",
            "format": "vtt",
        },
    },
    {
        "code": "lb",
        "label": "Lëtzebuergesch",
        "audio": {
            "fileUrl": f"{MEDIA_BASE}/audio/newtons-laws-lb.mp3",
            "kind": "dubbed",
        },
        "subtitle": {
            "fileUrl": f"{MEDIA_BASE}/subtitles/newtons-laws-lb.vtt",
            "format": "vtt",
        },
    },
    {
        "code": "pt",
        "label": "Portugues",
        "audio": {
            "fileUrl": f"{MEDIA_BASE}/audio/newtons-laws-pt.mp3",
            "kind": "dubbed",
        },
        "subtitle": {
            "fileUrl": f"{MEDIA_BASE}/subtitles/newtons-laws-pt.vtt",
            "format": "vtt",
        },
    },
]

CHARACTERS = [
    {
        "name": "Newton the Cartoon Fox",
        "role": "Teacher - explains the three laws with slapstick",
        "avatarImageUrl": f"{MEDIA_BASE}/characters/newton-fox.png",
        "voiceActor": "Sam Rivera",
    },
    {
        "name": "Inky the Ball",
        "role": "Recurring character - demonstrates inertia",
        "avatarImageUrl": f"{MEDIA_BASE}/characters/inky-ball.png",
        "voiceActor": "Riley Chen",
    },
    {
        "name": "Rocket the Robot",
        "role": "Recurring character - demonstrates action and reaction",
        "avatarImageUrl": f"{MEDIA_BASE}/characters/rocket-robot.png",
        "voiceActor": "Ava Okafor",
    },
]

SCENES = [
    {
        "sequenceIndex": 1,
        "title": "Law 1 - Inertia",
        "startTimeSeconds": 0,
        "endTimeSeconds": 60,
        "storyboardNotes": "Newton the Fox rides a skateboard and Inky the Ball refuses to move. "
        "A big sign reads: an object stays at rest or in motion unless a force acts on it.",
    },
    {
        "sequenceIndex": 2,
        "title": "Law 2 - Force equals Mass times Acceleration",
        "startTimeSeconds": 60,
        "endTimeSeconds": 120,
        "storyboardNotes": "Rocket the Robot pushes a heavy crate and then a light balloon. "
        "The force arrow shrinks as the mass grows; the F = m x a formula appears in a bubble.",
    },
    {
        "sequenceIndex": 3,
        "title": "Law 3 - Action and Reaction",
        "startTimeSeconds": 120,
        "endTimeSeconds": 180,
        "storyboardNotes": "Rocket fires a rocket and the rocket pushes back. "
        "Two cartoon planets bump into each other and both bounce away.",
    },
]

ANIMATIONS = [
    {
        "animationType": "slide",
        "startTimeSeconds": 5,
        "endTimeSeconds": 25,
        "parameters": "ease-in-out from x=0 to x=640, bounce at the end",
        "targetObjectId": "inky-ball",
        "targetCharacter": "Inky the Ball",
    },
    {
        "animationType": "explosion",
        "startTimeSeconds": 130,
        "endTimeSeconds": 150,
        "parameters": "particle burst, 24 particles, gravity 0.4",
        "targetObjectId": "rocket-robot",
        "targetCharacter": "Rocket the Robot",
    },
]


def seed_newtons_laws_lesson(session):
    """Create the lesson once. Returns the seeded Video, or None if it existed."""
    existing = session.query(Video).filter(Video.title == LESSON_TITLE).first()
    if existing is not None:
        return None

    video = Video(
        title=LESSON_TITLE,
        description=(
            "A cartoon adventure with Newton the Fox, Inky the Ball and Rocket the Robot. "
            "The three short scenes show, with slapstick and simple maths, why things keep "
            "moving, why heavy things are hard to push, and why every push is met with a push back."
        ),
        learningObjectives=(
            "By the end of the lesson students can: "
            "(1) state Newton's first law of motion and give a real life example of inertia; "
            "(2) use F = m x a to explain why the same force moves a light object faster than a heavy one; "
            "(3) explain Newton's third law with an everyday example such as swimming or walking."
        ),
        durationSeconds=180,
        thumbnailUrl=f"{MEDIA_BASE}/thumbnails/newtons-laws-poster.png",
        fileUrl=f"{MEDIA_BASE}/video/newtons-laws.mp4",
        creationDate=datetime.now(),
        version="1.0.0",
    )
    session.add(video)
    session.flush()

    # Characters (cartoons who appear in the lesson)
    character_rows = {}
    for spec in CHARACTERS:
        character = Character(
            name=spec["name"],
            role=spec["role"],
            avatarImageUrl=spec["avatarImageUrl"],
            voiceActor=spec["voiceActor"],
        )
        session.add(character)
        session.flush()
        character_rows[spec["name"]] = character

    # Scenes, each attached to the lesson video
    scene_rows = []
    for spec in SCENES:
        scene = Scene(
            sequenceIndex=spec["sequenceIndex"],
            title=spec["title"],
            startTimeSeconds=spec["startTimeSeconds"],
            endTimeSeconds=spec["endTimeSeconds"],
            storyboardNotes=spec["storyboardNotes"],
            video_id=video.id,
        )
        session.add(scene)
        session.flush()
        scene_rows.append(scene)

    # Every character appears in the scenes; link them through the association table.
    for scene in scene_rows:
        for character in character_rows.values():
            session.execute(
                characters.insert().values(characters=scene.id, scenes=character.id)
            )
    session.flush()

    # Animations inside the scenes
    animation_rows = []
    for spec in ANIMATIONS:
        scene = next(
            s
            for s in scene_rows
            if s.sequenceIndex == (1 if spec["targetObjectId"] == "inky-ball" else 3)
        )
        animation = Animation(
            animationType=spec["animationType"],
            startTimeSeconds=spec["startTimeSeconds"],
            endTimeSeconds=spec["endTimeSeconds"],
            parameters=spec["parameters"],
            targetObjectId=spec["targetObjectId"],
            scene_id=scene.id,
            targetCharacter_id=character_rows[spec["targetCharacter"]].id,
        )
        session.add(animation)
        session.flush()
        animation_rows.append(animation)

    # Audio tracks and subtitles, one pair per language, all linked to the video
    audio_tracks = []
    subtitles = []
    for index, language in enumerate(LANGUAGES):
        is_default = index == 0
        audio_track = AudioTrack(
            languageCode=language["code"],
            kind=language["audio"]["kind"],
            fileUrl=language["audio"]["fileUrl"],
            durationSeconds=video.durationSeconds,
            volumeLevelDefault=1.0,
            isDefault=is_default,
        )
        session.add(audio_track)
        session.flush()
        audio_tracks.append(audio_track)

        subtitle = Subtitle(
            languageCode=language["code"],
            format=language["subtitle"]["format"],
            fileUrl=language["subtitle"]["fileUrl"],
            isEnabledByDefault=is_default,
        )
        session.add(subtitle)
        session.flush()
        subtitles.append(subtitle)

    for audio_track in audio_tracks:
        session.execute(
            videos.insert().values(videos=video.id, audioTracks=audio_track.id)
        )
    for subtitle in subtitles:
        session.execute(
            subtitlevideo.insert().values(subtitleVideo=video.id, subtitles=subtitle.id)
        )
    session.flush()

    # The player settings the app starts from
    player_settings = PlayerSettings(
        volume=0.8,
        isFullScreen=False,
        playbackSpeed=1.0,
        activeLanguageCode=LANGUAGES[0]["code"],
        isMuted=False,
        currentTimeSeconds=0,
        isLooping=False,
        activeAudioTrack_id=audio_tracks[0].id,
        activeSubtitle_id=subtitles[0].id,
        currentVideo_id=video.id,
    )
    session.add(player_settings)
    session.commit()

    logger.info(
        "Seeded Newton's three laws lesson: video=%s, scenes=%s, characters=%s, languages=%s",
        video.id,
        len(scene_rows),
        len(character_rows),
        len(LANGUAGES),
    )
    return video
