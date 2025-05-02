import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image
from processor import AnimationType
from builder import AnimationConfig
from preview import PreviewWindow
from typing import Callable, List, Optional

class AnimationCache:
    """Cache for loaded animation frames"""
    def __init__(self):
        self.frames = {}

    def load_if_needed(self, name: str, folder_path: Optional[str] = None) -> List[Image.Image]:
        """Load frames if not already cached"""
        if name in self.frames:
            return self.frames[name]

        if folder_path:
            frames = self._load_frames(folder_path)
            if frames:
                self.frames[name] = frames
                return frames

        return []

    def _load_frames(self, folder_path: str) -> List[Image.Image]:
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

    def clear(self):
        """Clear the cache"""
        self.frames.clear()


class AnimationEntry:
    """Represents a row in the animation table"""
    def __init__(self, parent: ctk.CTkFrame, row: int,
                 on_update: Callable, on_delete: Callable,
                 animation_cache: AnimationCache):
        self.parent = parent
        self.row = row
        self.on_update = on_update
        self.on_delete = on_delete
        self.animation_cache = animation_cache
        self.frames: List[Image.Image] = []

        # Initializing StringVar for various settings
        self.name_var = ctk.StringVar()
        self.type_var = ctk.StringVar(value=AnimationType.FOLDER.name)
        self.source_var = ctk.StringVar()
        self.fps_var = ctk.StringVar(value="30")
        self.target_var = ctk.StringVar()
        self.position_x_var = ctk.StringVar(value="0")
        self.position_y_var = ctk.StringVar(value="-70")
        self.scale_var = ctk.StringVar(value="100")

        self._create_widgets()
        self._setup_bindings()

    def _create_widgets(self):
        # Name entry
        self.name_entry = ctk.CTkEntry(self.parent, textvariable=self.name_var)
        self.name_entry.grid(row=self.row, column=0, padx=5, pady=5, sticky='ew')

        # Type combobox
        self.type_combo = ctk.CTkComboBox(self.parent, values=[t.name for t in AnimationType],
                                          textvariable=self.type_var)
        self.type_combo.grid(row=self.row, column=1, padx=5, pady=5, sticky='ew')

        # Source frame setup
        self.source_frame = ctk.CTkFrame(self.parent)
        self.source_frame.grid(row=self.row, column=2, padx=5, pady=5, sticky='ew')

        # Path entry & browse button
        self.path_entry = ctk.CTkEntry(self.source_frame, textvariable=self.source_var)
        self.browse_btn = ctk.CTkButton(self.source_frame, text="Browse", command=self._browse_folder)
        self.path_entry.grid(row=0, column=0, sticky='ew', padx=(5, 0))
        self.browse_btn.grid(row=0, column=1, padx=5)

        # FPS entry
        self.fps_entry = ctk.CTkEntry(self.parent, textvariable=self.fps_var, width=10)
        self.fps_entry.grid(row=self.row, column=3, padx=5, pady=5, sticky='ew')

        # Frame count label
        self.frame_count = ctk.CTkLabel(self.parent, text="0 frames")
        self.frame_count.grid(row=self.row, column=4, padx=5, pady=5)

        # Preview button
        self.preview_btn = ctk.CTkButton(self.parent, text="Preview", command=self._show_preview)
        self.preview_btn.grid(row=self.row, column=5, padx=5, pady=5)

        # Delete button
        self.delete_btn = ctk.CTkButton(self.parent, text="❌", command=lambda: self.on_delete(self))
        self.delete_btn.grid(row=self.row, column=6, padx=5, pady=5)

        # Position and scale settings
        self._setup_position_scale_widgets()

    def _setup_position_scale_widgets(self):
        position_frame = ctk.CTkFrame(self.parent)
        position_frame.grid(row=self.row, column=4, padx=5, pady=5)

        # X Position
        self.position_x_entry = ctk.CTkEntry(position_frame, textvariable=self.position_x_var, width=5)
        self.position_x_entry.grid(row=0, column=0, padx=5)

        # Y Position
        self.position_y_entry = ctk.CTkEntry(position_frame, textvariable=self.position_y_var, width=5)
        self.position_y_entry.grid(row=0, column=1, padx=5)

        # Scale
        self.scale_entry = ctk.CTkEntry(position_frame, textvariable=self.scale_var, width=5)
        self.scale_entry.grid(row=0, column=2, padx=5)

    def _setup_bindings(self):
        self.type_combo.bind('<<ComboboxSelected>>', lambda _: self._update_source_widgets())
        for var in [self.name_var, self.type_var, self.source_var, self.fps_var, self.target_var, 
                    self.position_x_var, self.position_y_var, self.scale_var]:
            var.trace_add('write', lambda *_: self._on_change())

    def _browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_var.set(folder)
            frames = self.animation_cache.load_if_needed(self.name_var.get().strip(), folder)
            self.frame_count.configure(text=f"{len(frames)} frames")

    def _update_source_widgets(self):
        for widget in self.source_frame.winfo_children():
            widget.grid_remove()

        anim_type = AnimationType[self.type_var.get()]
        if anim_type == AnimationType.FOLDER:
            self.path_entry.grid(row=0, column=0, sticky='ew')
            self.browse_btn.grid(row=0, column=1, padx=5)
        else:
            pass

    def _show_preview(self):
        """Show animation preview window"""
        try:
            fps = float(self.fps_var.get())
            if fps <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Invalid FPS value")
            return

        if self.frames:
            PreviewWindow(self.parent.winfo_toplevel(), self.frames, fps)
            return

        folder_path = self.source_var.get().strip()
        if not folder_path:
            messagebox.showerror("Error", "No folder specified")
            return

        frames = self.animation_cache.load_if_needed(self.name_var.get().strip(), folder_path)
        if not frames:
            messagebox.showerror("Error", "No frames found in folder")
            return

        self.frames = frames
        self.frame_count.configure(text=f"{len(frames)} frames")
        PreviewWindow(self.parent.winfo_toplevel(), frames, fps)

    def _on_change(self):
        self.on_update(self)

    def get_config(self) -> Optional[AnimationConfig]:
        name = self.name_var.get().strip()
        if not name:
            return None

        try:
            fps = float(self.fps_var.get())
            position_x = float(self.position_x_var.get())
            position_y = float(self.position_y_var.get())
            scale = float(self.scale_var.get())
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value: {e}")
            return None

        anim_type = AnimationType[self.type_var.get()]
        if anim_type == AnimationType.FOLDER:
            source_path = self.source_var.get().strip()
            if not source_path or not Path(source_path).is_dir():
                messagebox.showerror("Error", f"Invalid source folder: {source_path}")
                return None
            return AnimationConfig(name=name, type=anim_type, source_path=source_path,
                                   fps=fps, position_x=position_x, position_y=position_y, scale=scale)

        ref_anim = self.target_var.get()
        if not ref_anim:
            messagebox.showerror("Error", "No reference animation specified")
            return None

        return AnimationConfig(name=name, type=anim_type, reference_anim=ref_anim, 
                               fps=fps, position_x=position_x, position_y=position_y, scale=scale)


