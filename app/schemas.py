from typing import Union, Dict, Any, Optional

from pydantic import BaseModel


class WSResponse(BaseModel):
    status: int
    type: str
    data: Optional[Any] = None
