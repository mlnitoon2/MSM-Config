from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image
import math
from xml.etree.ElementTree import Element, ElementTree, SubElement
import shutil
from binfile import BinFile

from processor import ProcessedFrame, BoundingBox
from animation import Source, Animation


@dataclass
class OutputPaths:
    """Paths for output files"""
    gfx_dir: Path
    xml_dir: Path
    bin_dir: Path
    
    @classmethod
    def create(cls, base_path: Path) -> 'OutputPaths':
        """Create output directories and return paths"""
        paths = cls(
            gfx_dir=base_path / 'gfx' / 'bori',
            xml_dir=base_path / 'xml_resources',
            bin_dir=base_path / 'xml_bin'
        )
        
        # Create directories
        paths.gfx_dir.mkdir(parents=True, exist_ok=True)
        paths.xml_dir.mkdir(parents=True, exist_ok=True)
        paths.bin_dir.mkdir(parents=True, exist_ok=True)
        
        return paths


@dataclass
class SpritesheetData:
    """Data for a generated spritesheet"""
    image: Image.Image
    frame_positions: List[Tuple[int, int]]  # x, y positions for each frame
    frame_size: Tuple[int, int]  # width, height of frames


class Compiler:
    """Handles compilation of processed animations into final output"""
    
    def __init__(self):
        self.output_paths: OutputPaths | None = None
        
    def set_output_path(self, path: Path) -> None:
        """Set and create output directory structure"""
        self.output_paths = OutputPaths.create(path)
        
    def _calculate_spritesheet_size(self, frame_count: int, 
                                  frame_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
        """Calculate optimal spritesheet dimensions"""
        # Aim for roughly square texture
        cols = math.ceil(math.sqrt(frame_count))
        rows = math.ceil(frame_count / cols)
        
        sheet_width = cols * frame_size[0]
        sheet_height = rows * frame_size[1]
        
        return sheet_width, sheet_height, cols, rows
    
    def _create_spritesheet(self, frames: List[ProcessedFrame],
                           name: str) -> SpritesheetData:
        """Create a spritesheet from frames"""
        if not frames:
            raise ValueError(f"No frames provided for {name}")
            
        # Get frame size from first frame
        frame_size = frames[0].image.size
        
        # Calculate sheet size
        width, height, cols, _ = self._calculate_spritesheet_size(
            len(frames), frame_size
        )
        
        # Create sheet
        sheet = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        frame_positions = []
        
        # Place frames
        for i, frame in enumerate(frames):
            x = (i % cols) * frame_size[0]
            y = (i // cols) * frame_size[1]
            sheet.paste(frame.image, (x, y))
            frame_positions.append((x, y))
            
        return SpritesheetData(sheet, frame_positions, frame_size)
    
    def _create_sprite_xml(self, name: str, sheet_data: SpritesheetData,
                          gfx_path: str) -> ElementTree:
        """Create XML metadata for spritesheet"""
        root = Element('TextureAtlas', {
            'imagePath': gfx_path,
            'width': str(sheet_data.image.width),
            'height': str(sheet_data.image.height),
            'hires': 'true'
        })
        
        # Add sprite entries
        for i, (x, y) in enumerate(sheet_data.frame_positions):
            SubElement(root, 'sprite', {
                'n': f'frame_{i:03d}',
                'x': str(x),
                'y': str(y),
                'w': str(sheet_data.frame_size[0]),
                'h': str(sheet_data.frame_size[1]),
                'pX': '0.5',  # Pivot points at center
                'pY': '0.5'
            })
            
        return ElementTree(root)
    
    def compile_animations(self, processed_frames: Dict[str, List[ProcessedFrame]],
                         sources: List[Source], animations: List[Animation],
                         bin_name: str, common_name: str,
                         global_bbox: Optional[BoundingBox] = None) -> None:
        """Compile all animations into final output"""
        if not self.output_paths:
            raise ValueError("Output paths not set")
            
        xml_paths: Dict[str, str] = {}
        
        # First pass: create spritesheets and XMLs
        for name, frames in processed_frames.items():
            if not frames:
                continue
                
            # Generate filenames using common_name for PNGs and XMLs
            sprite_name = f"{common_name}_{name}"
            png_path = self.output_paths.gfx_dir / f"{sprite_name}.png"
            xml_path = self.output_paths.xml_dir / f"{sprite_name}.xml"
            
            # Create and save spritesheet
            sheet_data = self._create_spritesheet(frames, name)
            sheet_data.image.save(png_path)
            
            # Create and save XML
            gfx_path = f"gfx/bori_love/{sprite_name}.png"
            xml_tree = self._create_sprite_xml(name, sheet_data, gfx_path)
            xml_tree.write(xml_path, encoding='utf-8', xml_declaration=True)
            
            # Store relative XML path for binary file
            xml_paths[name] = f"{sprite_name}.xml"
        
        # Update sources with XML paths and dimensions
        for source in sources:
            source_name = source.path.replace("BASENAME", common_name)
            if source_name in xml_paths:
                source.path = xml_paths[source_name]
                # Get first frame of corresponding animation for dimensions
                frames = next(frames for name, frames in processed_frames.items()
                            if f"{common_name}_{name}.xml" == source.path)
                if frames:
                    source.width = frames[0].image.size[0]
                    source.height = frames[0].image.size[1]
        
        # Create binary file (using bin_name)
        bin_path = self.output_paths.bin_dir / f"{bin_name}.bin"
        bf = BinFile(str(bin_path), write=True)
        
        # Write sources
        bf.writeUInt32(len(sources))
        for source in sources:
            source.write(bf)
        
        # Write animations
        bf.writeUInt32(len(animations))
        for animation in animations:
            animation.write(bf)
        
        # Write watermark at the end of the file
        bf.writeInt32(0)  # Four null bytes
        bf.writeString("created by borealis & riotlove")

        bf.close()
        
    def cleanup_old_files(self, common_name: str, bin_name: str) -> None:
        """Clean up old output files"""
        if not self.output_paths:
            return
            
        # Remove old PNGs using common_name
        for file in self.output_paths.gfx_dir.glob(f"{common_name}_*.png"):
            file.unlink()
            
        # Remove old XMLs using common_name
        for file in self.output_paths.xml_dir.glob(f"{common_name}_*.xml"):
            file.unlink()
            
        # Remove old binary using bin_name
        bin_file = self.output_paths.bin_dir / f"{bin_name}.bin"
        if bin_file.exists():
            bin_file.unlink()
            
    def verify_output(self, common_name: str, bin_name: str) -> bool:
        """Verify all output files were created correctly"""
        if not self.output_paths:
            return False
            
        # Check if at least one file of each type exists using appropriate names
        has_png = any(self.output_paths.gfx_dir.glob(f"{common_name}_*.png"))
        has_xml = any(self.output_paths.xml_dir.glob(f"{common_name}_*.xml"))
        has_bin = (self.output_paths.bin_dir / f"{bin_name}.bin").exists()
        
        return has_png and has_xml and has_bin
