import base64
import io
from PIL import Image
try:
    from PIL import UnidentifiedImageError
except ImportError:
    # Для старых версий Pillow
    UnidentifiedImageError = (IOError, OSError)

try:
    import binascii # Для base64.binascii.Error
except ImportError:
    binascii = None # На случай отсутствия (маловероятно)

_Base64Error = binascii.Error if binascii else ValueError # Ошибка декодирования base64

from transformers import pipeline
import logging
from typing import Union # Для type hints

# Подавляем информационные сообщения от transformers
logging.getLogger("transformers").setLevel(logging.ERROR)

class NsfwDetector:
    """
    Класс для определения NSFW контента на изображении.
    Принимает путь к файлу, PIL Image объект или строку base64.
    """
    def __init__(self, model_name="Falconsai/nsfw_image_detection"):
        """
        Инициализирует классификатор изображений.
        """
        try:
            self.classifier = pipeline(
                "image-classification",
                model=model_name,
                use_fast=True
            )
        except Exception as e:
            print(f"Ошибка инициализации модели: {e}")
            self.classifier = None

    def _load_image(self, image_input: Union[str, Image.Image]) -> Image.Image | None:
        """Вспомогательный метод для загрузки изображения из разных источников."""
        img = None
        error_message = None
        input_description = "ввода"

        try:
            if isinstance(image_input, Image.Image):
                img = image_input
                input_description = "PIL Image объекта"
            elif isinstance(image_input, str):
                # Попытка декодировать как base64
                try:
                    # Обработка префикса data URI (если есть)
                    if ',' in image_input and image_input.startswith('data:image'):
                        base64_str = image_input.split(',', 1)[1]
                    else:
                        base64_str = image_input # Предполагаем чистый base64

                    decoded_bytes = base64.b64decode(base64_str)
                    img_file = io.BytesIO(decoded_bytes)
                    img = Image.open(img_file)
                    input_description = "base64 строки"
                except (_Base64Error, UnidentifiedImageError, ValueError) as e_b64:
                    # Если не base64, пытаемся открыть как путь к файлу
                    try:
                        img = Image.open(image_input)
                        input_description = f"пути '{image_input}'"
                    except FileNotFoundError:
                        error_message = f"Файл не найден: {image_input}"
                    except UnidentifiedImageError:
                        error_message = f"Не удалось распознать как изображение (проверен base64 и путь): {image_input}"
                    except Exception as e_path:
                        error_message = f"Ошибка открытия файла по пути {image_input}: {e_path}"
                except Exception as e_generic_str:
                     error_message = f"Ошибка обработки строки '{image_input[:50]}...': {e_generic_str}"

            else:
                error_message = f"Неподдерживаемый тип ввода: {type(image_input)}"

            # Конвертация в RGB после успешной загрузки, если необходимо
            if img and img.mode != 'RGB':
                img = img.convert('RGB')

        except Exception as e_load:
            error_message = f"Ошибка при загрузке/конвертации из {input_description}: {e_load}"
            img = None # Убедимся, что img None при любой ошибке

        if error_message:
            print(f"Ошибка загрузки изображения: {error_message}")
            return None

        return img


    def is_nsfw(self, image_input: Union[str, Image.Image]) -> bool | None:
        """
        Проверяет, является ли входное изображение NSFW.

        Args:
            image_input: Путь к файлу (str), PIL Image объект, или base64 строка (str).

        Returns:
            True, если изображение классифицировано как NSFW.
            False, если изображение классифицировано как не NSFW.
            None, если произошла ошибка при обработке, модель не загружена,
                  или входные данные некорректны.
        """
        if not self.classifier:
            print("Классификатор не был инициализирован.")
            return None

        img = self._load_image(image_input)

        if img is None:
            # Сообщение об ошибке уже выведено в _load_image
            return None

        try:
            results = self.classifier(img)
            best_result = max(results, key=lambda x: x["score"])
            return best_result["label"] == "nsfw"
        except Exception as e:
            print(f"Ошибка классификации изображения: {e}")
            return None