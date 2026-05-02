from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.auth.database import get_db
from app.auth.models import User

SECRET_KEY = "fx_alphalab_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

bearer_scheme = HTTPBearer()


def hash_password(password: str):
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(
        plain_password[:72],
        hashed_password
    )


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        email = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        db_user = db.query(User).filter(User.email == email).first()

        if not db_user:
            raise HTTPException(status_code=401, detail="User not found")

        return db_user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")