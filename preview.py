import tkinter as tk
from PIL import Image, ImageTk
from typing import List, Optional
import time
from threading import Thread
import queue

class PreviewWindow:
    def __init__(self, parent: tk.Tk, frames: List[Image.Image], fps: float):
        self.window = tk.Toplevel(parent)
        self.window.title("Animation Preview")
        
        self.frames = frames
        self.frame_delay = 1.0 / fps
        self.current_frame = 0
        self.playing = True
        self.photo_images: List[ImageTk.PhotoImage] = []
        
        # Convert PIL images to PhotoImage
        for frame in frames:
            photo = ImageTk.PhotoImage(frame)
            self.photo_images.append(photo)
            
        # Create canvas sized to the first frame
        self.canvas = tk.Canvas(
            self.window,
            width=frames[0].width,
            height=frames[0].height
        )
        self.canvas.pack(expand=True)
        
        # Create UI controls
        controls = tk.Frame(self.window)
        controls.pack(fill=tk.X, padx=5, pady=5)
        
        self.play_btn = tk.Button(
            controls, text="⏸️", command=self.toggle_play
        )
        self.play_btn.pack(side=tk.LEFT, padx=2)
        
        tk.Label(controls, text=f"FPS: {fps}").pack(side=tk.RIGHT, padx=2)
        
        # Start animation thread
        self.queue = queue.Queue()
        self.animation_thread = Thread(target=self._animate, daemon=True)
        self.animation_thread.start()
        
        # Start update loop
        self._update()
        
        # Center window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.window.geometry(f"+{x}+{y}")
        
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        
    def _animate(self):
        """Animation loop running in separate thread"""
        while self.playing:
            if self.current_frame >= len(self.frames):
                self.current_frame = 0
                
            # Put current frame index in queue
            self.queue.put(self.current_frame)
            
            # Wait for frame delay
            time.sleep(self.frame_delay)
            
            if self.playing:
                self.current_frame += 1
                
    def _update(self):
        """Update canvas from main thread"""
        try:
            # Get all pending frames
            while True:
                frame_idx = self.queue.get_nowait()
                # Update canvas
                self.canvas.delete("all")
                self.canvas.create_image(
                    self.frames[0].width // 2,
                    self.frames[0].height // 2,
                    image=self.photo_images[frame_idx]
                )
        except queue.Empty:
            pass
            
        # Schedule next update
        if not self.window.winfo_exists():
            return
        self.window.after(10, self._update)
        
    def toggle_play(self):
        """Toggle animation playback"""
        self.playing = not self.playing
        self.play_btn.configure(text="▶️" if not self.playing else "⏸️")
        
        if self.playing:
            self.animation_thread = Thread(target=self._animate, daemon=True)
            self.animation_thread.start()
            
    def close(self):
        """Close preview window"""
        self.playing = False
        self.window.destroy()