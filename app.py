import json
import time
import requests
import base64
import os
import datetime
import io  # For handling images in memory
from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageOps, ImageEnhance  # Added ImageOps, ImageEnhance for potential future retouching
from werkzeug.utils import secure_filename  # For safe filenames
from rembg import remove
from giga import GigaChatClient, GigaChatAPIError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration from .env ---
API_URL = os.environ.get('FUSION_API_URL', 'https://api-key.fusionbrain.ai/')
API_KEY = os.environ.get('FUSION_API_KEY')
SECRET_KEY = os.environ.get('FUSION_SECRET_KEY')
TARGET_WIDTH = int(os.environ.get('TARGET_WIDTH', 1032))
TARGET_HEIGHT = int(os.environ.get('TARGET_HEIGHT', 648))
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
PLACEHOLDERS_FOLDER = 'placeholders'  # Добавляем папку для шаблонов
CARD_TEMPLATE_PATH = os.path.join(os.environ.get('CARD_TEMPLATE_PATH', 'placeholders'), 'card-vanished.png')

GIGA_CLIENT_ID = os.environ.get('GIGA_CLIENT_ID')
GIGA_CLIENT_SECRET = os.environ.get('GIGA_CLIENT_SECRET')
GIGA_SCOPE = os.environ.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGA_VERIFY_SSL = os.environ.get("GIGA_VERIFY_SSL", "False").lower() != "false"

# System prompt for improving prompts
SYSTEM_PROMPT_IMPROVER = os.environ.get('PROMPT_SYSTEM', """Роль: AI-улучшатель промптов для генерации изображений...""")

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Инициализируем клиент один раз при старте приложения
try:
    giga_client = GigaChatClient(GIGA_CLIENT_ID, GIGA_CLIENT_SECRET, scope=GIGA_SCOPE, verify_ssl=GIGA_VERIFY_SSL)
    print("GigaChatClient успешно инициализирован для Flask.")
except ValueError as e:
    print(f"Ошибка инициализации GigaChatClient: {e}")
    giga_client = None  # Устанавливаем в None, чтобы обработать это в роуте

# Системная инструкция для улучшения промпта (взята из giga.py)
SYSTEM_PROMPT_IMPROVER = """Роль: AI-улучшатель промптов для генерации изображений (Stable Diffusion, Midjourney).
Задача: Превращать краткие/неясные запросы в детализированные, эффективные промпты.
Действия:
Детализируй: Субъект, действие, фон.
Добавь: Стиль (фото, арт, 3D, рендер, специфичный), освещение, атмосферу.
Уточни: Композицию (кадр: крупный, средний, общий).
Включи: Ключевые слова качества (высокая детализация, 8k, фотореалистично).
Выход: Улучшенный, структурированный промпт, который должен быть написан в одну строчку через запятые, как в примерах!!! Не пиши ничего, кроме самого промпта.
Примеры Улучшений (для контекста, не включать в сам промпт):
Плохой: кошка
Улучшенный: Фотореалистичный рыжий кот породы мейн-кун, спящий, свернувшись калачиком, в мягком кресле у окна, утренний солнечный свет, уютная атмосфера, детализированный мех, снимок крупным планом
Плохой: пейзаж
Улучшенный: Эпический фантастический пейзаж, плавучие острова, соединенные светящимися мостами, закат с двумя лунами, водопады, низвергающиеся в облака внизу, стиль цифровой живописи, высокая детализация, яркие цвета, волшебная атмосфера."""

# --- Pre-load Card Template ---
CARD_TEMPLATE_IMAGE = None
try:
    if not os.path.exists(CARD_TEMPLATE_PATH):
        print(f"!!! ОШИБКА: Файл шаблона карты не найден по пути: {CARD_TEMPLATE_PATH}")
        # Можно либо прервать выполнение, либо продолжить без шаблона,
        # но лучше сообщить об ошибке. Для простоты пока оставляем None.
    else:
        print(f"Загрузка шаблона карты из: {CARD_TEMPLATE_PATH}")
        template_img = Image.open(CARD_TEMPLATE_PATH).convert("RGBA")
        # Сразу изменим размер шаблона под целевой размер карты для эффективности
        if template_img.size != (TARGET_WIDTH, TARGET_HEIGHT):
            print(f"Изменение размера шаблона карты с {template_img.size} до {TARGET_WIDTH}x{TARGET_HEIGHT}")
            CARD_TEMPLATE_IMAGE = template_img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
        else:
            CARD_TEMPLATE_IMAGE = template_img
        print("Шаблон карты успешно загружен и подготовлен.")

except Exception as e:
    print(f"!!! КРИТИЧЕСКАЯ ОШИБКА при загрузке/обработке шаблона карты: {e}")


