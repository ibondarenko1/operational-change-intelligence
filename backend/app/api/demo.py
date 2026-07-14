from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services.demo_assets import seed_demo_assets
from app.services.historical_changes import seed_historical_changes

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


class SeedDemoResponse(BaseModel):
    inserted: int
    updated: int
    total: int
    assets_inserted: int
    assets_updated: int
    assets_total: int
    dependencies_inserted: int
    dependencies_updated: int
    dependencies_total: int


@router.post("/seed", response_model=SeedDemoResponse)
def seed_demo_data(db: Session = Depends(get_db)) -> SeedDemoResponse:
    if not get_settings().demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo seeding is disabled. Set DEMO_MODE=true to enable it.",
        )

    historical_result = seed_historical_changes(db)
    asset_result = seed_demo_assets(db)
    return SeedDemoResponse(**historical_result, **asset_result)
