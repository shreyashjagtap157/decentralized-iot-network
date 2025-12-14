from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, get_db
from app.schemas import UserCreate, UserResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await db.execute(User.__table__.select().where(User.username == user.username))
    if db_user.scalar():
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = auth_service.get_password_hash(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
