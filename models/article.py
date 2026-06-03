import hashlib
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator, AwareDatetime

class Article(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = ""
    url: str
    title: str
    body: str
    source: str
    published_at: AwareDatetime
    minhash_signature: tuple[int, ...] = ()
    is_duplicate: bool = False

    @model_validator(mode="after")
    def set_id(self) -> "Article":
        object.__setattr__(self, "id", hashlib.sha256(self.url.encode()).hexdigest())
        return self
