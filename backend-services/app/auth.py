from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth_service import auth_service
from app.db.models import Device, User, get_db

router = APIRouter(tags=["auth"])

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    device = await db.get(Device, form_data.username)
    if not device or not auth_service.verify_password(form_data.password, device.hashed_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect device ID or signature",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth_service.create_access_token(data={"sub": device.device_id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users/token")
async def login_for_user_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await db.execute(User.__table__.select().where(User.username == form_data.username))
    user = user.scalar_one_or_none()
    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth_service.create_access_token(data={"sub": user.username, "type": "user"})
    return {"access_token": access_token, "token_type": "bearer"}
