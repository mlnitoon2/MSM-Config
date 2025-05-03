import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, Toplevel, Listbox
from pathlib import Path
from PIL import Image
from processor import AnimationType
from builder import AnimationConfig
from preview import PreviewWindow
from typing import Callable, Dict, Optional, List
import requests

CONFIG_URL = "https://raw.githubusercontent.com/mlnitoon2/MSM-Config/refs/heads/main/anim_maker_config.json"

def fetch_config_json():
    try:
        response = requests.get(CONFIG_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load credits config:\n{e}")
        return None

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
    def __init__(self, parent: ctk.CTkFrame, row: int, 
                 on_update: Callable, on_delete: Callable,
                 animation_cache: AnimationCache):
        self.parent = parent
        self.row = row
        self.on_update = on_update
        self.on_delete = on_delete
        self.animation_cache = animation_cache
        self.frames: List[Image.Image] = []

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
        self.name_entry = ctk.CTkEntry(self.parent, textvariable=self.name_var, width=150)
        self.name_entry.grid(row=self.row, column=0, padx=2, pady=2, sticky='ew')

        self.type_combo = ctk.CTkComboBox(self.parent,
                                          variable=self.type_var,
                                          values=[t.name for t in AnimationType],
                                          width=140,
                                          state='readonly')
        self.type_combo.grid(row=self.row, column=1, padx=2, pady=2, sticky='ew')

        self.source_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.source_frame.grid(row=self.row, column=2, padx=2, pady=2, sticky='ew')

        self.path_entry = ctk.CTkEntry(self.source_frame, textvariable=self.source_var)
        self.path_entry.grid(row=0, column=0, padx=(0,5), sticky='ew')

        self.browse_btn = ctk.CTkButton(self.source_frame, text="Browse", command=self._browse_folder, width=70)
        self.browse_btn.grid(row=0, column=1)

        self.target_combo = ctk.CTkComboBox(self.source_frame, variable=self.target_var, state='readonly', values=[], width=120)
        self.target_combo.grid(row=1, column=0, columnspan=2, pady=4)

        self.fps_entry = ctk.CTkEntry(self.parent, textvariable=self.fps_var, width=60)
        self.fps_entry.grid(row=self.row, column=3, padx=2, pady=2, sticky='ew')

        self.frame_count = ctk.CTkLabel(self.parent, text="0 frames")
        self.frame_count.grid(row=self.row, column=4, padx=2, pady=2)

        self.preview_btn = ctk.CTkButton(self.parent, text="P", width=30, command=self._show_preview)
        self.preview_btn.grid(row=self.row, column=5, padx=2, pady=2)

        self.delete_btn = ctk.CTkButton(self.parent, text="❌", width=30, command=lambda: self.on_delete(self))
        self.delete_btn.grid(row=self.row, column=6, padx=2, pady=2)

        position_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        position_frame.grid(row=self.row, column=7, padx=2, pady=2)

        ctk.CTkLabel(position_frame, text="X:").grid(row=0, column=0, padx=(5, 0))
        self.position_x_entry = ctk.CTkEntry(position_frame, textvariable=self.position_x_var, width=50)
        self.position_x_entry.grid(row=0, column=1, padx=2)

        ctk.CTkLabel(position_frame, text="Y:").grid(row=0, column=2, padx=(5, 0))
        self.position_y_entry = ctk.CTkEntry(position_frame, textvariable=self.position_y_var, width=50)
        self.position_y_entry.grid(row=0, column=3, padx=2)

        ctk.CTkLabel(position_frame, text="Scale %:").grid(row=0, column=4, padx=(5, 0))
        self.scale_entry = ctk.CTkEntry(position_frame, textvariable=self.scale_var, width=50)
        self.scale_entry.grid(row=0, column=5, padx=2)

        self._update_source_widgets()

    def _setup_bindings(self):
        self.type_combo.bind('<<ComboboxSelected>>', lambda _: self._update_source_widgets())
        for var in [self.name_var, self.type_var, self.source_var, self.fps_var, self.target_var,
                    self.position_x_var, self.position_y_var, self.scale_var]:
            var.trace_add('write', lambda *_: self._on_change())

    def _browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.source_var.set(path)
            self.frames = self.animation_cache.load_if_needed(self.name_var.get(), path)
            self.frame_count.configure(text=f"{len(self.frames)} frames")
            self._on_change()

    def _update_source_widgets(self):
        if self.type_var.get() == AnimationType.FOLDER.name:
            self.path_entry.grid()
            self.browse_btn.grid()
            self.target_combo.grid_remove()
        else:
            self.path_entry.grid_remove()
            self.browse_btn.grid_remove()
            self.target_combo.grid()

    def _on_change(self):
        self.on_update(self)

    def _show_preview(self):
        if not self.frames and self.source_var.get():
            self.frames = self.animation_cache.load_if_needed(self.name_var.get(), self.source_var.get())
        if self.frames:
            PreviewWindow(self.frames)

        # Otherwise try to load frames based on type
        anim_type = AnimationType[self.type_var.get()]
        
        if anim_type == AnimationType.FOLDER:
            # Try to load from folder
            folder_path = self.source_var.get().strip()
            if not folder_path:
                messagebox.showerror("Error", "No folder specified")
                return
                
            frames = self.animation_cache.load_if_needed(
                self.name_var.get().strip(),
                folder_path
            )
            if not frames:
                messagebox.showerror("Error", "No frames found in folder")
                return
                
            self.frames = frames
            self.frame_count.configure(text=f"{len(frames)} frames")
            PreviewWindow(self.parent.winfo_toplevel(), frames, fps)
            
        elif anim_type == AnimationType.COPY:
            # Get frames from reference animation
            ref_name = self.target_var.get().strip()
            if not ref_name:
                messagebox.showerror("Error", "No reference animation selected")
                return
                
            frames = self.animation_cache.get_frames(ref_name)
            if not frames:
                messagebox.showerror("Error", "No frames available for reference animation")
                return
                
            PreviewWindow(self.parent.winfo_toplevel(), frames, fps)
            
        else:  # FIRST_FRAME
            # Get first frame from reference animation
            ref_name = self.target_var.get().strip()
            if not ref_name:
                messagebox.showerror("Error", "No reference animation selected")
                return
                
            frames = self.animation_cache.get_frames(ref_name, first_frame_only=True)
            if not frames:
                messagebox.showerror("Error", "No frames available for reference animation")
                return
                
            PreviewWindow(self.parent.winfo_toplevel(), frames, fps)

    def _on_change(self):
        self.on_update(self)

    def set_frames(self, frames: List[Image.Image]) -> None:
        """Set frames for preview"""
        self.frames = frames
        self.frame_count.configure(text=f"{len(frames)} frames")

    def get_config(self) -> Optional[AnimationConfig]:
        """Get animation configuration from current values"""
        name = self.name_var.get().strip()
        if not name:
            return None

        try:
            fps = float(self.fps_var.get())
            if fps <= 0:
                raise ValueError("FPS must be positive")
            
            position_x = float(self.position_x_var.get())
            position_y = float(self.position_y_var.get())

            scale = float(self.scale_var.get())

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value for {name}: {str(e)}")
            return None

        anim_type = AnimationType[self.type_var.get()]
        
        if anim_type == AnimationType.FOLDER:
            source_path = self.source_var.get().strip()
            if not source_path:
                messagebox.showerror("Error", f"No source folder specified for {name}")
                return None
            if not Path(source_path).is_dir():
                messagebox.showerror("Error", f"Invalid source folder for {name}")
                return None
            
            return AnimationConfig(
                name=name,
                type=anim_type,
                source_path=source_path,
                fps=fps,
                position_x=position_x,
                position_y=position_y,
                scale=scale
            )
        else:
            ref_anim = self.target_var.get()
            if not ref_anim:
                messagebox.showerror("Error", 
                                f"No reference animation specified for {name}")
                return None
            
            return AnimationConfig(
                name=name,
                type=anim_type,
                reference_anim=ref_anim,
                fps=fps,
                position_x=position_x,
                position_y=position_y,
                scale=scale
            )

    def update_target_animations(self, animations: list[str]):
        """Update available target animations in the combobox"""
        current = self.target_var.get()
        self.target_combo['values'] = animations
        if current in animations:
            self.target_var.set(current)
        elif animations:
            self.target_var.set(animations[0])
        else:
            self.target_var.set('')


class AnimationTable(ttk.Frame):
    """Main animation table widget"""
    def __init__(self, parent):
        super().__init__(parent)
        self.animation_cache = AnimationCache()
        self.entries: list[AnimationEntry] = []
        self._setup_ui()

    def _setup_ui(self):
        # Headers
        headers = ['Name', 'Type', 'Source/Target', 'FPS', 'Offset', 'Count', 'Preview', '']
        for i, header in enumerate(headers):
            label = ttk.Label(self, text=header, font=('TkDefaultFont', 10, 'bold'))
            label.grid(row=0, column=i, padx=2, pady=(0, 5), sticky='w')

        # Add button
        self.add_btn = ttk.Button(
            self, text="Add Animation", command=self._add_entry
        )
        self.add_btn.grid(row=99, column=0, columnspan=2, pady=10, sticky='w')

        # Configure grid
        self.grid_columnconfigure(2, weight=1)  # Source column expands

    def _add_entry(self):
        """Add a new animation entry"""
        row = len(self.entries) + 1
        entry = AnimationEntry(
            self, row,
            on_update=self._update_references,
            on_delete=self._delete_entry,
            animation_cache=self.animation_cache
        )
        self.entries.append(entry)
        self._update_references()

    def _delete_entry(self, entry: AnimationEntry):
        """Delete an animation entry"""
        self.entries.remove(entry)
        # Destroy widgets
        entry.name_entry.destroy()
        entry.type_combo.destroy()
        entry.source_frame.destroy()
        entry.fps_entry.destroy()
        entry.frame_count.destroy()
        entry.preview_btn.destroy()
        entry.delete_btn.destroy()
        # Reposition remaining entries
        for i, e in enumerate(self.entries, start=1):
            e.row = i
            e.name_entry.grid(row=i)
            e.type_combo.grid(row=i)
            e.source_frame.grid(row=i)
            e.fps_entry.grid(row=i)
            e.frame_count.grid(row=i)
            e.preview_btn.grid(row=i)
            e.delete_btn.grid(row=i)
        self._update_references()

    def _update_references(self, _=None):
        """Update available reference animations in all entries"""
        folder_anims = [e.name_var.get() for e in self.entries 
                       if e.type_var.get() == AnimationType.FOLDER.name 
                       and e.name_var.get().strip()]
        
        for entry in self.entries:
            if entry.type_var.get() != AnimationType.FOLDER.name:
                entry.update_target_animations(folder_anims)

    def get_entry(self, name: str) -> Optional[AnimationEntry]:
        """Get entry by animation name"""
        return next((e for e in self.entries 
                    if e.name_var.get().strip() == name), None)

    def get_configs(self) -> Dict[str, AnimationConfig]:
        """Get all valid animation configurations"""
        configs = {}
        for entry in self.entries:
            config = entry.get_config()
            if config:
                if config.name in configs:
                    messagebox.showerror(
                        "Error", f"Duplicate animation name: {config.name}")
                    return {}
                configs[config.name] = config
        return configs


class AnimationUI:
    """Main application window"""
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Borealis & RiotLoves Custom Animation Manager")
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

        self.credits_btn = ttk.Button(
            main_frame, text="Credits",
            command=self._credits
        )
        self.credits_btn.pack(pady=10)


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

    def _credits(self):
        config = fetch_config_json()
        if not config or "credits" not in config:
            return
    
        credits = config["credits"]
    
        credits_win = Toplevel()
        credits_win.title("Credits")
        credits_win.geometry("300x200")
    
        listbox = Listbox(credits_win)
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
    
        for line in credits:
            listbox.insert(tk.END, line)

    def run(self):
        self.window.mainloop()

    def get_output_path(self) -> Optional[Path]:
        """Get the selected output path"""
        path = self.output_var.get().strip()
        return Path(path) if path else None

    def get_configs(self) -> Dict[str, AnimationConfig]:
        """Get all animation configurations"""
        return self.table.get_configs()
