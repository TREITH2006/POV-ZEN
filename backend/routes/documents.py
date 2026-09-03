from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from auth.dependencies import Identity, require_group_member, require_owner
from database import get_db
from schemas.document import DocumentOut
from services import document_service
from services.storage_service import resolve_path

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(
    title: str = Form(..., min_length=1, max_length=150),
    category: str = Form(default="other", max_length=50),
    file: UploadFile = File(...),
    identity: Identity = Depends(require_owner),
    db: Session = Depends(get_db),
):
    return document_service.upload_document(db, identity, title, category, file)


@router.get("", response_model=list[DocumentOut])
def list_documents(identity: Identity = Depends(require_group_member), db: Session = Depends(get_db)):
    return document_service.list_documents(db, identity)


@router.get("/{document_id}/file")
def get_document_file(
    document_id: str, identity: Identity = Depends(require_group_member), db: Session = Depends(get_db)
):
    document = document_service.get_owned_document(db, identity, document_id)
    return FileResponse(resolve_path(document.file_path))


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, identity: Identity = Depends(require_owner), db: Session = Depends(get_db)):
    document_service.delete_document(db, identity, document_id)
