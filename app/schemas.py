from typing import Optional, Union, List, Dict, Any

from pydantic import BaseModel, validator


class WSResponse(BaseModel):
    status: int
    type: str
    data: Union[Dict[str, Any], BaseModel] = None
