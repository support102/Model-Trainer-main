from tkinter import *
from tkinter import ttk, filedialog, messagebox
from PIL import ImageTk, Image
from csv import DictWriter, DictReader
import os
import random
import json
from datetime import datetime
import threading
import time

class ImageAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Annotator Pro")
        self.root.geometry("1200x800")
        
        # Try to set icon if available
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass  # Skip if icon not found
            
        # Initialize variables
        self.current = 0
        self.i_path = ""
        self.o_path = ""
        self.images = []
        self.image_files = []
        self.canvas = None
        self.annotations_per_image = {}
        self.label_list = []
        self.current_label = StringVar()  # Will be set once labels are loaded
        self.current_points = []
        self.label_colors = {}
        self.resized_images_cache = {}
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False
        self.undo_stack = []
        self.autosave_timer = None
        self.last_save_time = None
        self.display_scale = 1.0
        
        # Define theme colors
        self.theme = {
            "primary": "#3498db",
            "secondary": "#2c3e50",
            "accent": "#1abc9c",
            "light": "#ecf0f1",
            "dark": "#34495e",
            "success": "#2ecc71",
            "warning": "#f39c12",
            "danger": "#e74c3c"
        }
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure("TButton", background=self.theme["primary"], foreground="black", font=("Arial", 10))
        self.style.configure("Nav.TButton", foreground="black")  # Configure black text color for all nav buttons
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("TFrame", background=self.theme["light"])
        
        # Show setup screen
        self.show_setup_screen()
        
        # Add window event handlers
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def get_random_color(self):
        colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", 
                  "#1abc9c", "#34495e", "#7f8c8d", "#d35400", "#c0392b",
                  "#16a085", "#27ae60", "#2980b9", "#8e44ad", "#f1c40f"]
        return random.choice(colors)

    def get_label_color(self, label):
        if label not in self.label_colors:
            self.label_colors[label] = self.get_random_color()
        return self.label_colors[label]

    def show_setup_screen(self):
        # Clear current widgets
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Configure styles
        self.style.configure("Title.TLabel", font=("Helvetica", 24, "bold"), foreground=self.theme["secondary"])
        self.style.configure("Subtitle.TLabel", font=("Helvetica", 12), foreground=self.theme["dark"])
        self.style.configure("Card.TFrame", background=self.theme["light"], relief="raised")
        self.style.configure("Action.TButton", font=("Helvetica", 11), padding=10)
        self.style.configure("Primary.TButton", background=self.theme["primary"], foreground="white")
        
        # Create main frame with padding and background
        main_frame = ttk.Frame(self.root, padding="40", style="Card.TFrame")
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # App title with enhanced styling
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=X, pady=(0, 30))
        ttk.Label(title_frame, text="Image Annotator Pro", style="Title.TLabel").pack()
        ttk.Label(title_frame, 
                 text="Streamline your dataset preparation with powerful annotation tools", 
                 style="Subtitle.TLabel").pack(pady=(5, 0))
        
        # Create a card-style container for the form
        form_card = ttk.LabelFrame(main_frame, text="Project Configuration", padding="20")
        form_card.pack(fill=X, pady=(0, 20))
        
        # Input folder with icon
        input_folder_frame = ttk.Frame(form_card)
        input_folder_frame.pack(fill=X, pady=(0, 15))
        ttk.Label(input_folder_frame, text="📁 Input Images Folder", 
                 font=("Helvetica", 10, "bold")).pack(anchor=W, pady=(0, 5))
        input_container = ttk.Frame(input_folder_frame)
        input_container.pack(fill=X)
        self.input_entry = ttk.Entry(input_container)
        self.input_entry.pack(side=LEFT, expand=True, fill=X, padx=(0, 10))
        ttk.Button(input_container, text="Browse", style="Action.TButton",
                  command=lambda: self.browse_folder(self.input_entry)).pack(side=RIGHT)
        
        # Output folder with icon
        output_folder_frame = ttk.Frame(form_card)
        output_folder_frame.pack(fill=X, pady=(0, 15))
        ttk.Label(output_folder_frame, text="💾 Output Folder", 
                 font=("Helvetica", 10, "bold")).pack(anchor=W, pady=(0, 5))
        output_container = ttk.Frame(output_folder_frame)
        output_container.pack(fill=X)
        self.output_entry = ttk.Entry(output_container)
        self.output_entry.pack(side=LEFT, expand=True, fill=X, padx=(0, 10))
        ttk.Button(output_container, text="Browse", style="Action.TButton",
                  command=lambda: self.browse_folder(self.output_entry)).pack(side=RIGHT)
        
        # Labels section with icon
        labels_frame = ttk.Frame(form_card)
        labels_frame.pack(fill=X, pady=(0, 15))
        ttk.Label(labels_frame, text="🏷️ Object Labels", 
                 font=("Helvetica", 10, "bold")).pack(anchor=W, pady=(0, 5))
        self.label_entry = ttk.Entry(labels_frame)
        self.label_entry.pack(fill=X)
        self.label_entry.insert(0, "Person, Car, Dog, Cat")
        ttk.Label(labels_frame, text="Separate labels with commas", 
                 foreground=self.theme["dark"]).pack(anchor=W, pady=(2, 0))
        
        # Action buttons with enhanced styling
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X, pady=(20, 10))
        
        # Load project button with icon
        load_btn = ttk.Button(button_frame, text="📂 Load Project", style="Action.TButton",
                            command=self.load_previous_project)
        load_btn.pack(side=LEFT)
        
        # Create separator
        ttk.Frame(button_frame).pack(side=LEFT, expand=True)
        
        # Right-side buttons
        ttk.Button(button_frame, text="❌ Exit", style="Action.TButton",
                  command=self.on_close).pack(side=RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="✨ Start New Project", style="Action.TButton",
                  command=self.proceed_to_annotation).pack(side=RIGHT)
        
        # Footer with version and help
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=X, pady=(20, 0))
        ttk.Label(footer_frame, text="Need help? Press F1 for documentation",
                 foreground=self.theme["dark"]).pack(side=LEFT)
        ttk.Label(footer_frame, text="Version 1.0",
                 foreground=self.theme["dark"]).pack(side=RIGHT)
        
        # Add keyboard shortcuts
        self.root.bind('<F1>', lambda e: self.show_help())
        self.root.bind('<Return>', lambda e: self.proceed_to_annotation())
        self.root.bind('<Escape>', lambda e: self.on_close())
    
    def browse_folder(self, entry_widget):
        """Helper function to browse and update folder entry"""
        # Clear the entry first
        entry_widget.delete(0, END)
        # Get the folder path
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.insert(0, folder)
            
    def show_help(self):
        """Show help documentation"""
        help_text = """
Image Annotator Pro - Quick Help

1. Project Setup:
   • Input Folder: Select the folder containing your images
   • Output Folder: Choose where to save annotations
   • Labels: Enter object labels separated by commas

2. Keyboard Shortcuts:
   • Enter: Start new project
   • F1: Show this help
   • Escape: Exit application

3. Tips:
   • You can drag and drop folders into the entry fields
   • Labels can be added/edited later in the annotation screen
   • Annotations are auto-saved every 5 minutes
        """
        messagebox.showinfo("Help", help_text)

    def load_previous_project(self):
        project_file = filedialog.askopenfilename(defaultextension=".json", filetypes=[("Project Files", "*.json")])
        if not project_file:
            return
            
        try:
            with open(project_file, 'r') as f:
                project_data = json.load(f)
                
            self.i_path = project_data.get('input_path', '')
            self.o_path = project_data.get('output_path', '')
            self.label_list = project_data.get('labels', [])
            self.annotations_per_image = project_data.get('annotations', {})
            self.label_colors = project_data.get('label_colors', {})
            
            # Update UI with loaded data
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, self.i_path)
            
            self.output_entry.delete(0, END)
            self.output_entry.insert(0, self.o_path)
            
            self.label_entry.delete(0, END)
            self.label_entry.insert(0, ", ".join(self.label_list))
            
            messagebox.showinfo("Project Loaded", f"Successfully loaded project with {len(self.annotations_per_image)} annotated images")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project: {str(e)}")

    def proceed_to_annotation(self):
        self.i_path = self.input_entry.get().strip()
        self.o_path = self.output_entry.get().strip()
        raw_labels = self.label_entry.get().strip()
        
        # Validate input
        if not self.i_path or not os.path.isdir(self.i_path):
            messagebox.showerror("Error", "Please select a valid input directory")
            return
            
        if not self.o_path:
            messagebox.showerror("Error", "Please select an output directory")
            return
            
        # Create output directory if it doesn't exist
        if not os.path.exists(self.o_path):
            try:
                os.makedirs(self.o_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output directory: {str(e)}")
                return
        
        # Process labels
        self.label_list = [label.strip() for label in raw_labels.split(',') if label.strip()]
        if not self.label_list:
            messagebox.showerror("Error", "Please specify at least one object label")
            return
            
        # Set the first label as default
        self.current_label.set(self.label_list[0])
            
        # Setup annotation screen
        self.show_annotation_screen()
        
        # Load images and start autosave timer
        self.load_images()
        self.setup_autosave()

    def show_annotation_screen(self):
        # Clear current widgets
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Create toolbar
        self.toolbar = ttk.Frame(main_frame, padding="5")
        self.toolbar.pack(fill=X)
        
        # Navigation buttons
        nav_frame = ttk.Frame(self.toolbar)
        nav_frame.pack(side=LEFT, padx=5)
        
        self.style.configure("Nav.TButton", foreground="black")  # Configure black text color for all nav buttons
        ttk.Button(nav_frame, text="⏮", width=3, command=lambda: self.navigate_image_to(0), style="Nav.TButton").pack(side=LEFT, padx=2)
        ttk.Button(nav_frame, text="◀", width=3, command=lambda: self.navigate_image(-1), style="Nav.TButton").pack(side=LEFT, padx=2)
        ttk.Button(nav_frame, text="▶", width=3, command=lambda: self.navigate_image(1), style="Nav.TButton").pack(side=LEFT, padx=2)
        ttk.Button(nav_frame, text="⏭", width=3, command=lambda: self.navigate_image_to(-1), style="Nav.TButton").pack(side=LEFT, padx=2)
        
        # Label selection
        label_frame = ttk.Frame(self.toolbar)
        label_frame.pack(side=LEFT, padx=10)
        
        ttk.Label(label_frame, text="Label:").pack(side=LEFT, padx=5)
        
        # Add label management and editing
        edit_frame = ttk.Frame(label_frame)
        edit_frame.pack(side=LEFT)
        
        self.label_menu = ttk.Combobox(label_frame, textvariable=self.current_label, values=self.label_list, width=15)
        self.label_menu.pack(side=LEFT, padx=5)
        
        # Make combobox editable
        self.label_menu.configure(state='normal')
        
        # Add functionality to handle new label addition
        def add_new_label(event):
            new_label = self.current_label.get().strip()
            if new_label and new_label not in self.label_list:
                self.label_list.append(new_label)
                self.label_menu['values'] = self.label_list
        self.label_menu.bind('<Return>', add_new_label)
        
        # Add color indicator
        self.color_indicator = Label(label_frame, text="■", font=("Arial", 16), fg=self.get_label_color(self.current_label.get()))
        self.color_indicator.pack(side=LEFT, padx=5)
        
        # Bind label change event
        self.current_label.trace("w", self.on_label_change)
        
        # Tool buttons
        tool_frame = ttk.Frame(self.toolbar)
        tool_frame.pack(side=LEFT, padx=10)
        
        ttk.Button(tool_frame, text="Clear All", command=self.clear_all_annotations, style="Nav.TButton").pack(side=LEFT, padx=5)
        ttk.Button(tool_frame, text="Undo", command=self.undo_last_annotation, style="Nav.TButton").pack(side=LEFT, padx=5)
        
        # Zoom controls
        zoom_frame = ttk.Frame(self.toolbar)
        zoom_frame.pack(side=LEFT, padx=10)
        
        ttk.Button(zoom_frame, text="−", width=3, command=lambda: self.zoom(-0.1), style="Nav.TButton").pack(side=LEFT, padx=2)
        self.zoom_label = ttk.Label(zoom_frame, text="100%", width=5)
        self.zoom_label.pack(side=LEFT, padx=2)
        ttk.Button(zoom_frame, text="+", width=3, command=lambda: self.zoom(0.1), style="Nav.TButton").pack(side=LEFT, padx=2)
        ttk.Button(zoom_frame, text="1:1", width=3, command=lambda: self.zoom(reset=True), style="Nav.TButton").pack(side=LEFT, padx=2)
        
        # Right side buttons
        right_frame = ttk.Frame(self.toolbar)
        right_frame.pack(side=RIGHT, padx=5)
        
        ttk.Button(right_frame, text="Save", command=self.save_annotations, style="Nav.TButton").pack(side=RIGHT, padx=5)
        ttk.Button(right_frame, text="Export", command=self.export_menu, style="Nav.TButton").pack(side=RIGHT, padx=5)
        ttk.Button(right_frame, text="Settings", command=self.show_settings, style="Nav.TButton").pack(side=RIGHT, padx=5)
        
        # Annotation area
        self.canvas_frame = ttk.Frame(main_frame)
        self.canvas_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Create canvas container with specific size
        canvas_container = ttk.Frame(self.canvas_frame)
        canvas_container.pack(fill=BOTH, expand=True)
        
        # Configure grid weights for proper centering
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)
        
        # Force the canvas container to have a minimum size
        canvas_container.update_idletasks()
        min_width = self.root.winfo_width() - 40
        min_height = self.root.winfo_height() - 100
        canvas_container.config(width=min_width, height=min_height)
        
        self.canvas = Canvas(canvas_container, bg="#2c3e50", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        self.v_scrollbar = Scrollbar(canvas_container, orient=VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.h_scrollbar = Scrollbar(canvas_container, orient=HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.canvas.config(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.draw_shape_start)
        self.canvas.bind("<B1-Motion>", self.draw_shape_update)
        self.canvas.bind("<ButtonRelease-1>", self.draw_shape_finalize)
        self.canvas.bind("<Button-3>", self.canvas_right_click)
        self.canvas.bind("<MouseWheel>", self.mouse_scroll)
        
        # Status bar
        status_frame = ttk.Frame(main_frame, padding="5")
        status_frame.pack(fill=X, side=BOTTOM)
        
        self.statusBar = ttk.Label(status_frame, text="No images loaded.", anchor=E)
        self.statusBar.pack(side=RIGHT)
        
        self.annotation_count = ttk.Label(status_frame, text="Annotations: 0", anchor=W)
        self.annotation_count.pack(side=LEFT)
        
        self.autosave_status = ttk.Label(status_frame, text="", anchor=W)
        self.autosave_status.pack(side=LEFT, padx=20)
        
        # Bind keyboard shortcuts
        self.root.bind('<Left>', lambda e: self.navigate_image(-1))
        self.root.bind('<Right>', lambda e: self.navigate_image(1))
        self.root.bind('a', lambda e: self.navigate_image(-1))  # A key for previous image
        self.root.bind('d', lambda e: self.navigate_image(1))   # D key for next image
        self.root.bind('<Return>', lambda e: self.save_annotations())
        self.root.bind('<Control-z>', lambda e: self.undo_last_annotation())
        self.root.bind('<Control-s>', lambda e: self.save_annotations())
        self.root.bind('<Escape>', lambda e: self.clear_current_drawing())
        
        # Number key shortcuts for labels
        for i in range(10):
            self.root.bind(str(i if i > 0 else 10), lambda e, idx=i-1 if i > 0 else 9: self.select_label(idx))

    def export_menu(self):
        export_window = Toplevel(self.root)
        export_window.title("Export Options")
        export_window.geometry("400x300")
        export_window.transient(self.root)
        export_window.grab_set()
        
        ttk.Label(export_window, text="Export Format", font=("Arial", 12, "bold")).pack(pady=(20, 10))
        
        formats = [
            ("CSV Format", "csv"),
            ("YOLO Format", "yolo"),
            ("COCO Format", "coco"),
            ("Pascal VOC Format", "voc")
        ]
        
        format_var = StringVar(value="csv")
        
        for text, value in formats:
            ttk.Radiobutton(export_window, text=text, variable=format_var, value=value).pack(anchor=W, padx=20, pady=5)
        
        ttk.Button(export_window, text="Export", command=lambda: self.export_annotations(format_var.get(), export_window), style="Nav.TButton").pack(pady=20)

    def export_annotations(self, format_type, window=None):
        if format_type == "csv":
            self.save_annotations()
        elif format_type == "yolo":
            self.export_yolo_format()
        elif format_type == "coco":
            messagebox.showinfo("Info", "COCO format export will be available in the next update")
        elif format_type == "voc":
            messagebox.showinfo("Info", "Pascal VOC format export will be available in the next update")
            
        if window:
            window.destroy()

    def export_yolo_format(self):
        try:
            # Create classes.txt
            with open(os.path.join(self.o_path, "classes.txt"), "w") as f:
                for label in self.label_list:
                    f.write(f"{label}\n")
            
            # Process each image
            for img_idx, img_path in enumerate(self.image_files):
                img_name = os.path.basename(img_path)
                base_name = os.path.splitext(img_name)[0]
                
                # If no annotations for this image, continue
                if img_name not in self.annotations_per_image:
                    continue
                    
                # Get image dimensions
                img = self.images[img_idx]
                img_w, img_h = img.size
                
                # Create YOLO format file
                with open(os.path.join(self.o_path, f"{base_name}.txt"), "w") as f:
                    for ann in self.annotations_per_image.get(img_name, []):
                        (x1, y1), (x2, y2) = ann["points"]
                        
                        # Convert to YOLO format (center_x, center_y, width, height)
                        # All values are normalized between 0 and 1
                        center_x = (x1 + x2) / (2 * img_w)
                        center_y = (y1 + y2) / (2 * img_h)
                        width = abs(x2 - x1) / img_w
                        height = abs(y2 - y1) / img_h
                        
                        # Get class index
                        class_idx = self.label_list.index(ann["label"])
                        
                        # Write to file
                        f.write(f"{class_idx} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}\n")
            
            messagebox.showinfo("Export Complete", f"YOLO format annotations exported to {self.o_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export YOLO format: {str(e)}")

    def show_settings(self):
        settings_window = Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        ttk.Label(settings_window, text="Application Settings", font=("Arial", 12, "bold")).pack(pady=(20, 10))
        
        # Autosave interval
        autosave_frame = ttk.Frame(settings_window, padding="10")
        autosave_frame.pack(fill=X)
        
        ttk.Label(autosave_frame, text="Autosave Interval (minutes):").pack(side=LEFT, padx=5)
        autosave_var = StringVar(value="5")
        autosave_entry = ttk.Entry(autosave_frame, textvariable=autosave_var, width=5)
        autosave_entry.pack(side=LEFT, padx=5)
        
        # Keyboard shortcuts
        ttk.Label(settings_window, text="Keyboard Shortcuts", font=("Arial", 10, "bold")).pack(pady=(20, 10), anchor=W, padx=20)
        
        shortcuts = [
            ("Next Image", "Right Arrow"),
            ("Previous Image", "Left Arrow"),
            ("Save", "Ctrl+S"),
            ("Undo", "Ctrl+Z"),
            ("Cancel Drawing", "Escape"),
            ("Quick Label Selection", "1-0 (number keys)")
        ]
        
        for action, key in shortcuts:
            shortcut_frame = ttk.Frame(settings_window)
            shortcut_frame.pack(fill=X, padx=20, pady=2)
            ttk.Label(shortcut_frame, text=action, width=20).pack(side=LEFT)
            ttk.Label(shortcut_frame, text=key).pack(side=LEFT)
            
        ttk.Button(settings_window, text="Close", command=settings_window.destroy, style="Nav.TButton").pack(pady=20)

    def on_label_change(self, *args):
        # Update color indicator
        label = self.current_label.get()
        self.color_indicator.config(fg=self.get_label_color(label))

    def zoom(self, delta=0, reset=False):
        if reset:
            self.display_scale = 1.0
        else:
            new_scale = self.display_scale + delta
            if 0.1 <= new_scale <= 3.0:  # Limit zoom range
                self.display_scale = new_scale
                
        # Update zoom label
        self.zoom_label.config(text=f"{int(self.display_scale*100)}%")
        
        # Refresh display
        if self.images:
            self.show_image(self.current)

    def mouse_scroll(self, event):
        # Ctrl+Scroll for zoom
        if event.state & 0x4:  # Check if Ctrl key is pressed
            if event.delta > 0:
                self.zoom(0.1)
            else:
                self.zoom(-0.1)
        # Regular scroll for vertical navigation
        else:
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def canvas_right_click(self, event):
        if not self.images:
            return
            
        # Show context menu
        menu = Menu(self.root, tearoff=0)
        menu.add_command(label="Clear All Annotations", command=self.clear_all_annotations)
        menu.add_command(label="Undo Last Annotation", command=self.undo_last_annotation)
        menu.add_separator()
        
        # Submenu for labels
        label_menu = Menu(menu, tearoff=0)
        for label in self.label_list:
            label_menu.add_command(label=label, command=lambda l=label: self.set_label(l))
        menu.add_cascade(label="Change Label", menu=label_menu)
        
        menu.tk_popup(event.x_root, event.y_root)

    def set_label(self, label):
        self.current_label.set(label)

    def select_label(self, idx):
        if idx < len(self.label_list):
            self.current_label.set(self.label_list[idx])

    def clear_current_drawing(self):
        if self.current_points:
            self.current_points = []
            self.show_image(self.current)

    def clear_all_annotations(self):
        if not self.images:
            return
            
        result = messagebox.askyesno("Confirm", "Clear all annotations for the current image?")
        if not result:
            return
            
        img_name = os.path.basename(self.image_files[self.current])
        
        # Add to undo stack before clearing
        if img_name in self.annotations_per_image:
            self.undo_stack.append({
                "action": "clear_all",
                "image": img_name,
                "annotations": self.annotations_per_image[img_name].copy()
            })
            
        # Clear annotations
        self.annotations_per_image[img_name] = []
        self.show_image(self.current)
        self.update_annotation_count()

    def undo_last_annotation(self):
        if not self.undo_stack:
            return
            
        action = self.undo_stack.pop()
        action_type = action["action"]
        
        if action_type == "add":
            # Remove the last added annotation
            img_name = action["image"]
            if img_name in self.annotations_per_image and self.annotations_per_image[img_name]:
                self.annotations_per_image[img_name].pop()
        elif action_type == "clear_all":
            # Restore all cleared annotations
            img_name = action["image"]
            self.annotations_per_image[img_name] = action["annotations"]
            
        self.show_image(self.current)
        self.update_annotation_count()

    def navigate_image_to(self, idx):
        if not self.images:
            return
            
        if idx < 0:  # Navigate to last image
            self.current = len(self.images) - 1
        else:  # Navigate to specific index
            self.current = min(idx, len(self.images) - 1)
            
        self.show_image(self.current)

    def draw_shape_start(self, event):
        if not self.images:
            return
            
        # Calculate actual image coordinates
        x, y = self.get_image_coords(event.x, event.y)
        
        # Start drawing rectangle
        self.current_points = [(x, y), (x, y)]
        self.temp_rect = None  # Store the temporary rectangle ID

    def draw_shape_update(self, event):
        if not self.images or not self.current_points:
            return
            
        # Calculate actual image coordinates
        x, y = self.get_image_coords(event.x, event.y)
        
        # Update rectangle end point
        if len(self.current_points) == 2:
            self.current_points[1] = (x, y)
            
            # Get canvas scale and offsets
            img = self.images[self.current]
            img_w, img_h = img.size
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            base_scale = min(canvas_width / img_w, canvas_height / img_h)
            scale = base_scale * self.display_scale
            
            # Calculate image position
            img_display_w = int(img_w * scale)
            img_display_h = int(img_h * scale)
            img_x = max(0, (canvas_width - img_display_w) // 2)
            img_y = max(0, (canvas_height - img_display_h) // 2)
            
            # Scale coordinates
            (x1, y1), (x2, y2) = self.current_points
            sx1 = img_x + x1 * scale
            sy1 = img_y + y1 * scale
            sx2 = img_x + x2 * scale
            sy2 = img_y + y2 * scale
            
            # Update or create temporary rectangle
            color = self.get_label_color(self.current_label.get())
            if self.temp_rect:
                self.canvas.coords(self.temp_rect, sx1, sy1, sx2, sy2)
            else:
                self.temp_rect = self.canvas.create_rectangle(
                    sx1, sy1, sx2, sy2, 
                    outline=color, 
                    dash=(2,2), 
                    width=2
                )

    def draw_shape_finalize(self, event):
        if not self.images or not self.current_points:
            return
            
        if len(self.current_points) == 2:
            # Get starting and ending points
            (x1, y1), (x2, y2) = self.current_points
            
            # Only add annotation if it's not too small
            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
                self.add_annotation("Rectangle", self.current_points)
                self.show_image(self.current)  # Refresh to show final state
            else:
                # Remove temporary rectangle if too small
                if self.temp_rect:
                    self.canvas.delete(self.temp_rect)
                
        self.current_points = []
        self.temp_rect = None

    def get_image_coords(self, canvas_x, canvas_y):
        if not self.images:
            return (0, 0)
            
        img = self.images[self.current]
        img_w, img_h = img.size
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Ensure canvas has proper dimensions
        if canvas_width < 10 or canvas_height < 10:
            canvas_width, canvas_height = 1200, 800
            
        # Calculate scale based on zoom factor
        base_scale = min(canvas_width / img_w, canvas_height / img_h)
        scale = base_scale * self.display_scale
        
        # Calculate image position on canvas
        img_display_w = int(img_w * scale)
        img_display_h = int(img_h * scale)
        
        # Calculate image offset (centered in canvas)
        offset_x = max(0, (canvas_width - img_display_w) // 2)
        offset_y = max(0, (canvas_height - img_display_h) // 2)
        
        # Get scroll position
        scroll_x = self.canvas.canvasx(canvas_x)
        scroll_y = self.canvas.canvasy(canvas_y)
        
        # Convert canvas coordinates to image coordinates
        img_x = (scroll_x - offset_x) / scale
        img_y = (scroll_y - offset_y) / scale
        
        # Constrain coordinates to image bounds
        img_x = max(0, min(img_w, img_x))
        img_y = max(0, min(img_h, img_y))
        
        return (img_x, img_y)

    def add_annotation(self, shape, points):
        if not self.images:
            return
            
        # Get current image name
        img_name = os.path.basename(self.image_files[self.current])
        
        # Create annotation
        color = self.get_label_color(self.current_label.get())
        ann = {
            "shape": shape, 
            "points": points.copy(), 
            "label": self.current_label.get(), 
            "color": color
        }
        
        # Initialize annotation list if needed
        if img_name not in self.annotations_per_image:
            self.annotations_per_image[img_name] = []
            
        # Add to undo stack
        self.undo_stack.append({
            "action": "add",
            "image": img_name
        })
        
        # Add annotation
        self.annotations_per_image[img_name].append(ann)
        self.update_annotation_count()

    def update_annotation_count(self):
        if not self.images:
            self.annotation_count.config(text="Annotations: 0")
            return
            
        img_name = os.path.basename(self.image_files[self.current])
        count = len(self.annotations_per_image.get(img_name, []))
        self.annotation_count.config(text=f"Annotations: {count}")

    def show_image(self, index):
        if not self.image_files:
            return
            
        # Clear canvas
        self.canvas.delete("all")
        
        # Get current image with lazy loading
        img = self._load_image(index)
        if not img:
            return
        img_w, img_h = img.size
        
        # Get canvas dimensions and update if needed
        self.canvas.update_idletasks()  # Force geometry update
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Ensure canvas has proper dimensions
        if canvas_width < 10 or canvas_height < 10:
            canvas_width, canvas_height = self.root.winfo_width() - 40, self.root.winfo_height() - 100  # Adjust for padding
            
        # Calculate scale based on zoom factor
        base_scale = min(canvas_width / img_w, canvas_height / img_h)
        scale = base_scale * self.display_scale
        
        # Calculate image dimensions after scaling
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        
        # Check cache for resized image
        cache_key = (index, new_w, new_h)
        if cache_key in self.resized_images_cache:
            resized_img = self.resized_images_cache[cache_key]
        else:
            # Use BILINEAR for faster resizing when zooming out, LANCZOS for zooming in
            resample = Image.LANCZOS if scale > 1 else Image.BILINEAR
            resized_img = img.resize((new_w, new_h), resample)
            
            # Manage cache size
            if len(self.resized_images_cache) > 5:  # Reduce cache size to 5
                # Remove oldest entries
                oldest_keys = list(self.resized_images_cache.keys())[:-4]  # Keep last 4
                for k in oldest_keys:
                    del self.resized_images_cache[k]
            self.resized_images_cache[cache_key] = resized_img
            
        # Convert to PhotoImage
        self.canvas.image = ImageTk.PhotoImage(resized_img)
        
        # Calculate image position (centered in canvas)
        img_x = max(0, (canvas_width - new_w) // 2)
        img_y = max(0, (canvas_height - new_h) // 2)
        
        # Create a larger scroll region to allow for proper centering
        scroll_width = max(canvas_width, new_w + img_x * 2)
        scroll_height = max(canvas_height, new_h + img_y * 2)
        
        # Draw image
        self.canvas.create_image(img_x, img_y, image=self.canvas.image, anchor=NW)
        
        # Set scroll region to include padding
        self.canvas.config(scrollregion=(0, 0, scroll_width, scroll_height))
        
        # Draw annotations
        img_name = os.path.basename(self.image_files[index])
        for ann in self.annotations_per_image.get(img_name, []):
            color = self.get_label_color(ann["label"])
            (x1, y1), (x2, y2) = ann["points"]
            
            # Scale coordinates to canvas
            sx1 = img_x + x1 * scale
            sy1 = img_y + y1 * scale
            sx2 = img_x + x2 * scale
            sy2 = img_y + y2 * scale
            
            # Draw rectangle
            self.canvas.create_rectangle(sx1, sy1, sx2, sy2, outline=color, width=2)
            
            # Draw label
            text_bg = self.canvas.create_rectangle(sx1, sy1-20, sx1+len(ann["label"])*8+10, sy1, 
                                                fill=color, outline=color)
            text = self.canvas.create_text(sx1+5, sy1-10, text=ann["label"], anchor=W, fill="white")
        
        # Draw current shape being created
        if self.current_points:
            color = self.get_label_color(self.current_label.get())
            (x1, y1), (x2, y2) = self.current_points
            
            # Scale coordinates to canvas
            sx1 = img_x + x1 * scale
            sy1 = img_y + y1 * scale
            sx2 = img_x + x2 * scale
            sy2 = img_y + y2 * scale
            
            # Draw rectangle with dashed line
            self.canvas.create_rectangle(sx1, sy1, sx2, sy2, outline=color, dash=(2,2), width=2)
            
        # Set scroll region
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        # Update status bar
        self.statusBar.config(text=f"Image {index + 1} of {len(self.images)} | {img_name} | {img_w}×{img_h}px")
        
        # Update annotation count
        self.update_annotation_count()

    def navigate_image(self, step):
        if not self.image_files:
            return
            
        # Calculate new index with bounds checking
        new_index = (self.current + step) % len(self.image_files)
        self.current = new_index
        
        # Load batch of images around new index
        self.load_image_batch(self.current)
        
        # Show new image
        self.show_image(self.current)
        
        # Report memory usage if it's high
        mem_usage = self.calculate_memory_usage()
        if mem_usage > 1000:  # Alert if over 1GB
            print(f"Warning: High memory usage: {mem_usage:.1f}MB")

    def load_images(self):
        """Load image paths and initialize the first batch of images"""
        # Get list of image files
        extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
        self.image_files = [os.path.join(self.i_path, f) for f in os.listdir(self.i_path)
                           if f.lower().endswith(extensions)]
        self.image_files.sort()
        
        if not self.image_files:
            messagebox.showerror("Error", "No valid images found in the input directory")
            return

        self.current = 0
        self.images = {}  # Dictionary to store loaded images
        self.load_image_batch(self.current)  # Load initial batch
        self.show_image(self.current)
        self.statusBar.config(text=f"Image 1 of {len(self.image_files)}")
        """Load images with optimizations for handling large datasets"""
        # Reset existing values
        self.images = {}  # Change to dictionary for lazy loading
        self.image_files = []
        self.current = 0
        self.resized_images_cache = {}
        self.total_loaded = 0
        
        try:
            # Create progress window
            progress_window = Toplevel(self.root)
            progress_window.title("Loading Images")
            progress_window.geometry("300x150")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            # Configure progress window
            progress_window.grid_rowconfigure(0, weight=1)
            progress_window.grid_columnconfigure(0, weight=1)
            
            # Create progress frame
            progress_frame = ttk.Frame(progress_window, padding="20")
            progress_frame.grid(row=0, column=0, sticky="nsew")
            
            # Create progress label
            progress_label = ttk.Label(progress_frame, text="Scanning image files...")
            progress_label.grid(row=0, column=0, pady=(0, 10))
            
            # Create progress bar
            progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=200)
            progress_bar.grid(row=1, column=0)
            
            valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif")
            file_list = []
            
            # Scan directory with progress update
            all_files = os.listdir(self.i_path)
            for i, f in enumerate(all_files):
                if os.path.isfile(os.path.join(self.i_path, f)) and f.lower().endswith(valid_extensions):
                    file_list.append(f)
                progress_bar['value'] = (i + 1) / len(all_files) * 100
                progress_window.update()
            # Sort files alphabetically
            file_list.sort()
            
            # Create full paths
            self.image_files = [os.path.join(self.i_path, f) for f in file_list]
            
            if not self.image_files:
                messagebox.showwarning("Warning", "No valid images found in selected directory")
                progress_window.destroy()
                return
                
            # Update progress message
            progress_label.config(text=f"Found {len(self.image_files)} images\nPreloading first few images...")
            progress_window.update()
            
            # Preload first few images for faster initial display
            for i in range(min(5, len(self.image_files))):
                self._load_image(i)
                progress_bar['value'] = (i + 1) / min(5, len(self.image_files)) * 100
                progress_window.update()
            
            progress_window.destroy()
            
            # Start background loading
            self.loading_thread = threading.Thread(target=self._background_loader,
                                                daemon=True)
            self.loading_thread.start()
            
            # Update UI
            self.root.update_idletasks()
            self.canvas.after(100, lambda: self.show_image(0))
            
            # Try to load existing annotations
            self.try_load_existing_annotations()
            
            # Start progress updater
            self._update_loading_progress()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load images: {str(e)}")
            if 'progress_window' in locals():
                progress_window.destroy()

    def _load_image(self, index):
        """Load a single image at the specified index with memory optimization"""
        if index not in self.images and 0 <= index < len(self.image_files):
            try:
                # Check current memory usage
                current_mem = self.calculate_memory_usage()
                if current_mem > 2000:  # If over 2GB
                    # Force cleanup of distant images
                    self.cleanup_distant_images(index, buffer=50)  # Reduced buffer during high memory
                
                # Open image and convert to RGB to ensure it's loaded into memory
                with Image.open(self.image_files[index]) as img:
                    # Determine if we should downsample the image
                    target_max_dim = 1920  # Max dimension for large images
                    orig_w, orig_h = img.size
                    scale = min(1.0, target_max_dim / max(orig_w, orig_h))
                    
                    if scale < 1.0:
                        new_w = int(orig_w * scale)
                        new_h = int(orig_h * scale)
                        img = img.resize((new_w, new_h), Image.LANCZOS)
                    
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        rgb_img = img.convert('RGB')
                    else:
                        rgb_img = img.copy()
                    
                self.images[index] = rgb_img
                self.total_loaded += 1
                
                # Clear resize cache if it's getting too large
                if len(self.resized_images_cache) > 10:
                    self.resized_images_cache.clear()
                    
                return rgb_img
                
            except Exception as e:
                print(f"Error loading image {self.image_files[index]}: {e}")
                return None
                
        return self.images.get(index)

    def _background_loader(self):
        """Background thread for loading remaining images with memory management"""
        try:
            # Initialize variables for adaptive batch loading
            batch_size = 10
            min_batch_size = 5
            max_batch_size = 20
            mem_threshold = 1500  # MB
            
            for i in range(0, len(self.image_files), batch_size):
                if not hasattr(self, 'loading_thread'):
                    break  # Stop if window is closed
                
                # Check memory usage and adjust batch size
                current_mem = self.calculate_memory_usage()
                if current_mem > mem_threshold:
                    # Reduce batch size if memory usage is high
                    batch_size = max(min_batch_size, batch_size - 5)
                    # Force cleanup of distant images
                    self.cleanup_distant_images(self.current, buffer=50)
                    # Wait for memory to be freed
                    time.sleep(0.5)
                else:
                    # Increase batch size if memory usage is low
                    batch_size = min(max_batch_size, batch_size + 1)
                
                # Load next batch
                batch_end = min(i + batch_size, len(self.image_files))
                for j in range(i, batch_end):
                    if j not in self.images:
                        self._load_image(j)
                        
                        # Update progress in status bar
                        if hasattr(self, 'statusBar'):
                            self.root.after(0, lambda: self.statusBar.config(
                                text=f"Loading images: {self.total_loaded}/{len(self.image_files)}"
                            ))
                
                # Adaptive delay based on memory pressure
                delay = 0.1 if current_mem < mem_threshold else 0.5
                time.sleep(delay)
                
        except Exception as e:
            print(f"Background loader error: {e}")
            
        finally:
            # Update status when done
            if hasattr(self, 'statusBar'):
                self.root.after(0, lambda: self.statusBar.config(
                    text=f"All {len(self.image_files)} images indexed"
                ))

    def _update_loading_progress(self):
        """Update status bar with loading progress"""
        if hasattr(self, 'statusBar') and self.total_loaded < len(self.image_files):
            self.statusBar.config(text=f"Loading images: {self.total_loaded}/{len(self.image_files)}")
            self.root.after(1000, self._update_loading_progress)
        elif hasattr(self, 'statusBar'):
            self.statusBar.config(text=f"All {len(self.image_files)} images loaded")

    def try_load_existing_annotations(self):
        # First clear any existing annotations to prevent duplicates
        self.annotations_per_image = {}
        
        # Check for both CSV and JSON project files
        csv_path = os.path.join(self.o_path, "annotations.csv")
        json_path = os.path.join(self.o_path, "project.json")
        
        # First try loading from project.json as it contains more metadata
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    project_data = json.load(f)
                    self.annotations_per_image = project_data.get('annotations', {})
                    self.label_colors = project_data.get('label_colors', {})
                    print(f"Loaded {len(self.annotations_per_image)} annotated images from project file")
                    return
            except Exception as e:
                print(f"Error loading project file: {str(e)}")
                self.annotations_per_image = {}  # Reset annotations if error
        
        # Fall back to CSV if no project file or error loading it
        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r", newline="") as file:
                    reader = DictReader(file)
                    for row in reader:
                        img_name = row["image"]
                        x1 = float(row["x1"])
                        y1 = float(row["y1"])
                        x2 = float(row["x2"])
                        y2 = float(row["y2"])
                        label = row["label"]
                        shape = row["shape"]
                        
                        # Create annotation
                        color = self.get_label_color(label)
                        ann = {
                            "shape": shape,
                            "points": [(x1, y1), (x2, y2)],
                            "label": label,
                            "color": color
                        }
                        
                        # Add to annotations
                        if img_name not in self.annotations_per_image:
                            self.annotations_per_image[img_name] = []
                        self.annotations_per_image[img_name].append(ann)
                
                print(f"Loaded {len(self.annotations_per_image)} annotated images from CSV file")
            except Exception as e:
                print(f"Error loading CSV annotations: {str(e)}")
                messagebox.showwarning("Warning", f"Failed to load existing annotations: {str(e)}")
                self.annotations_per_image = {}  # Reset annotations if error

    def save_annotations(self):
        if not self.images:
            messagebox.showwarning("Warning", "No images loaded")
            return
            
        try:
            # Prepare rows for CSV
            rows = []
            for img_name, anns in self.annotations_per_image.items():
                for ann in anns:
                    (x1, y1), (x2, y2) = ann["points"]
                    rows.append({
                        "image": img_name,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "label": ann["label"],
                        "shape": ann["shape"]
                    })
            
            if not rows:
                messagebox.showinfo("Info", "No annotations to save")
                return
                
            # Save to CSV using temporary file approach
            csv_path = os.path.join(self.o_path, "annotations.csv")
            temp_csv_path = csv_path + ".tmp"
            
            try:
                fieldnames = ["image", "x1", "y1", "x2", "y2", "label", "shape"]
                with open(temp_csv_path, "w", newline="") as file:
                    writer = DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                    
                # Only after successful write, replace the old file
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                os.rename(temp_csv_path, csv_path)
                
            except Exception as e:
                # Clean up temp file if something went wrong
                if os.path.exists(temp_csv_path):
                    try:
                        os.remove(temp_csv_path)
                    except:
                        pass
                raise e
                
            # Save project file using temporary file approach
            self.save_project_file()
                
            # Update status
            self.last_save_time = datetime.now()
            self.autosave_status.config(text=f"Last saved: {self.last_save_time.strftime('%H:%M:%S')}")
            
            messagebox.showinfo("Saved", f"Saved {len(rows)} annotations to {csv_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save annotations: {str(e)}")

    def save_project_file(self):
        # Create project data
        project_data = {
            "input_path": self.i_path,
            "output_path": self.o_path,
            "labels": self.label_list,
            "annotations": self.annotations_per_image,
            "label_colors": self.label_colors,
            "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save as JSON using temporary file approach
        project_path = os.path.join(self.o_path, "project.json")
        temp_project_path = project_path + ".tmp"
        
        try:
            # Save to temporary file first
            with open(temp_project_path, "w") as f:
                json.dump(project_data, f, indent=2)
                
            # Only after successful write, replace the old file
            if os.path.exists(project_path):
                os.remove(project_path)
            os.rename(temp_project_path, project_path)
            
        except Exception as e:
            # Clean up temp file if something went wrong
            if os.path.exists(temp_project_path):
                try:
                    os.remove(temp_project_path)
                except:
                    pass
            raise e

    def setup_autosave(self):
        def autosave_worker():
            while True:
                time.sleep(300)  # Default 5 minute interval
                if self.images and self.annotations_per_image:
                    # Only save if there are annotations and they haven't been saved recently
                    if not self.last_save_time or (datetime.now() - self.last_save_time).seconds > 60:
                        self.root.after(0, self.autosave)

        # Start autosave in a separate thread
        self.autosave_timer = threading.Thread(target=autosave_worker, daemon=True)
        self.autosave_timer.start()

    def autosave(self):
        try:
            # Skip if no annotations
            any_annotations = any(self.annotations_per_image.values())
            if not any_annotations:
                return

            # Prepare rows for CSV            
            rows = []
            for img_name, anns in self.annotations_per_image.items():
                for ann in anns:
                    (x1, y1), (x2, y2) = ann["points"]
                    rows.append({
                        "image": img_name,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "label": ann["label"],
                        "shape": ann["shape"]
                    })
            
            # Save to CSV
            autosave_path = os.path.join(self.o_path, "annotations_autosave.csv")
            fieldnames = ["image", "x1", "y1", "x2", "y2", "label", "shape"]
            
            # Use a temporary file to avoid file handle conflicts
            temp_path = autosave_path + ".tmp"
            try:
                with open(temp_path, "w", newline="") as file:
                    writer = DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                
                # Only after successful write, replace the old file
                if os.path.exists(autosave_path):
                    os.remove(autosave_path)
                os.rename(temp_path, autosave_path)
                
            except Exception as e:
                # Clean up temp file if something went wrong
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                raise e
                
            # Also save project file using temporary file approach
            project_path = os.path.join(self.o_path, "project.json")
            temp_project_path = project_path + ".tmp"
            
            try:
                # Create project data
                project_data = {
                    "input_path": self.i_path,
                    "output_path": self.o_path,
                    "labels": self.label_list,
                    "annotations": self.annotations_per_image,
                    "label_colors": self.label_colors,
                    "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Save to temporary file first
                with open(temp_project_path, "w") as f:
                    json.dump(project_data, f, indent=2)
                    
                # Only after successful write, replace the old file
                if os.path.exists(project_path):
                    os.remove(project_path)
                os.rename(temp_project_path, project_path)
                
            except Exception as e:
                # Clean up temp file if something went wrong
                if os.path.exists(temp_project_path):
                    try:
                        os.remove(temp_project_path)
                    except:
                        pass
                raise e
                
            # Update status
            self.last_save_time = datetime.now()
            self.autosave_status.config(text=f"Auto-saved: {self.last_save_time.strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"Autosave error: {e}")
            # Don't show error dialog for autosave failures to avoid interrupting the user

    def on_close(self):
        # Check if there are unsaved changes
        if self.annotations_per_image and (not self.last_save_time):
            result = messagebox.askyesnocancel("Save Changes", "Save changes before exiting?")
            if result is None:  # Cancel
                return
            if result:  # Yes
                self.save_annotations()
                
        # Cleanup resources
        try:
            # Clear image cache
            for img in self.images.values():
                try:
                    if hasattr(img, 'close'):
                        img.close()
                except:
                    pass
                    
            # Clear resize cache
            for img in self.resized_images_cache.values():
                try:
                    if hasattr(img, 'close'):
                        img.close()
                except:
                    pass
                    
            self.images.clear()
            self.resized_images_cache.clear()
            
            # Force garbage collection
            import gc
            gc.collect()
            
        except:
            pass  # Ensure cleanup doesn't prevent application from closing
            
        self.root.destroy()

    def load_image_batch(self, center_idx, window_size=100):
        """Load a batch of images around the given center index"""
        # Calculate the range of indices to load
        start_idx = max(0, center_idx - window_size // 2)
        end_idx = min(len(self.image_files), center_idx + window_size // 2)
        
        # Clean up images that are far from current view
        self.cleanup_distant_images(center_idx, buffer=window_size)
        
        # Load images in the window
        for idx in range(start_idx, end_idx):
            if idx not in self.images:
                try:
                    self._load_image(idx)
                except Exception as e:
                    print(f"Error loading image {self.image_files[idx]}: {str(e)}")
                    
    def cleanup_distant_images(self, center_idx, buffer=100):
        """Remove images that are far from the current view"""
        # Calculate the range of indices to keep
        start_idx = max(0, center_idx - buffer // 2)
        end_idx = min(len(self.image_files), center_idx + buffer // 2)
        
        # Get indices to remove
        indices_to_remove = [idx for idx in self.images.keys() 
                           if idx < start_idx or idx > end_idx]
        
        # Remove distant images
        for idx in indices_to_remove:
            try:
                if hasattr(self.images[idx], 'close'):
                    self.images[idx].close()
                del self.images[idx]
            except Exception as e:
                print(f"Error cleaning up image {idx}: {str(e)}")
                
    def calculate_memory_usage(self):
        """Calculate approximate memory usage of loaded images in MB"""
        total_bytes = 0
        for img in self.images.values():
            try:
                if isinstance(img, Image.Image):
                    # Calculate bytes per pixel (assuming RGB or RGBA)
                    bytes_per_pixel = len(img.getbands())
                    # Calculate total bytes
                    total_bytes += img.width * img.height * bytes_per_pixel
            except:
                continue
        return total_bytes / (1024 * 1024)  # Convert to MB

def main():
    root = Tk()
    app = ImageAnnotator(root)
    root.mainloop()

if __name__ == "__main__":
    main()