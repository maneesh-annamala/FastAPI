from contextlib import asynccontextmanager
from typing import Annotated

from core.config import settings
from database import engine, get_db
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import *
from routers.posts import router as posts_router
from routers.users import router as users_router
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException as StarletteExceptions


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # shutdown code
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


template = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(users_router)
app.include_router(posts_router)

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: db_dependency):
    count_result = await db.execute(select(func.count()).select_from(Posts))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Posts)
        .options(
            selectinload(Posts.author),
            selectinload(Posts.comments).selectinload(Comment.comment_author),
        )
        .order_by(Posts.date_posted.desc())
        .limit(settings.max_posts_per_user)
    )
    posts = result.scalars().all()

    has_more = len(posts) < total

    return template.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "posts": posts,
            "title": "Home",
            "has_more": has_more,
            "limit": settings.max_posts_per_user,
            "total": total,
        },
    )


@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(request: Request, post_id: int, db: db_dependency):
    result = await db.execute(
        select(Posts)
        .options(
            selectinload(Posts.author),
            selectinload(Posts.comments).selectinload(Comment.comment_author),
        )
        .where(Posts.id == post_id)
    )
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return template.TemplateResponse(
            request=request,
            name="post.html",
            context={"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: db_dependency,
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
        .where(Posts.user_id == user_id)
        .order_by(Posts.date_posted.desc())
        .limit(settings.max_posts_per_user)
    )
    posts = result.scalars().all()

    has_more = len(posts) < total
    return template.TemplateResponse(
        request=request,
        name="user_posts.html",
        context={
            "posts": posts,
            "user": user,
            "title": f"{user.username}'s Posts",
            "has_more": has_more,
            "total": total,
            "limit": settings.max_posts_per_user,
        },
    )


## login and register template_routes
@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return template.TemplateResponse(
        request,
        "login.html",
        {"title": "Login"},
    )


@app.get("/register", include_in_schema=False)
async def register_page(request: Request):
    return template.TemplateResponse(
        request,
        "register.html",
        {"title": "Register"},
    )


@app.get("/account", include_in_schema=False)
async def account_page(request: Request):
    return template.TemplateResponse(
        request,
        "account.html",
        {"title": "Account"},
    )


@app.get("/forgot-password", include_in_schema=False)
async def forgot_password_page(request: Request):
    return template.TemplateResponse(
        request, "forgot_password.html", {"title": "Forgot Password"}
    )


@app.get("/reset-password", include_in_schema=False)
async def reset_password_page(request: Request):
    response = template.TemplateResponse(
        request, "reset_password.html", {"title": "Reset Password"}
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(StarletteExceptions)
async def general_httpexception_handler(request: Request, exe: StarletteExceptions):

    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exe)

    message = (
        exe.detail
        if exe.detail
        else "An error occurred. Please check your request and try again."
    )
    return template.TemplateResponse(
        name="error.html",
        request=request,
        context={
            "status_code": exe.status_code,
            "title": exe.status_code,
            "message": message,
        },
        status_code=exe.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exception: RequestValidationError
):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)
    return template.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
