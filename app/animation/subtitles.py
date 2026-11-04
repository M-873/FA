from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFont


class SubtitleOverlayGenerator:
    """Generates high-contrast subtitle text overlays positioned safely for 9:16 vertical videos."""

    @classmethod
    def overlay_subtitles(
        self,
        frame: Image.Image,
        text: str,
        font_size: int = 36,
    ) -> Image.Image:
        """Draws bold yellow subtitles with black outline at bottom safe area."""
        if not text:
            return frame

        draw = ImageDraw.Draw(frame)
        width, height = frame.size

        # Position: Bottom safe area (75% height)
        sub_y = int(height * 0.78)
        sub_x = width // 2

        # Draw dark semi-transparent background box
        box_padding = 15
        box_y1 = sub_y - 25
        box_y2 = sub_y + 35
        draw.rectangle([50, box_y1, width - 50, box_y2], fill=(0, 0, 0, 180))

        # Text with outline for maximum readability
        text_color = (255, 230, 0, 255)  # Bright Yellow
        outline_color = (0, 0, 0, 255)

        # Draw outline
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2)]:
            draw.text((sub_x + dx, sub_y + dy), text, fill=outline_color, anchor="mm")

        # Draw text
        draw.text((sub_x, sub_y), text, fill=text_color, anchor="mm")
        return frame
