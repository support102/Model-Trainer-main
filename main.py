from tkinter import *
from tkinter import filedialog, messagebox
from PIL import ImageTk, Image
from csv import DictWriter
import os
import random

root = Tk()
root.title("Image Annotator for Dataset Preparation")
root.geometry("1200x800")
root.iconbitmap("icon.ico")

current, i_path, o_path, images, canvas = 0, "", "", [], None
annotations_per_image = {}
label_list = []
current_label = StringVar(value="Object")
current_points = []
label_colors = {}
resized_images_cache = {}


def get_random_color():
    return "#%06x" % random.randint(0, 0xFFFFFF)

def get_label_color(label):
    if label not in label_colors:
        label_colors[label] = get_random_color()
    return label_colors[label]

def show_setup_screen():
    for widget in root.winfo_children():
        widget.destroy()
    setup_frame = Frame(root)
    setup_frame.pack(fill=BOTH, expand=True)
    Label(setup_frame, text="Select Input Folder").pack(pady=5)
    input_entry = Entry(setup_frame, width=50)
    input_entry.pack(pady=2)
    Button(setup_frame, text="Browse", command=lambda: input_entry.insert(0, filedialog.askdirectory())).pack(pady=2)
    Label(setup_frame, text="Select Output Folder").pack(pady=5)
    output_entry = Entry(setup_frame, width=50)
    output_entry.pack(pady=2)
    Button(setup_frame, text="Browse", command=lambda: output_entry.insert(0, filedialog.askdirectory())).pack(pady=2)
    Label(setup_frame, text="Add Object Labels (comma separated)").pack(pady=5)
    label_entry = Entry(setup_frame, width=50)
    label_entry.pack(pady=2)
    def proceed():
        global i_path, o_path, label_list
        i_path = input_entry.get()
        o_path = output_entry.get()
        label_list = [l.strip() for l in label_entry.get().split(",") if l.strip()]
        if i_path and o_path and label_list:
            show_annotation_screen()
        else:
            messagebox.showerror("Error", "Please set all fields and at least one label.")
    Button(setup_frame, text="Proceed", command=proceed).pack(pady=10)

