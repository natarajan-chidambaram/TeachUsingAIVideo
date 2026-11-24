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


@router.get("/language/", response_model=None, tags=["Language"])
def get_all_language(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    return database.query(Language).all()


@router.get("/language/count/", response_model=None, tags=["Language"])
def get_count_language(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Language entities"""
    count = database.query(Language).count()
    return {"count": count}


@router.get("/language/paginated/", response_model=None, tags=["Language"])
def get_paginated_language(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Language entities"""
    total = database.query(Language).count()
    language_list = database.query(Language).offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": language_list
    }
@router.get("/language/search/", response_model=None, tags=["Language"])
def search_language(
    code: str = None,
    isSupportedForAudio: bool = None,
    isSupportedForSubtitles: bool = None,
    name: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Language entities by attributes"""
    query = database.query(Language)

    if code is not None:
        query = query.filter(Language.code.ilike(f"%{code}%"))
    if isSupportedForAudio is not None:
        query = query.filter(Language.isSupportedForAudio == isSupportedForAudio)
    if isSupportedForSubtitles is not None:
        query = query.filter(Language.isSupportedForSubtitles == isSupportedForSubtitles)
    if name is not None:
        query = query.filter(Language.name.ilike(f"%{name}%"))

    results = query.all()
    return results


@router.get("/language/{language_id}/", response_model=None, tags=["Language"])
async def get_language(language_id: int, database: Session = Depends(get_db)) -> Language:
    db_language = database.query(Language).filter(Language.id == language_id).first()
    if db_language is None:
        raise HTTPException(status_code=404, detail="Language not found")

    response_data = {
        "language": db_language,
}
    return response_data



@router.post("/language/", response_model=None, tags=["Language"])
async def create_language(language_data: LanguageCreate, database: Session = Depends(get_db)) -> Language:


    db_language = Language(
        code=language_data.code,        isSupportedForAudio=language_data.isSupportedForAudio,        isSupportedForSubtitles=language_data.isSupportedForSubtitles,        name=language_data.name        )

    database.add(db_language)
    database.flush()
    database.refresh(db_language)





    database.commit()
    database.refresh(db_language)
    return db_language


@router.post("/language/bulk/", response_model=None, tags=["Language"])
async def bulk_create_language(items: list[LanguageCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Language entities at once"""
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_language = Language(
                code=item_data.code,                isSupportedForAudio=item_data.isSupportedForAudio,                isSupportedForSubtitles=item_data.isSupportedForSubtitles,                name=item_data.name            )
            database.add(db_language)
            database.flush()  # Get ID without committing
            created_items.append(db_language.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of Language failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Language entities"
    }


@router.delete("/language/bulk/", response_model=None, tags=["Language"])
async def bulk_delete_language(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Language entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_language = database.query(Language).filter(Language.id == item_id).first()
        if db_language:
            conflict = language_delete_conflict(db_language)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete Language " + str(item_id) + ": " + conflict)
            database.delete(db_language)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Language entities"
    }

@router.put("/language/{language_id}/", response_model=None, tags=["Language"])
async def update_language(language_id: int, language_data: LanguageCreate, database: Session = Depends(get_db)) -> Language:
    db_language = database.query(Language).filter(Language.id == language_id).first()
    if db_language is None:
        raise HTTPException(status_code=404, detail="Language not found")

    setattr(db_language, 'code', language_data.code)
    setattr(db_language, 'isSupportedForAudio', language_data.isSupportedForAudio)
    setattr(db_language, 'isSupportedForSubtitles', language_data.isSupportedForSubtitles)
    setattr(db_language, 'name', language_data.name)
    database.commit()
    database.refresh(db_language)

    return db_language


def language_delete_conflict(db_language, deleting=None, wholes=()):
    """Why this Language cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_language)
        deleting = [db_language] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    return None


@router.delete("/language/{language_id}/", response_model=None, tags=["Language"])
async def delete_language(language_id: int, database: Session = Depends(get_db)):
    db_language = database.query(Language).filter(Language.id == language_id).first()
    if db_language is None:
        raise HTTPException(status_code=404, detail="Language not found")
    conflict = language_delete_conflict(db_language)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete Language " + str(language_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_language = {
        attr.key: getattr(db_language, attr.key)
        for attr in db_language.__mapper__.column_attrs
    }
    database.delete(db_language)
    database.commit()
    return deleted_language



