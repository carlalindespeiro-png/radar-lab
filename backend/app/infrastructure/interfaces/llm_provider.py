from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: pass