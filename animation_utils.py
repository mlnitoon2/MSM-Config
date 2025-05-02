from pathlib import Path
from PIL import Image
from typing import List, Dict, Optional
import glob

def load_animation_frames(folder_path: str) -> List[Image.Image]:
    """Load all PNG frames from a folder"""
    folder = Path(folder_path)
    if not folder.is_dir():
        return []
        
    frames = []
    for img_path in sorted(folder.glob("*.png")):
        try:
            img = Image.open(img_path)
            frames.append(img.convert('RGBA'))
        except Exception:
            continue
            
    return frames

class AnimationCache:
    """Cache for loaded animation frames"""
    def __init__(self):
        self.frames: Dict[str, List[Image.Image]] = {}
        
    def load_if_needed(self, name: str, folder_path: Optional[str] = None) -> List[Image.Image]:
        """Load frames if not already cached"""
        if name in self.frames:
            return self.frames[name]
            
        if folder_path:
            frames = load_animation_frames(folder_path)
            if frames:
                self.frames[name] = frames
                return frames
                
        return []
        
    def get_frames(self, name: str, ref_name: Optional[str] = None, 
                  first_frame_only: bool = False) -> List[Image.Image]:
        """Get frames for an animation, possibly referencing another"""
        if name in self.frames:
            frames = self.frames[name]
            return [frames[0]] if first_frame_only and frames else frames
            
        if ref_name and ref_name in self.frames:
            frames = self.frames[ref_name]
            if first_frame_only and frames:
                return [frames[0]]
            return frames.copy()
            
        return []
        
    def clear(self):
        """Clear the cache"""
        self.frames.clear()