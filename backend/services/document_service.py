from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from auth.dependencies import Identity
from models.document import Document
from services.storage_service import ALLOWED_DOCUMENT_TYPES, UnsupportedFileError, delete_upload, save_upload


def upload_document(db: Session, identity: Identity, title: str, category: str, file: UploadFile) -> Document:
    contents = file.file.read()
    try:
        file_path = save_upload(file, contents, subfolder="documents", allowed_types=ALLOWED_DOCUMENT_TYPES)
    except UnsupportedFileError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    document = Document(
        group_id=identity.group_id,
        owner_id=identity.ref_id,
        title=title,
        category=category,
        file_path=file_path,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session, identity: Identity) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.group_id == identity.group_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


def get_owned_document(db: Session, identity: Identity, document_id: str) -> Document:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.group_id == identity.group_id)
        .first()
    )
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


def delete_document(db: Session, identity: Identity, document_id: str) -> None:
    document = get_owned_document(db, identity, document_id)
    delete_upload(document.file_path)
    db.delete(document)
    db.commit()
