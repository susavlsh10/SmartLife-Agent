from fastapi import APIRouter, HTTPException, status, Header, Depends
from typing import Optional
from sqlalchemy.orm import Session
from app.models import UserSignup, UserLogin, AuthResponse, UserResponse
from app.database import get_db
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    get_user_by_email,
    get_user_by_id,
    create_user,
)

router = APIRouter()


@router.post("/signup", response_model=AuthResponse)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """Create a new user account"""
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password and create user
    password_hash = hash_password(user_data.password)
    user = create_user(db, user_data.email, password_hash, user_data.name)

    # Create access token
    token = create_access_token(data={"sub": user.id, "email": user.email})

    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email, name=user.name),
        token=token,
    )


@router.post("/login", response_model=AuthResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password"""
    # Get user from database
    user = get_user_by_email(db, user_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Verify password
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Create access token
    token = create_access_token(data={"sub": user.id, "email": user.email})

    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email, name=user.name),
        token=token,
    )


@router.get("/verify", response_model=UserResponse)
async def verify_token_endpoint(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
):
    """Verify authentication token and return user info"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    # Verify token
    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Get user from database
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return UserResponse(id=user.id, email=user.email, name=user.name)

