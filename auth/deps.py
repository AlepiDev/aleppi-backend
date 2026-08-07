from typing import Optional

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
# auto_error=False: no lanza 401 si falta el header, para poder resolver un
# usuario "opcional" en endpoints públicos que se comportan distinto si hay sesión.
security_optional = HTTPBearer(auto_error=False)


def _decode_user_or_none(token: str, session: Session) -> Optional[User]:
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
            return None

    except (JWTError, ValueError, TypeError):
        return None

    user = session.get(User, int(user_id))

    if not user or not user.is_active:
        return None

    return user


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

    user = _decode_user_or_none(credentials.credentials, session)

    if user is None:
        raise credentials_exception

    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    session: Session = Depends(get_session),
) -> Optional[User]:
    """
    Igual que get_current_user, pero nunca lanza: si no hay header, el token
    es inválido/expiró, o el usuario no existe/no está activo, devuelve None.
    Pensado para endpoints públicos que exponen datos extra si hay sesión.
    """
    if credentials is None:
        return None

    return _decode_user_or_none(credentials.credentials, session)


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