# --- FusionBrain API Class (No changes needed) ---
class FusionBrainAPI:
    def __init__(self, url, api_key, secret_key):
        self.URL = url
        self.AUTH_HEADERS = {
            'X-Key': f'Key {api_key}',
            'X-Secret': f'Secret {secret_key}',
        }

    def get_pipeline(self):
        # ... (keep existing code) ...
        print("Getting pipeline...")
        try:
            response = requests.get(self.URL + 'key/api/v1/pipelines', headers=self.AUTH_HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            if not data:
                raise ValueError("API did not return pipeline list.")
            print(f"Pipeline info: {data[0]}")
            return data[0]['id']
        except Exception as e:
            print(f"Error getting pipeline: {e}")
            raise

    def generate(self, prompt, pipeline, width, height, style):
        # ... (keep existing code) ...
        print(f"Starting generation: P='{prompt}', S='{style}', W={width}, H={height}")
        params = {
            "type": "GENERATE", "numImages": 1, "width": width, "height": height,
            "generateParams": {"query": f'{prompt}'}
        }
        if style and style != "DEFAULT": params["style"] = style
        data = {'pipeline_id': (None, pipeline), 'params': (None, json.dumps(params), 'application/json')}
        try:
            response = requests.post(self.URL + 'key/api/v1/pipeline/run', headers=self.AUTH_HEADERS, files=data,
                                     timeout=60)
            response.raise_for_status()
            data = response.json()
            print(f"Generation request response: {data}")
            if 'uuid' in data:
                return data['uuid']
            else:
                error_msg = data.get('errorDescription', data.get('message', str(data)))
                raise ValueError(f"API error starting generation: {error_msg}")
        except Exception as e:
            print(f"Error starting generation: {e}")
            raise

    def check_generation(self, request_id, attempts=20, delay=5):
        # ... (keep existing code) ...
        print(f"Checking status for UUID: {request_id}")
        while attempts > 0:
            try:
                response = requests.get(self.URL + 'key/api/v1/pipeline/status/' + request_id,
                                        headers=self.AUTH_HEADERS, timeout=30)
                response.raise_for_status()
                data = response.json()
                status = data.get('status', 'UNKNOWN')
                print(f"Attempt {21 - attempts}/20: Status = {status}")
                if status == 'DONE':
                    if data.get('censored', False): print("Warning: Generation result is censored.")
                    if data.get('result') and data['result'].get('files'):
                        return data['result']['files'][0]
                    else:
                        print(f"Status 'DONE' but no image data found. Response: {data}")
                        return None
                elif status == 'FAIL':
                    error_desc = data.get('errorDescription', 'Unknown generation error')
                    print(f"Generation failed: {error_desc}")
                    return None
            except requests.exceptions.RequestException as e:
                print(f"Network error checking status: {e}. Retrying...")
            except Exception as e:
                print(
                    f"Error checking status: {e}. Response: {response.text if 'response' in locals() else 'N/A'}"); return None
            attempts -= 1;
            time.sleep(delay)
        print("Generation timed out.");
        return None


# --- Image Composition Function (Minor refactoring for clarity) ---
def overlay_logo(background_base64, logo_bytes, logo_x_rel, logo_y_rel, logo_scale, card_width, card_height):
    """Overlays logo (already processed by rembg) onto background (as base64)."""
    try:
        # Decode background
        bg_image_data = base64.b64decode(background_base64)
        background = Image.open(io.BytesIO(bg_image_data)).convert("RGBA")

        # Optional: Apply basic background retouching here if desired
        background = ImageOps.autocontrast(background.convert("RGB"), cutoff=0.5).convert("RGBA")
        # enhancer_sharp = ImageEnhance.Sharpness(background); background = enhancer_sharp.enhance(1.1)

        # Ensure background matches target size
        if background.size != (card_width, card_height):
            print(
                f"Warning: Background size {background.size} differs from target {card_width}x{card_height}. Resizing.")
            background = background.resize((card_width, card_height), Image.Resampling.LANCZOS)

        # Open logo from bytes (already processed by rembg)
        logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")

        base_max_logo_w = card_width * 0.25
        aspect_ratio = logo.height / logo.width
        target_logo_w = int(base_max_logo_w * logo_scale)
        target_logo_h = int(target_logo_w * aspect_ratio)

        target_logo_w = max(target_logo_w, 5)
        target_logo_h = max(target_logo_h, 5)

        print(f"Resizing logo to: {target_logo_w}x{target_logo_h} (Scale: {logo_scale:.2f})")
        logo = logo.resize((target_logo_w, target_logo_h), Image.Resampling.LANCZOS)
        logo_w, logo_h = logo.size  # Get actual size after resize

        # Calculate top-left position from relative CENTER coordinates
        # (logo_x_rel, logo_y_rel are percentages 0.0-1.0 of the center point)
        center_x_px = logo_x_rel * card_width
        center_y_px = logo_y_rel * card_height

        # Calculate top-left corner coordinates for pasting
        paste_x = int(center_x_px - (logo_w / 2))
        paste_y = int(center_y_px - (logo_h / 2))

        # --- Boundary Check (Optional but Recommended) ---
        paste_x = max(0, min(paste_x, card_width - logo_w))
        paste_y = max(0, min(paste_y, card_height - logo_h))
        # --- End Boundary Check ---

        paste_position = (paste_x, paste_y)
        print(f"Calculated paste position (top-left): {paste_position}")

        # Paste logo
        # The third argument 'logo' acts as the mask for transparency
        background.paste(logo, paste_position, logo)
        print("Логотип наложен на фон.")  # Добавим лог

        if CARD_TEMPLATE_IMAGE:
            print("Наложение шаблона элементов карты...")
            # Шаблон уже должен быть нужного размера и RGBA
            # Накладываем его поверх всего (включая логотип)
            # Третий аргумент CARD_TEMPLATE_IMAGE используется как маска для прозрачности
            background.paste(CARD_TEMPLATE_IMAGE, (0, 0), CARD_TEMPLATE_IMAGE)
            print("Шаблон элементов карты успешно наложен.")
        else:
            # Если шаблон не загрузился, выводим предупреждение, но продолжаем
            print("!!! ПРЕДУПРЕЖДЕНИЕ: Шаблон карты не загружен, результат будет без элементов карты.")
            # Можно здесь выбросить исключение, если шаблон обязателен:
            # raise ValueError("Не удалось загрузить обязательный шаблон карты.")

        # Save final image to buffer
        final_image_buffer = io.BytesIO()
        background.save(final_image_buffer, format='PNG')
        final_image_buffer.seek(0)

        return final_image_buffer

    except Exception as e:
        print(f"Error during image composition: {e}")
        # It's often helpful to re-raise the exception after logging
        # to ensure the calling function knows something went wrong.
        raise


# --- Flask App ---
app = Flask(__name__, static_folder='.', static_url_path='')


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/improve-prompt', methods=['POST'])
def improve_prompt_endpoint():
    if not giga_client:
        return jsonify({"error": "Сервис улучшения промптов временно недоступен (ошибка конфигурации)."}), 503

    try:
        data = request.get_json()
        user_prompt = data.get('prompt')

        if not user_prompt:
            return jsonify({"error": "Промпт не может быть пустым."}), 400

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_IMPROVER},
            {"role": "user", "content": user_prompt}
        ]

        print(f"Отправка промпта '{user_prompt}' в GigaChat для улучшения...")
        response = giga_client.chat(messages, model="GigaChat")  # Используем GigaChat-Pro или другую подходящую модель

        if response and "choices" in response and response["choices"]:
            improved_prompt = response["choices"][0].get("message", {}).get("content")
            if improved_prompt:
                print(f"GigaChat вернул улучшенный промпт: {improved_prompt}")
                return jsonify({"improved_prompt": improved_prompt.strip()})
            else:
                print("GigaChat API вернул ответ без контента.")
                return jsonify({"error": "Не удалось получить улучшенный промпт от GigaChat."}), 500
        else:
            print(f"Неожиданный ответ от GigaChat API: {response}")
            return jsonify({"error": "Неожиданный ответ от сервиса улучшения промптов."}), 500

    except GigaChatAPIError as e:
        print(f"Ошибка GigaChat API при улучшении промпта: {e}")
        return jsonify({"error": f"Ошибка сервиса улучшения промптов: {e.message}"}), e.status_code
    except requests.exceptions.RequestException as e:
        print(f"Сетевая ошибка при обращении к GigaChat: {e}")
        return jsonify({"error": "Сетевая ошибка при обращении к сервису улучшения промптов."}), 504
    except Exception as e:
        print(f"Непредвиденная ошибка при улучшении промпта: {e}")
        return jsonify({"error": "Внутренняя ошибка сервера при улучшении промпта."}), 500


