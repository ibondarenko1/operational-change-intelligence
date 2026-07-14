import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.change import (
    ChangeRequestCreate,
    ChangeRequestResponse,
    ChangeRequestUpdate,
    RiskAssessmentResponse,
    SimilarHistoricalChangeResponse,
)
from app.services.change_requests import (
    ChangeRequestNotFoundError,
    create_change_request,
    delete_change_request,
    get_change_request,
    list_change_requests,
    update_change_request,
)
from app.services.risk_assessments import (
    RiskAssessmentNotFoundError,
    analyze_change_request,
    get_change_assessment,
)
from app.services.similarity import find_similar_changes

router = APIRouter(prefix="/api/v1/changes", tags=["changes"])


@router.post("", response_model=ChangeRequestResponse, status_code=status.HTTP_201_CREATED)
def create_change(payload: ChangeRequestCreate, db: Session = Depends(get_db)) -> ChangeRequestResponse:
    return create_change_request(db, payload)


@router.get("", response_model=list[ChangeRequestResponse])
def list_changes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ChangeRequestResponse]:
    return list(list_change_requests(db, skip=skip, limit=limit))


@router.get("/{change_id}", response_model=ChangeRequestResponse)
def get_change(change_id: uuid.UUID, db: Session = Depends(get_db)) -> ChangeRequestResponse:
    try:
        return get_change_request(db, change_id)
    except ChangeRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found") from exc


@router.post("/{change_id}/analyze", response_model=RiskAssessmentResponse)
def analyze_change(change_id: uuid.UUID, db: Session = Depends(get_db)) -> RiskAssessmentResponse:
    try:
        return analyze_change_request(db, change_id)
    except ChangeRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found") from exc


@router.get("/{change_id}/assessment", response_model=RiskAssessmentResponse)
def get_assessment(change_id: uuid.UUID, db: Session = Depends(get_db)) -> RiskAssessmentResponse:
    try:
        return get_change_assessment(db, change_id)
    except ChangeRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found") from exc
    except RiskAssessmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk assessment not found") from exc


@router.get("/{change_id}/similar", response_model=list[SimilarHistoricalChangeResponse])
def get_similar_changes(
    change_id: uuid.UUID,
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[SimilarHistoricalChangeResponse]:
    try:
        return find_similar_changes(db, change_id, limit=limit)
    except ChangeRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found") from exc


@router.patch("/{change_id}", response_model=ChangeRequestResponse)
def patch_change(
    change_id: uuid.UUID,
    payload: ChangeRequestUpdate,
    db: Session = Depends(get_db),
) -> ChangeRequestResponse:
    try:
        return update_change_request(db, change_id, payload)
    except ChangeRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{change_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_change(change_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    try:
        delete_change_request(db, change_id)
    except ChangeRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
