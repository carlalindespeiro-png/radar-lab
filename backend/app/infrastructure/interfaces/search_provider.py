from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]: pass