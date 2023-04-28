from typing import Union, Dict, Any

from pydantic import BaseModel


class WSResponse(BaseModel):
    status: int
    type: str
    data: Union[Dict[str, Any], BaseModel] = None
