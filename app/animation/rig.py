import math
from typing import Dict, Any, Tuple
from PIL import Image, ImageDraw
from app.animation.actions import CharacterTransform, VisemeMouthState


class CartoonCharacterRig:
    """
    Lightweight 2D Character Rig Renderer using PIL/Pillow layer compositing.
    Zero 3D overhead, zero heavy dependencies. Perfect for NVIDIA MX110 2GB & 8GB RAM.
    """

    def __init__(self, character_id: str = "cat", width: int = 400, height: int = 600):
        self.character_id = character_id
        self.width = width
        self.height = height

    def render_frame(self, transform: CharacterTransform) -> Image.Image:
        """Renders 2D character frame at current pose transform."""
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        center_x = self.width // 2
        center_y = self.height // 2

        # Color schemes based on character ID
        if "cat" in self.character_id.lower():
            body_color = (255, 165, 0, 255)  # Orange
            head_color = (255, 180, 50, 255)
        elif "robot" in self.character_id.lower():
            body_color = (0, 200, 255, 255)   # Cyan
            head_color = (180, 220, 255, 255)
        else:
            body_color = (138, 43, 226, 255)  # Purple
            head_color = (186, 85, 211, 255)

        # 1. Body
        body_box = [center_x - 60, center_y, center_x + 60, center_y + 160]
        draw.ellipse(body_box, fill=body_color, outline=(0, 0, 0, 255), width=4)

        # 2. Arms (waving transform)
        arm_offset = int(math.sin(math.radians(transform.arm_angle)) * 30)
        draw.line([center_x - 50, center_y + 40, center_x - 90, center_y + 80 + arm_offset], fill=body_color, width=16)
        draw.line([center_x + 50, center_y + 40, center_x + 90, center_y + 80 - arm_offset], fill=body_color, width=16)

        # 3. Head (jump/rotation transform)
        head_y = center_y - 70 + int(transform.rotation)
        head_box = [center_x - 70, head_y - 70, center_x + 70, head_y + 70]
        draw.ellipse(head_box, fill=head_color, outline=(0, 0, 0, 255), width=4)

        # 4. Eyes
        if transform.eye_state == "blinking":
            draw.line([center_x - 35, head_y - 15, center_x - 15, head_y - 15], fill=(0, 0, 0, 255), width=4)
            draw.line([center_x + 15, head_y - 15, center_x + 35, head_y - 15], fill=(0, 0, 0, 255), width=4)
        else:
            draw.ellipse([center_x - 40, head_y - 30, center_x - 10, head_y], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=3)
            draw.ellipse([center_x + 10, head_y - 30, center_x + 40, head_y], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=3)
            draw.ellipse([center_x - 28, head_y - 20, center_x - 18, head_y - 10], fill=(0, 0, 0, 255))
            draw.ellipse([center_x + 18, head_y - 20, center_x + 28, head_y - 10], fill=(0, 0, 0, 255))

        # 5. Viseme Mouth Shape
        mouth_y = head_y + 25
        self._draw_viseme_mouth(draw, center_x, mouth_y, transform.mouth_state)

        return img

    def _draw_viseme_mouth(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, mouth_state: VisemeMouthState):
        """Draws viseme mouth shape corresponding to phoneme lip sync state."""
        if mouth_state in (VisemeMouthState.A, VisemeMouthState.O):
            # Wide open mouth
            draw.ellipse([cx - 20, cy - 15, cx + 20, cy + 15], fill=(200, 30, 30, 255), outline=(0, 0, 0, 255), width=3)
        elif mouth_state in (VisemeMouthState.E, VisemeMouthState.I):
            # Wide smile mouth
            draw.rectangle([cx - 25, cy - 8, cx + 25, cy + 8], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=3)
        elif mouth_state in (VisemeMouthState.M_B_P, VisemeMouthState.REST):
            # Closed line mouth
            draw.line([cx - 20, cy, cx + 20, cy], fill=(0, 0, 0, 255), width=4)
        else:
            # Round mouth
            draw.ellipse([cx - 12, cy - 10, cx + 12, cy + 10], fill=(220, 50, 50, 255), outline=(0, 0, 0, 255), width=3)
