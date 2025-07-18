from pydantic import BaseModel, computed_field, field_validator, Field
from solara import Reactive
from cosmicds.state import BaseState, GLOBAL_STATE, BaseLocalState
import solara
import datetime
from functools import cached_property
from solara.toestand import Ref
from typing import Callable, Tuple, Optional

from cosmicds.logger import setup_logger

logger = setup_logger("TEMPO STATE")


class LocalState(BaseLocalState):
    title: str = "Tempo"
    story_id: str = "tempo"
    last_route: Optional[str] = None
    route_restored: bool = Field(False, exclude=True)


LOCAL_STATE = solara.reactive(LocalState())
