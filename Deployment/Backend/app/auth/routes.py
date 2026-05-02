import random
import traceback
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .email_service import send_verification_email, send_welcome_email
from .models import User
from .schemas import Token, UserCreate, UserLogin, UserResponse, VerifyCode
from .security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
def register(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        existing_email = db.query(User).filter(User.email == user.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")

        existing_username = db.query(User).filter(User.username == user.username).first()
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")

        code = str(random.randint(100000, 999999))
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hash_password(user.password),
            is_verified=0,
            verification_code=code,
            verification_code_expires_at=expires_at,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        background_tasks.add_task(
            send_verification_email,
            new_user.email,
            new_user.username,
            code,
        )

        return new_user

    except HTTPException:
        raise

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify")
def verify_email(payload: VerifyCode, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.email == payload.email).first()

        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        if db_user.is_verified == 1:
            return {"message": "Account already verified"}

        if db_user.verification_code != payload.code:
            raise HTTPException(status_code=400, detail="Invalid verification code")

        if db_user.verification_code_expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Verification code expired")

        db_user.is_verified = 1
        db_user.verification_code = None
        db_user.verification_code_expires_at = None

        db.commit()

        send_welcome_email(
        db_user.email,
        db_user.username
)

        return {"message": "Account verified successfully"}

    except HTTPException:
        raise

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.email == user.email).first()

        if not db_user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(user.password, db_user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if db_user.is_verified == 0:
            raise HTTPException(
                status_code=403,
                detail="Please verify your email before logging in",
            )

        access_token = create_access_token(
    data={
        "sub": db_user.email,
        "username": db_user.username,
        "user_id": db_user.id,
    }
)

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    except HTTPException:
        raise

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "is_verified": current_user.is_verified,
    }
def get_me(current_user=Depends(get_current_user)):
    return current_user