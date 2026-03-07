"""POST /import — upload one or more hand history files."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import Engine

from api.deps import get_engine
from app.import_hands import import_hands

router = APIRouter()


@router.post("/import")
def import_files(
    files: list[UploadFile],
    engine: Engine = Depends(get_engine),
) -> dict:
    """Accept one or more hand history files and persist them.

    Returns aggregated totals across all uploaded files:
        {"imported": N, "skipped": M, "errors": [...]}
    """
    total_imported = 0
    total_skipped = 0
    all_errors: list[str] = []

    for upload in files:
        content = upload.file.read()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        result = import_hands(tmp_path, engine=engine)
        tmp_path.unlink(missing_ok=True)

        total_imported += result["imported"]
        total_skipped += result["skipped"]
        all_errors.extend(
            f"{upload.filename}: {e}" for e in result["errors"]
        )

    return {"imported": total_imported, "skipped": total_skipped, "errors": all_errors}
