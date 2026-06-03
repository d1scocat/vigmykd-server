from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar


T = TypeVar('T')


@dataclass
class ObtainStrategy(Generic[T]):
    mapper: Callable[[str], T]
    fallback: Callable[[], T]  # may raise
