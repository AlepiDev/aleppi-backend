from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import Session

from database import get_session
from models import User

SECRET_KEY = "CAMBIA_ESTA_CLAVE_SUPER_SECRETA"
ALGORITHM = "HS256"

# Esquema HTTP Bearer para Swagger
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    """
    Obtiene el usuario actual a partir del JWT enviado en el header:
    Authorization: Bearer <token>
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience="aleppi-frontend",
            issuer="aleppi-backend",
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = session.get(User, int(user_id))

    if not user or not user.is_active:
        raise credentials_exception

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Solo permite acceso a usuarios con role = 1 (admin).
    """
    if current_user.role != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los admins pueden realizar esta acción",
        )

    return current_user
