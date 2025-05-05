from ultralytics import YOLO

# Load a model
model = YOLO("C:\Projects\card-style-generator\models\yolo11x.pt")

# Perform object detection on an image
results = model(r"C:\Users\romac\OneDrive\Рабочий стол\nsfwe\asd.jpg")
results[0].show()

print(results[0])