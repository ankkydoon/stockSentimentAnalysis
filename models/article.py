import hashlib
from datetime import datetime
from pydantic import BaseModel, model_validator


class Article(BaseModel):
    id: str = ""
    url: str
    title: str
    body: str
    source: str
    published_at: datetime
    minhash_signature: list[int] = []
    is_duplicate: bool = False

    @model_validator(mode="after")
    def set_id(self) -> "Article":
        if not self.id:
            self.id = hashlib.sha256(self.url.encode()).hexdigest()
        return self
