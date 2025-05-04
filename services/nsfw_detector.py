from PIL import Image
from transformers import pipeline
import os

folder_path = r"C:\Users\romac\OneDrive\Рабочий стол\nsfwe"
classifier = pipeline(
    "image-classification",
    model="Falconsai/nsfw_image_detection",
    use_fast=True
)


for filename in os.listdir(folder_path):
    if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        continue

    file_path = os.path.join(folder_path, filename)
    try:
        img = Image.open(file_path)
        results = classifier(img)
        # ищем метку с максимальным score
        best = max(results, key=lambda x: x["score"])
        label = best["label"]
        score = best["score"]
        # выводим округлённое до сотых
        print(f"{filename}: {label} ({score:.2f})")
    except Exception as e:
        print(f"{filename}: ошибка обработки — {e}")