def show_annotation_screen():
    for widget in root.winfo_children():
        widget.destroy()
    global toolbar, canvas_frame, canvas, statusBar
    toolbar = Frame(root)
    toolbar.pack(fill=X)
    Button(toolbar, text="Save Annotations", command=save_annotations).pack(side=LEFT, padx=5)
    Button(toolbar, text="Clear Rectangles", command=clear_rectangles).pack(side=LEFT, padx=5)
    Button(toolbar, text="<<", command=lambda: navigate_image(-1)).pack(side=LEFT, padx=5)
    Button(toolbar, text=">>", command=lambda: navigate_image(1)).pack(side=LEFT, padx=5)
    Label(toolbar, text="Label:").pack(side=LEFT, padx=5)
    label_menu = OptionMenu(toolbar, current_label, *label_list)
    label_menu.pack(side=LEFT, padx=5)
    canvas_frame = Frame(root)
    canvas_frame.pack(fill=BOTH, expand=True)
    canvas = Canvas(canvas_frame, bg="grey")
    scroll_x = Scrollbar(canvas_frame, orient=HORIZONTAL, command=canvas.xview)
    scroll_y = Scrollbar(canvas_frame, orient=VERTICAL, command=canvas.yview)
    canvas.config(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
    scroll_x.pack(side=BOTTOM, fill=X)
    scroll_y.pack(side=RIGHT, fill=Y)
    canvas.pack(fill=BOTH, expand=True)
    canvas.bind("<Button-1>", draw_shape_start)
    canvas.bind("<B1-Motion>", draw_shape_update)
    canvas.bind("<ButtonRelease-1>", draw_shape_finalize)
    statusBar = Label(root, text="No images loaded.", bd=1, anchor=E)
    statusBar.pack(fill=X)
    root.bind('<Left>', lambda e: navigate_image(-1))
    root.bind('<Right>', lambda e: navigate_image(1))
    root.bind('<Return>', lambda e: save_annotations())
    root.bind('1', lambda e: select_label(0))
    root.bind('2', lambda e: select_label(1))
    root.bind('3', lambda e: select_label(2))
    root.bind('4', lambda e: select_label(3))
    load_images()

def select_label(idx):
    if idx < len(label_list):
        current_label.set(label_list[idx])

def clear_rectangles():
    img_name = f"image{current+1}.png"
    annotations_per_image[img_name] = []
    show_image(current)


def draw_shape_start(event):
    global current_points
    img = images[current]
    img_w, img_h = img.size
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()
    if canvas_width < 10 or canvas_height < 10:
        canvas_width, canvas_height = 1200, 800
    scale = min(canvas_width / img_w, canvas_height / img_h)
    x, y = event.x / scale, event.y / scale
    current_points = [(x, y), (x, y)]
    show_image(current)

prev_drawn_point = [None]
def draw_shape_update(event):
    global current_points
    img = images[current]
    img_w, img_h = img.size
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()
    if canvas_width < 10 or canvas_height < 10:
        canvas_width, canvas_height = 1200, 800
    scale = min(canvas_width / img_w, canvas_height / img_h)
    x, y = event.x / scale, event.y / scale
    if current_points:
        if prev_drawn_point[0] != (x, y):
            current_points[1] = (x, y)
            prev_drawn_point[0] = (x, y)
            show_image(current)

def draw_shape_finalize(event):
    global current_points
    if len(current_points) == 2:
        add_annotation("Rectangle", current_points)
        current_points = []
    show_image(current)

def add_annotation(shape, points):
    color = get_label_color(current_label.get())
    ann = {"shape": shape, "points": points.copy(), "label": current_label.get(), "color": color}
    img_name = f"image{current+1}.png"
    if img_name not in annotations_per_image:
        annotations_per_image[img_name] = []
    annotations_per_image[img_name].append(ann)

def show_image(index):
    canvas.delete("all")
    img = images[index]
    img_w, img_h = img.size
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()
    if canvas_width < 10 or canvas_height < 10:
        canvas_width, canvas_height = 1200, 800
    scale = min(canvas_width / img_w, canvas_height / img_h)
    new_w, new_h = int(img_w * scale), int(img_h * scale)
    cache_key = (index, new_w, new_h)
    if cache_key in resized_images_cache:
        resized_img = resized_images_cache[cache_key]
    else:
        resized_img = img.resize((new_w, new_h), Image.LANCZOS)
        resized_images_cache[cache_key] = resized_img
    canvas.image = ImageTk.PhotoImage(resized_img)
    canvas.create_image(0, 0, image=canvas.image, anchor=NW)
    img_name = f"image{index+1}.png"
    for ann in annotations_per_image.get(img_name, []):
        color = get_label_color(ann["label"])
        (x1, y1), (x2, y2) = ann["points"]
        sx1, sy1, sx2, sy2 = x1 * scale, y1 * scale, x2 * scale, y2 * scale
        canvas.create_rectangle(sx1, sy1, sx2, sy2, outline=color, width=2)

    if current_points:
        color = get_label_color(current_label.get())
        (x1, y1), (x2, y2) = current_points
        sx1, sy1, sx2, sy2 = x1 * scale, y1 * scale, x2 * scale, y2 * scale
        canvas.create_rectangle(sx1, sy1, sx2, sy2, outline=color, dash=(2,2))
    canvas.config(scrollregion=canvas.bbox("all"))
    statusBar.config(text=f"Image {index + 1} of {len(images)}")

def navigate_image(step):
    global current
    current = (current + step) % len(images)
    show_image(current)

def save_annotations():
    rows = []
    for img_name, anns in annotations_per_image.items():
        for ann in anns:
            (x1, y1), (x2, y2) = ann["points"]
            rows.append({"image": img_name, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": ann["label"], "shape": "Rectangle"})
    if not rows:
        messagebox.showerror("Error", "No annotations to save.")
        return
    fieldnames = ["image", "x1", "y1", "x2", "y2", "label", "shape"]
    with open(f"{o_path}/annotations.csv", "w", newline="") as file:
        writer = DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    messagebox.showinfo("Saved!", "Annotations saved in annotations.csv.")

def load_images():
    global images
    images = [Image.open(os.path.join(i_path, f)) for f in os.listdir(i_path) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    if images:
        show_image(0)

if __name__ == "__main__":
    show_setup_screen()
    root.mainloop()