class AnimationTable(ctk.CTkFrame):
    """Main animation table widget"""
    def __init__(self, parent):
        super().__init__(parent)
        self.animation_cache = AnimationCache()
        self.entries = []
        self._setup_ui()

    def _setup_ui(self):
        headers = ['Name', 'Type', 'Source/Target', 'FPS', 'Offset', 'Count', 'Preview', '']
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(self, text=header, font=('Arial', 12, 'bold'))
            label.grid(row=0, column=i, padx=5, pady=5)

        self.add_button = ctk.CTkButton(self, text="Add Animation", command=self._add_entry)
        self.add_button.grid(row=1, columnspan=8, pady=10)

    def _add_entry(self):
        entry = AnimationEntry(self, len(self.entries) + 1, self._on_update, self._on_delete, self.animation_cache)
        entry.grid(row=len(self.entries) + 1, column=0, columnspan=8, padx=5, pady=5, sticky='ew')
        self.entries.append(entry)

    def _on_update(self, entry: AnimationEntry):
        # Handle any updates on the entries
        pass

    def _on_delete(self, entry: AnimationEntry):
        # Remove entry from the UI
        entry.destroy()
        self.entries.remove(entry)

    def get_configs(self) -> List[AnimationConfig]:
        return [entry.get_config() for entry in self.entries if entry.get_config()]

class AnimationUI:
    """Main application window"""
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Animation Manager")
        self.window.geometry("800x600")
        
        self._setup_ui()

    def _setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Animation table
        self.table = AnimationTable(main_frame)
        self.table.pack(fill=tk.BOTH, expand=True)

        # Output settings
        settings_frame = ttk.LabelFrame(main_frame, text="Output Settings", 
                                      padding="5")
        settings_frame.pack(fill=tk.X, pady=(10, 0))

        # Common name for layers
        common_frame = ttk.Frame(settings_frame)
        common_frame.pack(fill=tk.X, pady=2)
        self.common_name_var = tk.StringVar()
        ttk.Label(common_frame, text="Common Name:").pack(side=tk.LEFT)
        ttk.Entry(common_frame, textvariable=self.common_name_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Bin file name
        bin_frame = ttk.Frame(settings_frame)
        bin_frame.pack(fill=tk.X, pady=2)
        self.bin_name_var = tk.StringVar()
        ttk.Label(bin_frame, text="Bin File Name:").pack(side=tk.LEFT)
        ttk.Entry(bin_frame, textvariable=self.bin_name_var).pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Output folder
        folder_frame = ttk.Frame(settings_frame)
        folder_frame.pack(fill=tk.X)
        
        self.output_var = tk.StringVar()
        ttk.Label(folder_frame, text="Output Folder:").pack(side=tk.LEFT)
        ttk.Entry(folder_frame, textvariable=self.output_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        ttk.Button(folder_frame, text="Browse", 
                  command=self._browse_output).pack(side=tk.LEFT, padx=(5, 0))

        # Process button
        self.process_btn = ttk.Button(
            main_frame, text="Process Animations",
            command=self._process
        )
        self.process_btn.pack(pady=10)

    def _browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_var.set(folder)

    def _process(self):
        configs = self.table.get_configs()
        if not configs:
            return

        output = self.output_var.get().strip()
        if not output:
            messagebox.showerror("Error", "No output folder specified")
            return
        if not Path(output).exists():
            if messagebox.askyesno("Create Folder", 
                                 "Output folder doesn't exist. Create it?"):
                Path(output).mkdir(parents=True)
            else:
                return

        # Signal that we're ready to process
        self.window.event_generate('<<ProcessAnimations>>')

    def run(self):
        self.window.mainloop()

    def get_output_path(self) -> Optional[Path]:
        """Get the selected output path"""
        path = self.output_var.get().strip()
        return Path(path) if path else None

    def get_configs(self) -> Dict[str, AnimationConfig]:
        """Get all animation configurations"""
        return self.table.get_configs()
