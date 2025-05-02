from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image
import numpy as np
from enum import Enum, auto

class ProcessingError(Exception):
    """Custom exception for image processing errors"""
    def __init__(self, message: str, source_path: Optional[Path] = None):
        self.source_path = source_path
        super().__init__(f"{message} ({source_path})" if source_path else message)

class AnimationType(Enum):
    """Type of animation source"""
    FOLDER = auto()
    COPY = auto()
    FIRST_FRAME = auto()

@dataclass
class BoundingBox:
    """Represents the bounding box of an image"""
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def update(self, other: 'BoundingBox') -> None:
        """Update this bounding box to encompass another"""
        self.left = min(self.left, other.left)
        self.top = min(self.top, other.top)
        self.right = max(self.right, other.right)
        self.bottom = max(self.bottom, other.bottom)

@dataclass
class ProcessedFrame:
    """Represents a processed animation frame"""
    image: Image.Image
    original_size: Tuple[int, int]
    original_bbox: BoundingBox
    final_offset: Tuple[int, int]  # Offset in final frame
    source_path: Optional[Path] = None

class ImageProcessor:
    """Handles processing of individual images"""
    
    def __init__(self, target_size: int = 192):
        self.target_size = target_size
        self._validate_target_size()

    def _validate_target_size(self) -> None:
        """Validate target size is reasonable"""
        if not isinstance(self.target_size, int):
            raise ValueError("Target size must be an integer")
        if self.target_size <= 0:
            raise ValueError("Target size must be positive")
        if self.target_size > 4096:  # Reasonable maximum
            raise ValueError("Target size too large")

    def find_bbox(self, image: Image.Image) -> BoundingBox:
        """Find bounding box of non-transparent pixels"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # Convert to numpy array for efficient processing
        data = np.array(image)
        alpha = data[:, :, 3]

        # Find non-transparent pixels
        rows = np.any(alpha > 0, axis=1)
        cols = np.any(alpha > 0, axis=0)

        if not np.any(rows) or not np.any(cols):
            raise ProcessingError("Image appears to be empty (fully transparent)")

        top, bottom = np.where(rows)[0][[0, -1]]
        left, right = np.where(cols)[0][[0, -1]]

        return BoundingBox(int(left), int(top), int(right + 1), int(bottom + 1))

    def compute_global_bbox(self, image_paths: List[Path]) -> BoundingBox:
        """Compute global bounding box across all images"""
        if not image_paths:
            raise ProcessingError("No images provided for processing")

        # Initialize with first image
        try:
            with Image.open(image_paths[0]) as first_img:
                global_bbox = self.find_bbox(first_img)
        except Exception as e:
            raise ProcessingError(f"Failed to process first image: {e}", image_paths[0])

        # Update with remaining images
        for path in image_paths[1:]:
            try:
                with Image.open(path) as img:
                    frame_bbox = self.find_bbox(img)
                    global_bbox.update(frame_bbox)
            except Exception as e:
                raise ProcessingError(f"Failed to process image: {e}", path)

        return global_bbox

    def _premultiply_alpha(self, image: Image.Image) -> Image.Image:
        """Premultiply RGB channels with alpha"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        data = np.array(image)
        alpha = data[:, :, 3] / 255.0
        
        # Premultiply RGB channels
        data[:, :, 0] = np.round(data[:, :, 0] * alpha)
        data[:, :, 1] = np.round(data[:, :, 1] * alpha)
        data[:, :, 2] = np.round(data[:, :, 2] * alpha)

        return Image.fromarray(data)

    def process_frame(self, image: Image.Image, global_bbox: BoundingBox,
                     source_path: Optional[Path] = None) -> ProcessedFrame:
        """Process a single frame using global bounding box"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # Get this frame's bbox
        frame_bbox = self.find_bbox(image)

        # Crop to global bounding box
        cropped = image.crop((
            global_bbox.left,
            global_bbox.top,
            global_bbox.right,
            global_bbox.bottom
        ))

        # Calculate scale to fit target size while maintaining aspect ratio
        scale = min(
            self.target_size / global_bbox.width,
            self.target_size / global_bbox.height
        )

        # Scale the image
        new_width = int(global_bbox.width * scale)
        new_height = int(global_bbox.height * scale)
        scaled = cropped.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )

        # Center in target size
        final = Image.new('RGBA', (self.target_size, self.target_size), (0, 0, 0, 0))
        paste_x = (self.target_size - new_width) // 2
        paste_y = (self.target_size - new_height) // 2
        final.paste(scaled, (paste_x, paste_y))

        # Premultiply alpha
        final = self._premultiply_alpha(final)

        return ProcessedFrame(
            image=final,
            original_size=image.size,
            original_bbox=frame_bbox,
            final_offset=(paste_x, paste_y),
            source_path=source_path
        )

    def process_animation(self, paths: List[Path]) -> Tuple[List[ProcessedFrame], BoundingBox]:
        """Process all frames in an animation"""
        if not paths:
            raise ProcessingError("No image paths provided")

        # First pass: compute global bounding box
        global_bbox = self.compute_global_bbox(paths)

        # Second pass: process all frames
        processed_frames = []
        for path in paths:
            try:
                with Image.open(path) as img:
                    frame = self.process_frame(img, global_bbox, path)
                    processed_frames.append(frame)
            except Exception as e:
                raise ProcessingError(f"Failed to process frame: {e}", path)

        return processed_frames, global_bbox

class AnimationProcessor:
    """Handles processing of multiple animations"""
    
    def __init__(self, target_size: int = 192):
        self.image_processor = ImageProcessor(target_size)
        self.animations: Dict[str, List[Path]] = {}
        self.animation_types: Dict[str, AnimationType] = {}
        self.source_refs: Dict[str, str] = {}  # For COPY and FIRST_FRAME types

    def add_animation(self, name: str, anim_type: AnimationType, 
                     source: Optional[str] = None, ref_anim: Optional[str] = None) -> None:
        """Add an animation to be processed"""
        if name in self.animations:
            raise ValueError(f"Animation '{name}' already exists")

        if anim_type == AnimationType.FOLDER:
            if not source:
                raise ValueError(f"Source path required for FOLDER animation '{name}'")
            path = Path(source)
            if not path.is_dir():
                raise ValueError(f"Source path '{source}' is not a directory")
            # Sort the PNG files to ensure consistent order
            self.animations[name] = sorted(path.glob("*.png"))
            if not self.animations[name]:
                raise ValueError(f"No PNG files found in '{source}'")
        elif anim_type in (AnimationType.COPY, AnimationType.FIRST_FRAME):
            if not ref_anim:
                raise ValueError(f"Reference animation required for {anim_type.name} type '{name}'")
            self.source_refs[name] = ref_anim
        else:
            raise ValueError(f"Unsupported animation type: {anim_type}")
        
        self.animation_types[name] = anim_type

    def process_all(self) -> tuple[Dict[str, List[ProcessedFrame]], BoundingBox]:
        """Process all animations using a unified bounding box"""
        try:
            # First, collect all unique frames that need processing
            all_frames: List[Path] = []
            for name, paths in self.animations.items():
                if self.animation_types[name] == AnimationType.FOLDER:
                    all_frames.extend(paths)

            if not all_frames:
                raise ProcessingError("No frames found to process")

            # Compute global bounding box across ALL frames
            try:
                global_bbox = self.image_processor.compute_global_bbox(all_frames)
            except Exception as e:
                raise ProcessingError(f"Failed to compute global bounding box: {str(e)}")

            # Process each animation using the global bounding box
            processed = {}
            for name in list(self.animations.keys()):
                try:
                    if self.animation_types[name] == AnimationType.FOLDER:
                        # Pass global_bbox to process_animation
                        frames = [
                            self.image_processor.process_frame(Image.open(path), global_bbox, path)
                            for path in self.animations[name]
                        ]
                        processed[name] = frames
                    elif self.animation_types[name] == AnimationType.COPY:
                        ref_name = self.source_refs[name]
                        if ref_name not in processed:
                            raise ProcessingError(f"Reference animation '{ref_name}' not processed yet")
                        processed[name] = [
                            ProcessedFrame(
                                image=frame.image.copy(),
                                original_size=frame.original_size,
                                original_bbox=frame.original_bbox,
                                final_offset=frame.final_offset,
                                source_path=frame.source_path
                            )
                            for frame in processed[ref_name]
                        ]
                    elif self.animation_types[name] == AnimationType.FIRST_FRAME:
                        ref_name = self.source_refs[name]
                        if ref_name not in processed:
                            raise ProcessingError(f"Reference animation '{ref_name}' not processed yet")
                        first_frame = processed[ref_name][0]
                        processed[name] = [
                            ProcessedFrame(
                                image=first_frame.image.copy(),
                                original_size=first_frame.original_size,
                                original_bbox=first_frame.original_bbox,
                                final_offset=first_frame.final_offset,
                                source_path=first_frame.source_path
                            )
                        ]
                except Exception as e:
                    raise ProcessingError(f"Failed to process animation '{name}': {str(e)}")

            if not processed:
                raise ProcessingError("No animations were successfully processed")

            return processed, global_bbox

        except Exception as e:
            if not isinstance(e, ProcessingError):
                raise ProcessingError(f"Unexpected error during processing: {str(e)}")
            raise

    def clear(self) -> None:
        """Clear all animations and reset processor state"""
        self.animations.clear()
        self.animation_types.clear()
        self.source_refs.clear()