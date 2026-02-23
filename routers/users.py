from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import os
import shutil
from pathlib import Path

from database import get_db
from models import User, UserSettings
from schemas import (
    UserResponse, UserUpdate, PasswordChange,
    UserSettingsUpdate, UserSettingsResponse
)
from security import get_current_user, hash_password, verify_password
from config import settings

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
        user_update: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update user profile"""
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user_update.email

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
        password_data: PasswordChange,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Change user password"""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new password
    if len(password_data.new_password) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
        )

    # Update password
    current_user.hashed_password = hash_password(password_data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/upload-profile-picture")
async def upload_profile_picture(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Upload or update profile picture"""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG images are allowed"
        )

    # Create upload directory if not exists
    upload_dir = Path(settings.UPLOAD_DIR) / "profile_pictures"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    filename = f"user_{current_user.id}.{file_extension}"
    file_path = upload_dir / filename

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Update user profile picture path
    current_user.profile_picture = str(file_path)
    db.commit()

    return {
        "message": "Profile picture uploaded successfully",
        "file_path": str(file_path)
    }


@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get user settings"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    if not settings:
        # Create default settings if not exists
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.put("/settings", response_model=UserSettingsResponse)
async def update_settings(
        settings_update: UserSettingsUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update user settings"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    # Update settings
    if settings_update.currency is not None:
        settings.currency = settings_update.currency
    if settings_update.date_format is not None:
        settings.date_format = settings_update.date_format
    if settings_update.notification_enabled is not None:
        settings.notification_enabled = settings_update.notification_enabled
    if settings_update.budget_alerts is not None:
        settings.budget_alerts = settings_update.budget_alerts
    if settings_update.theme is not None:
        settings.theme = settings_update.theme

    db.commit()
    db.refresh(settings)
    return settings