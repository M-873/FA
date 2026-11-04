import os
from typing import List, Dict, Any
from PIL import Image, ImageDraw
from app.animation.actions import CharacterTransform, VisemeMouthState
from app.animation.rig import CartoonCharacterRig
from app.animation.lip_sync import VisemeLipSyncGenerator
from app.animation.subtitles import SubtitleOverlayGenerator
from app.hardware.profiles import RenderSettings
from app.utils.logging import logger


class CartoonAnimationEngine:
    """
    Lightweight 2D Cartoon Animation Engine.
    Sequentially renders 2D frames at configured resolution (720x1280 or 1080x1920) and FPS.
    """

    def __init__(self, render_settings: RenderSettings):
        self.settings = render_settings
        self.width = render_settings.resolution_width
        self.height = render_settings.resolution_height
        self.fps = render_settings.fps

    def render_scene_frames(
        self,
        script: Dict[str, Any],
        scene_plan: Dict[str, Any],
        output_dir: str,
    ) -> List[str]:
        """
        Renders complete frame sequence as JPEG/PNG files in output_dir.
        Returns list of generated frame filepaths.
        """
        logger.info(f"Rendering 2D Cartoon frames ({self.width}x{self.height} @ {self.fps} FPS)...")
        os.makedirs(output_dir, exist_ok=True)

        dialogues = script.get("dialogues", [])
        total_duration = min(self.settings.max_duration_seconds, script.get("duration", 12))
        total_frames = int(total_duration * self.fps)

        # Create character rigs
        cat_rig = CartoonCharacterRig("cat", width=350, height=500)
        robot_rig = CartoonCharacterRig("robot", width=350, height=500)

        # Generate lip sync timelines for dialogue lines
        dial_1 = dialogues[0]["text"] if len(dialogues) > 0 else ""
        dial_2 = dialogues[1]["text"] if len(dialogues) > 1 else ""

        half_frames = total_frames // 2
        lip_timeline_1 = VisemeLipSyncGenerator.generate_viseme_timeline(dial_1, total_duration / 2, self.fps)
        lip_timeline_2 = VisemeLipSyncGenerator.generate_viseme_timeline(dial_2, total_duration / 2, self.fps)

        frame_paths: List[str] = []

        for frame_idx in range(total_frames):
            # Background Canvas
            frame_bg = Image.new("RGB", (self.width, self.height), color=(20, 28, 45))
            draw_bg = ImageDraw.Draw(frame_bg)

            # Draw 2D Room/Laboratory background elements
            draw_bg.rectangle([0, int(self.height * 0.65), self.width, self.height], fill=(40, 50, 70))  # Floor
            draw_bg.line([0, int(self.height * 0.65), self.width, int(self.height * 0.65)], fill=(0, 200, 255), width=3)

            # Determine speaker and viseme state
            if frame_idx < half_frames:
                current_subtitle = dial_1
                cat_mouth = lip_timeline_1[frame_idx] if frame_idx < len(lip_timeline_1) else VisemeMouthState.REST
                robot_mouth = VisemeMouthState.REST
                cat_arm = (frame_idx * 10) % 40
                robot_arm = 0
            else:
                current_subtitle = dial_2
                sub_idx = frame_idx - half_frames
                cat_mouth = VisemeMouthState.REST
                robot_mouth = lip_timeline_2[sub_idx] if sub_idx < len(lip_timeline_2) else VisemeMouthState.REST
                cat_arm = 0
                robot_arm = (frame_idx * 10) % 40

            # Render Character 1 (Cat)
            cat_transform = CharacterTransform(
                pos_x=0.25,
                pos_y=0.6,
                rotation=0,
                arm_angle=cat_arm,
                mouth_state=cat_mouth,
                eye_state="blinking" if frame_idx % 30 == 0 else "open",
            )
            cat_frame = cat_rig.render_frame(cat_transform)
            frame_bg.paste(cat_frame, (int(self.width * 0.05), int(self.height * 0.25)), cat_frame)

            # Render Character 2 (Robot)
            robot_transform = CharacterTransform(
                pos_x=0.75,
                pos_y=0.6,
                rotation=0,
                arm_angle=robot_arm,
                mouth_state=robot_mouth,
                eye_state="open",
            )
            robot_frame = robot_rig.render_frame(robot_transform)
            frame_bg.paste(robot_frame, (int(self.width * 0.52), int(self.height * 0.25)), robot_frame)

            # Overlay Subtitles
            frame_final = SubtitleOverlayGenerator.overlay_subtitles(frame_bg, current_subtitle)

            # Save Frame File
            frame_file = os.path.join(output_dir, f"frame_{frame_idx:04d}.jpg")
            frame_final.save(frame_file, "JPEG", quality=85)
            frame_paths.append(frame_file)

        logger.info(f"Rendered total {len(frame_paths)} 2D cartoon frames successfully.")
        return frame_paths
