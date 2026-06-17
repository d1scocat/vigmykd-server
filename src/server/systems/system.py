from abc import ABC, abstractmethod
from typing import Generic, TypeVar


Subject = TypeVar('Subject')


class System(ABC, Generic[Subject]):
    @abstractmethod
    def act_on(self, sub: Subject, *args, **kwargs):
        pass
