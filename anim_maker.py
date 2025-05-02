import sys
from pathlib import Path
from tkinter import messagebox
import traceback
from typing import Dict, List
import json

from processor import AnimationProcessor, AnimationType, ProcessedFrame
from builder import AnimationBuilder, AnimationConfig
from compiler import Compiler
from ui import AnimationUI
from animation import Source, Animation, ImmediateState

class AnimationManager:
    """Main application controller"""
    def __init__(self):
        self.ui = AnimationUI()
        self.processor = AnimationProcessor()
        self.builder = AnimationBuilder()
        self.compiler = Compiler()
        
        # Save reference to table for frame updates
        self.table = self.ui.table

        # Bind processing event
        self.ui.window.bind('<<ProcessAnimations>>', self._on_process)

    def run(self) -> None:
        """Start the application"""
        try:
            self.ui.run()
        except Exception as e:
            self._handle_error("Application Error", e)

    def _on_process(self, _) -> None:
        """Handle animation processing request"""
        try:
            # Get configurations
            configs = self.ui.get_configs()
            if not configs:
                return

            # Get and verify output path
            output_path = self.ui.get_output_path()
            if not output_path:
                messagebox.showerror("Error", "No output path specified")
                return

            # Get common name and bin file name from UI
            common_name = self.ui.common_name_var.get().strip()
            bin_name = self.ui.bin_name_var.get().strip()

            # Use default names if not provided
            if not common_name:
                common_name = "Animation"
            if not bin_name:
                bin_name = output_path.stem

            # Process animations
            if self._process_animations(configs, output_path, common_name, bin_name):
                messagebox.showinfo("Success", "Animations processed successfully!")

        except Exception as e:
            self._handle_error("Processing Error", e)

    def _process_animations(self, configs: Dict[str, AnimationConfig], 
                          output_path: Path, 
                          common_name: str,
                          bin_name: str) -> bool:
        """Process and compile animations"""
        try:
            # Reset builder state before starting
            self.builder.reset()
            
            # Reset processor state
            self.processor = AnimationProcessor()
            
            # First, validate all folder paths exist
            for name, config in configs.items():
                if config.type == AnimationType.FOLDER:
                    folder = Path(config.source_path)
                    if not folder.is_dir():
                        raise ValueError(f"Source folder for '{name}' not found: {folder}")

            # Setup processor with configurations
            for name, config in configs.items():
                self.processor.add_animation(
                    name,
                    config.type,
                    config.source_path,
                    config.reference_anim
                )

            # Process all frames
            processed_frames, global_bbox = self.processor.process_all()
            if not processed_frames:
                raise ValueError("No frames were processed")

            # Update UI with processed frames for preview
            for name, frames in processed_frames.items():
                entry = self.table.get_entry(name)
                if entry:
                    entry.set_frames([frame.image for frame in frames])

            # Setup builder with configurations
            for config in configs.values():
                self.builder.add_animation(config)

            # Calculate frame counts
            frame_counts = {name: len(frames) for name, frames in processed_frames.items()}

            # Build animation data structures using common name
            sources, animations = self.builder.build_all(
                frame_counts,
                bin_name,  # Use bin_name instead of output_path.stem
                common_name  # Pass through the common name
            )

            # Verify animations were built
            if not animations:
                raise ValueError("No animations were built")

            # Setup compiler and clean old files
            self.compiler.set_output_path(output_path)
            self.compiler.cleanup_old_files(common_name, bin_name)  # Pass both names

            print("About to compile animations...")
            print(f"Number of processed frames: {sum(len(frames) for frames in processed_frames.values())}")
            print(f"Number of sources: {len(sources)}")
            print(f"Number of animations: {len(animations)}")

            # Compile final output using both names
            self.compiler.compile_animations(
                processed_frames,
                sources,
                animations,
                bin_name,
                common_name,
                global_bbox
            )

            # Check if files were created
            gfx_files = list(self.compiler.output_paths.gfx_dir.glob(f"{common_name}_*.png"))
            xml_files = list(self.compiler.output_paths.xml_dir.glob(f"{common_name}_*.xml"))
            bin_file = self.compiler.output_paths.bin_dir / f"{bin_name}.bin"
            
            print(f"\nVerifying output files:")
            print(f"PNG files created: {len(gfx_files)}")
            print(f"XML files created: {len(xml_files)}")
            print(f"BIN file exists: {bin_file.exists()}")

            if not gfx_files or not xml_files or not bin_file.exists():
                raise ValueError("Failed to create all required output files")

            # Save debug information if needed
            try:
                debug_file = output_path / 'debug_info.json'
                debug_info = {
                    'common_name': common_name,
                    'bin_name': bin_name,
                    'sources': [
                        {
                            'path': s.path,
                            'id': s.id,
                            'width': s.width,
                            'height': s.height
                        }
                        for s in sources
                    ],
                    'animations': [
                        {
                            'name': a.name,
                            'width': a.width,
                            'height': a.height,
                            'centered': a.centered,
                            'layers': [
                                {
                                    'name': l.name,
                                    'type': l.type,
                                    'blend': l.blend.name,
                                    'source': l.source,
                                    'anchor_x': l.anchor_x,
                                    'anchor_y': l.anchor_y,
                                    'frame_count': len(l.frames)
                                }
                                for l in a.layers
                            ]
                        }
                        for a in animations
                    ]
                }
                
                with open(debug_file, 'w') as f:
                    json.dump(debug_info, f, indent=2)
            except Exception as e:
                print(f"Warning: Failed to save debug info: {e}", file=sys.stderr)

            return True

        except Exception as e:
            print(f"Error during processing: {str(e)}")
            traceback.print_exc()
            raise RuntimeError(f"Failed to process animations: {str(e)}") from e

    def _handle_error(self, title: str, error: Exception) -> None:
        """Handle and display errors"""
        trace = traceback.format_exc()
        message = f"Error: {str(error)}\n\nDetails:\n{trace}"
        messagebox.showerror(title, message)
        print(message, file=sys.stderr)
