# from contextlib import asynccontextmanager

# from fastapi.exception_handlers import http_exception_handler,request_validation_exception_handler
from datetime import UTC, datetime, timedelta
from typing import Annotated

from auth import (
    create_access_token,
    current_user,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    oauth2_scheme,
    verify_access_token,
    verify_password,
)
from botocore.exceptions import ClientError
from core.config import settings
from database import get_db
from email_utils import send_password_reset_email
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from image_utils import (
    delete_profile_image,
    process_profile_image,
    upload_profile_image,
)
from models import *
from PIL import UnidentifiedImageError
from schemas import *
from sqlalchemy import delete as sqlalchemy_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/api/users", tags=["Users"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: db_dependency):
    user_name = await db.execute(
        select(Users).where(func.lower(Users.username) == user.username.lower())
    )
    existing_user = user_name.scalars().first()
    user_email = await db.execute(
        select(Users).where(func.lower(Users.email) == user.email.lower())
    )
    existing_email = user_email.scalars().first()
    if existing_user or existing_email:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Email already registered",
        )
    password = hash_password(user.password)
    new_user = Users(
        username=user.username, email=user.email.lower(), password=password
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user, attribute_names=["posts"])
    return new_user


## login_for_access_token
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,
):
    # Look up user by email (case-insensitive)
    # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
    result = await db.execute(
        select(Users).where(
            func.lower(Users.email) == form_data.username.lower(),
        ),
    )
    user = result.scalars().first()

    # Verify user exists and password is correct
    # Don't reveal which one failed (security best practice)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("", response_model=list[UserPublic])
async def get_users(db: db_dependency, current_user: current_user):
    result = await db.execute(select(Users).options(selectinload(Users.posts)))
    users = result.scalars().all()
    return users


@router.get("/current_user", response_model=UserPrivate)
async def get_current_user(current_user: current_user):
    return current_user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Users).where(
            func.lower(Users.email) == request_data.email.lower(),
        ),
    )
    user = result.scalars().first()

    if user:
        await db.execute(
            sqlalchemy_delete(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
            ),
        )

        token = generate_reset_token()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.reset_token_expire_minutes
        )

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username=user.username,
            token=token,
        )

    return {
        "message": "If an account exists with this email, you will receive password reset instructions."
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    token_hash = hash_reset_token(request_data.token)

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
        )
    )
    reset_token = result.scalars().first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if reset_token.expires_at < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    result = await db.execute(
        select(Users).where(Users.id == reset_token.user_id),
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.password = hash_password(request_data.new_password)

    await db.execute(
        sqlalchemy_delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
        ),
    )

    await db.commit()
    return {
        "message": "Password reset successfully. You can now log in with your new password."
    }


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: current_user,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(password_data.current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password = hash_password(password_data.new_password)

    await db.execute(
        sqlalchemy_delete(PasswordResetToken).where(
            PasswordResetToken.user_id == current_user.id,
        ),
    )
    await db.commit()
    return {"message": "Password changed successfully"}


@router.get("/{user_id}/posts", response_model=PaginatedPostsResponse)
async def get_user_posts(
    user_id: int,
    db: db_dependency,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    result = await db.execute(select(Users).where(Users.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    count_result = await db.execute(
        select(func.count()).select_from(Posts).where(Posts.user_id == user.id)
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(Posts)
        .options(
            selectinload(Posts.author),
            selectinload(Posts.comments).selectinload(Comment.comment_author),
        )
        .where(Posts.user_id == user.id)
        .order_by(Posts.date_posted.desc())
        .offset(skip)
        .limit(limit)
    )
    posts = result.scalars().all()
    return PaginatedPostsResponse(
        posts=[PostResponse.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(posts)) < total,
    )


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(
    user_id: int, current_user: current_user, user_update: UserUpdate, db: db_dependency
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Un-Authorized Action"
        )
    if (
        user_update.username is not None
        and user_update.username.lower() != current_user.username.lower()
    ):
        result = await db.execute(
            select(Users).where(
                func.lower(Users.username) == user_update.username.lower()
            )
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )
    if (
        user_update.email is not None
        and user_update.email.lower() != current_user.email.lower()
    ):
        result = await db.execute(
            select(Users).where(func.lower(Users.email) == user_update.email.lower())
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
    if user_update.username is not None:
        current_user.username = user_update.username
    if user_update.email is not None:
        current_user.email = user_update.email.lower()
    await db.commit()
    await db.refresh(current_user, attribute_names=["posts"])
    return current_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, current_user: current_user, db: db_dependency):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Un-Authorized Action"
        )
    old_filename = current_user.image_file
    await db.delete(current_user)
    await db.commit()
    if old_filename:
        await delete_profile_image(old_filename)


# upload profile picture
@router.patch("/{user_id}/picture", response_model=UserPrivate)
async def upload_profile_picture(
    user_id: int, file: UploadFile, current_user: current_user, db: db_dependency
):

    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's picture",
        )

    content = await file.read()

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_upload_size_bytes // (1024 * 1024)}MB",
        )

    try:
        processed_bytes, new_filename = await run_in_threadpool(
            process_profile_image, content
        )
    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Please upload a valid image (JPEG, PNG, GIF, WebP).",
        ) from err

    try:
        await upload_profile_image(processed_bytes, new_filename)
    except ClientError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile picture",
        ) from err

    old_filename = current_user.image_file

    current_user.image_file = new_filename
    await db.commit()
    await db.refresh(current_user)
    if old_filename:
        await delete_profile_image(old_filename)
    return current_user


@router.delete("/{user_id}/picture", response_model=UserPrivate)
async def delete_profile_picture(
    user_id: int, current_user: current_user, db: db_dependency
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user's picture",
        )
    old_filename = current_user.image_file

    if old_filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete",
        )

    current_user.image_file = None

    await db.commit()
    await db.refresh(current_user)
    if old_filename:
        await delete_profile_image(old_filename)
    return current_user
