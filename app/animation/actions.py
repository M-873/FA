from enum import Enum
from typing import Dict, Tuple, List
from pydantic import BaseModel, Field


class CharacterAction(str, Enum):
    IDLE = "idle"
    WALK = "walk"
    TALK = "talk"
    BLINK = "blink"
    WAVE = "wave"
    JUMP = "jump"
    HEAD_TURN = "head_turn"


class VisemeMouthState(str, Enum):
    REST = "REST"
    A = "A"
    E = "E"
    I = "I"
    O = "O"
    U = "U"
    M_B_P = "M_B_P"
    F_V = "F_V"
    L = "L"
    S_Z = "S_Z"
    SH_CH = "SH_CH"
    TH = "TH"
    W_Q = "W_Q"


class CharacterTransform(BaseModel):
    """2D Character pose transform coordinates and angles."""

    pos_x: float = Field(default=0.5, description="Normalized X position (0.0 to 1.0)")
    pos_y: float = Field(default=0.7, description="Normalized Y position (0.0 to 1.0)")
    scale: float = Field(default=1.0, description="Scale factor")
    rotation: float = Field(default=0.0, description="Head/body rotation angle in degrees")
    arm_angle: float = Field(default=0.0, description="Arm rotation angle")
    mouth_state: VisemeMouthState = Field(default=VisemeMouthState.REST, description="Current lip sync mouth shape")
    eye_state: str = Field(default="open", description="Eye shape: open, closed, blinking, surprised")
