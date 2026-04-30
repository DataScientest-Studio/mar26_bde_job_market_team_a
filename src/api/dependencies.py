from typing import Annotated, Iterator

from fastapi import Depends
from sqlmodel import Session

from src.database import get_engine


def get_db_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


DbSession = Annotated[Session, Depends(get_db_session)]
