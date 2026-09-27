import os
from pathlib import Path

BASE = r'C:\Users\migue\Desktop\GTDM\TFG\privacy-shield\datasets\wider_face'

for split in ['WIDER_train', 'WIDER_val']:
    images_dir = Path(BASE) / split / 'images'
    labels_dir = Path(BASE) / split / 'labels'

    for img_path in images_dir.rglob('*.jpg'):
        subdir = img_path.parent.name
        label_flat = labels_dir / (img_path.stem + '.txt')
        label_target_dir = labels_dir / subdir
        label_target = label_target_dir / (img_path.stem + '.txt')

        if label_flat.exists() and not label_target.exists():
            label_target_dir.mkdir(parents=True, exist_ok=True)
            label_flat.rename(label_target)

    print(f'{split}: reorganizacion completada')

print('Listo.')