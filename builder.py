from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum, auto

from animation import (
    Animation, Layer, Frame, Source,
    Position, Scale, Value, Sprite, Color,
    BlendMode, ImmediateState
)
from processor import AnimationType

@dataclass
class AnimationConfig:
    """Configuration for an animation"""
    name: str
    type: AnimationType
    source_path: Optional[str] = None
    reference_anim: Optional[str] = None
    fps: float = 30.0
    centered: bool = True
    blend_mode: BlendMode = BlendMode.NORMAL
    position_x: float = 0
    position_y: float = -70.0
    scale: float = 100.0

    @property
    def frame_time(self) -> float:
        return 1.0 / self.fps

class AnimationBuilder:
    """Handles building animation data structures from processed frames"""
    
    def __init__(self, target_size: int = 192):
        self.target_size = target_size
        self.reset()
        
    def reset(self) -> None:
        """Reset builder state completely"""
        self.configs = {}
        self._source_counter = 0
        self._layer_counter = 0
        
    def add_animation(self, config: AnimationConfig) -> None:
        """Add an animation configuration"""
        if config.name in self.configs:
            raise ValueError(f"Animation '{config.name}' already exists")
        self.configs[config.name] = config
    
    def _create_source(self, name: str, common_name: str) -> Source:
        """Create a source entry using common name for consistency"""
        # Use the common name pattern for source file names
        source_name = f"{common_name}_{name}.xml"
        
        source = Source(
            path=source_name,
            id=self._source_counter,
            width=0,
            height=0
        )
        self._source_counter += 1
        return source
    
    def _create_frames(self, frame_count: int, config: AnimationConfig) -> List[Frame]:
        """Create frames with proper timing based on config"""
        frames = []
        size = self.target_size
        scale_factor = config.scale / 100.0
        scale_offset = (100 - config.scale) * 0.8
        
        for i in range(frame_count):
            frame = Frame(
                time=i * config.frame_time,
                position=Position(
                    immediate=ImmediateState.SET,
                    x=config.position_x + scale_offset,
                    y=config.position_y + scale_offset
                ),
                scale=Scale(
                    immediate=ImmediateState.SET,
                    x=size * scale_factor,
                    y=size * scale_factor
                ),
                rotation=Value(
                    immediate=ImmediateState.SET,
                    value=0.0
                ),
                opacity=Value(
                    immediate=ImmediateState.SET,
                    value=100.0
                ),
                sprite=Sprite(
                    immediate=ImmediateState.SET,
                    name=f"frame_{i:03d}"
                ),
                color=Color(
                    immediate=ImmediateState.UNSET,
                    r=-1, g=-1, b=-1
                )
            )
            frames.append(frame)
        
        return frames
        
    def _create_layer(self, name: str, frame_count: int,
                    source_id: int, config: AnimationConfig,
                    common_name: str) -> Layer:
        """Create layer with proper configuration"""
        size = self.target_size
        
        layer = Layer(
            name=f'Anim Maker {common_name}',
            type=1,
            blend=config.blend_mode,
            parent=-1,
            id=self._layer_counter,
            source=source_id,
            width=size,
            height=size,
            anchor_x=0,
            anchor_y=0,
            metadata='',
            frames=self._create_frames(frame_count, config)
        )
        self._layer_counter += 1
        return layer

    def _create_animation(self, name: str, frame_count: int,
                         source_id: int, config: AnimationConfig,
                         common_name: str) -> Animation:
        """Create animation with proper configuration"""
        return Animation(
            name=name,
            width=self.target_size,
            height=self.target_size,
            loop_offset=0.0,
            centered=1 if config.centered else 0,
            layers=[self._create_layer(name, frame_count, source_id, config, common_name)]
        )
    
    def build_all(self, frame_counts: Dict[str, int],
                 bin_name: str,
                 common_name: str = "Animation") -> Tuple[List[Source], List[Animation]]:
        """Build all animations from configurations and frame counts"""
        sources: List[Source] = []
        animations: List[Animation] = []
        source_map: Dict[str, Source] = {}
        processed_names = set()
        
        # Reset counters to ensure consistent IDs
        self._source_counter = 0
        self._layer_counter = 0
        
        # First pass: build folder-based animations
        for name, config in self.configs.items():
            if config.type != AnimationType.FOLDER:
                continue
                
            if name not in frame_counts:
                raise ValueError(f"No frame count for animation '{name}'")
            
            processed_names.add(name)
            
            source = self._create_source(name, common_name)
            sources.append(source)
            source_map[name] = source
            
            animation = self._create_animation(
                name,
                frame_counts[name],
                source.id,
                config,
                common_name
            )
            animations.append(animation)
        
        # Second pass: build reference-based animations
        for name, config in self.configs.items():
            if config.type == AnimationType.FOLDER or name in processed_names:
                continue
                
            if not config.reference_anim:
                raise ValueError(f"No reference animation specified for '{name}'")
                
            ref_anim = next((a for a in animations 
                           if a.name == config.reference_anim), None)
            if not ref_anim:
                raise ValueError(
                    f"Reference animation '{config.reference_anim}' not found"
                )
            
            ref_source = source_map.get(config.reference_anim)
            if not ref_source:
                raise ValueError(
                    f"Reference source for '{config.reference_anim}' not found"
                )
                
            frame_count = (1 if config.type == AnimationType.FIRST_FRAME 
                         else len(ref_anim.layers[0].frames))
            
            animation = self._create_animation(
                name,
                frame_count,
                ref_source.id,
                config,
                common_name
            )
            animations.append(animation)
            processed_names.add(name)
        
        # Verify all configs were processed
        unprocessed = set(self.configs.keys()) - processed_names
        if unprocessed:
            raise ValueError(f"Some animations were not processed: {unprocessed}")
        
        return sources, animations
