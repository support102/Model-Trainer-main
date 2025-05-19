import os
import pandas as pd
from PIL import Image

# Path to your CSV and images folder
csv_path = r"input/annotations.csv"
images_dir = r"input"
labels_dir = r"labels"

# Create labels directory if not exists
os.makedirs(labels_dir, exist_ok=True)

# Read CSV
df = pd.read_csv(csv_path)

# Get unique labels and assign class ids
label_names = sorted(df['label'].unique())
label_to_id = {name: idx for idx, name in enumerate(label_names)}

# Group by image
for img_name, group in df.groupby('image'):
    img_path = os.path.join(images_dir, img_name)
    if not os.path.exists(img_path):
        print(f"Warning: {img_path} not found, skipping.")
        continue
    with Image.open(img_path) as img:
        w, h = img.size
    yolo_lines = []
    for _, row in group.iterrows():
        class_id = label_to_id[row['label']]
        # Get box
        x1, y1, x2, y2 = row['x1'], row['y1'], row['x2'], row['y2']
        # Convert to YOLO format (center x/y, width, height, normalized)
        xc = ((x1 + x2) / 2) / w
        yc = ((y1 + y2) / 2) / h
        bw = abs(x2 - x1) / w
        bh = abs(y2 - y1) / h
        yolo_lines.append(f"{class_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
    # Write to txt file
    txt_name = os.path.splitext(img_name)[0] + ".txt"
    with open(os.path.join(labels_dir, txt_name), 'w') as f:
        f.write("\n".join(yolo_lines))

# Save label map for reference
with open(os.path.join(labels_dir, "classes.txt"), 'w') as f:
    for name in label_names:
        f.write(f"{name}\n")

print("Conversion complete! YOLO label files are in the 'labels' folder.")