@app.route('/generate-card', methods=['POST'])
def generate_card_endpoint():
    start_time = time.time()
    print("\n--- Received request for card generation ---")

    # --- Common Data ---
    if 'logo' not in request.files:
        return jsonify({"error": "Логотип не был загружен."}), 400
    logo_file = request.files['logo']

    try:
        logo_x_rel = request.form.get('logoX', default=0.5, type=float)  # Expecting 0.0-1.0
        logo_y_rel = request.form.get('logoY', default=0.5, type=float)  # Expecting 0.0-1.0
        logo_scale = request.form.get('logoScale', default=0.5, type=float)  # Expecting e.g. 0.2-1.0
        print(f"Received Position/Scale: X={logo_x_rel:.3f}, Y={logo_y_rel:.3f}, Scale={logo_scale:.3f}")
    except ValueError:
        return jsonify({"error": "Некорректные значения для позиции или размера логотипа."}), 400

    mode = request.form.get('mode')  # 'generate' or 'upload'

    print(f"Received Data: Mode='{mode}', Logo='{logo_file.filename}'")

    if not mode or mode not in ['generate', 'upload']:
        return jsonify({"error": "Некорректный режим работы."}), 400
    if logo_file.filename == '':
        return jsonify({"error": "Не выбран файл логотипа."}), 400

    # --- Process Logo (Save & Remove Background) ---
    logo_path = None  # Initialize logo_path
    processed_logo_bytes = None
    try:
        filename = secure_filename(f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{logo_file.filename}")
        logo_path = os.path.join(UPLOAD_FOLDER, filename)
        logo_file.save(logo_path)
        print(f"Logo saved temporarily to: {logo_path}")

        with open(logo_path, 'rb') as f_in:
            input_bytes = f_in.read()
        processed_logo_bytes = remove(input_bytes)  # Remove background
        print("Logo background removed.")

    except Exception as e:
        print(f"Error processing logo: {e}")
        if logo_path and os.path.exists(logo_path):  # Clean up if save succeeded but rembg failed
            os.remove(logo_path)
        return jsonify({"error": f"Ошибка обработки логотипа: {e}"}), 500
    finally:
        # Clean up original saved logo file *after* rembg processing
        if logo_path and os.path.exists(logo_path):
            os.remove(logo_path)
            print(f"Temporary original logo cleaned up: {logo_path}")

    # --- Get Background (Generate or Upload) ---
    background_base64 = None
    try:
        if mode == 'generate':
            prompt = request.form.get('prompt')
            style = request.form.get('style')
            print(f"Generate Mode: Prompt='{prompt}', Style='{style}'")
            if not prompt:  # Style can be DEFAULT
                return jsonify({"error": "Необходимо ввести промпт для генерации."}), 400

            api = FusionBrainAPI(API_URL, API_KEY, SECRET_KEY)
            pipeline_id = api.get_pipeline()
            uuid = api.generate(prompt, pipeline_id, TARGET_WIDTH, TARGET_HEIGHT, style)
            background_base64 = api.check_generation(uuid)
            if not background_base64:
                # api.check_generation should have printed the error
                return jsonify({"error": "Не удалось сгенерировать фоновое изображение."}), 500
            print("Background generated successfully.")


        elif mode == 'upload':
            if 'background' not in request.files:
                return jsonify({"error": "Файл фона не был загружен (ожидался ключ 'background')."}), 400

            bg_file = request.files['background']  # Use 'background' key
            if bg_file.filename == '':
                return jsonify({"error": "Не выбран файл фона."}), 400

            print(f"Upload Mode: Background File='{bg_file.filename}'")
            bg_file_bytes = bg_file.read()
            background_base64 = base64.b64encode(bg_file_bytes).decode('utf-8')
            print("Background uploaded and encoded successfully.")

    except Exception as e:
        print(f"Error getting background (mode: {mode}): {e}")
        return jsonify({"error": f"Ошибка получения фона: {e}"}), 500

    # --- Composite Image ---
    final_image_buffer = None
    try:
        if not background_base64 or not processed_logo_bytes:
            raise ValueError("Missing background or processed logo data for composition.")

        final_image_buffer = overlay_logo(
            background_base64,
            processed_logo_bytes,
            logo_x_rel,  # Pass relative X (0.0-1.0)
            logo_y_rel,  # Pass relative Y (0.0-1.0)
            logo_scale,  # Pass scale (e.g., 0.5)
            TARGET_WIDTH,
            TARGET_HEIGHT
        )
        if not final_image_buffer:
            raise ValueError("Image composition returned None")
        print("Image composition successful.")

    except Exception as e:
        print(f"Error during composition step: {e}")
        return jsonify({"error": f"Ошибка наложения логотипа: {e}"}), 500
    # No finally needed here as temp logo is already cleaned up

    # --- Send Result Back ---
    end_time = time.time()
    print(f"--- Request processed successfully in {end_time - start_time:.2f} seconds ---")
    return send_file(
        final_image_buffer,
        mimetype='image/png',
        as_attachment=False
    )


if __name__ == '__main__':
    print("Starting Flask server...")
    # Ensure ONNXRuntime is installed: pip install onnxruntime
    # Ensure rembg is installed: pip install rembg
    app.run(debug=True, port=5000)
