from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.services.auth_service import auth_service
from app.db.models import Device, User, get_db
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_device(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Device:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    device_id = auth_service.verify_token(token, credentials_exception)
    device = await db.get(Device, device_id)
    if device is None:
        raise credentials_exception
    return device

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = auth_service.verify_token(token, credentials_exception)
    if payload.get("type") != "user":
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = await db.execute(User.__table__.select().where(User.username == username))
    user = user.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user
