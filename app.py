import json
import time
import requests
import base64
import os
import datetime
import io # For handling images in memory
from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageOps, ImageEnhance # Added ImageOps, ImageEnhance for potential future retouching
from werkzeug.utils import secure_filename # For safe filenames
from rembg import remove
from giga import GigaChatClient, GigaChatAPIError

# --- Configuration ---
API_KEY = '8DA5C10BB6C112ABC8A1631455344B59' # Consider using environment variables
SECRET_KEY = '25EA78E09DB215C238DB649EFB737BBE' # Consider using environment variables
API_URL = 'https://api-key.fusionbrain.ai/'
TARGET_WIDTH = 1032
TARGET_HEIGHT = 648
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Optional: Keep results folder for saving final images if needed
# os.makedirs("results", exist_ok=True)

GIGA_CLIENT_ID = '62d5f574-b143-410a-b6f4-9880b8b8b5ef' # Или используйте os.environ.get
GIGA_CLIENT_SECRET = 'ad8a0333-0ea8-44ff-9d2c-fc1323b82db5' # Или используйте os.environ.get
GIGA_SCOPE = os.environ.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGA_VERIFY_SSL = False # Поставьте False, если есть проблемы с SSL

# Инициализируем клиент один раз при старте приложения
try:
    giga_client = GigaChatClient(GIGA_CLIENT_ID, GIGA_CLIENT_SECRET, scope=GIGA_SCOPE, verify_ssl=GIGA_VERIFY_SSL)
    print("GigaChatClient успешно инициализирован для Flask.")
except ValueError as e:
    print(f"Ошибка инициализации GigaChatClient: {e}")
    giga_client = None # Устанавливаем в None, чтобы обработать это в роуте

# Системная инструкция для улучшения промпта (взята из giga.py)
SYSTEM_PROMPT_IMPROVER = """Роль: AI-улучшатель промптов для генерации изображений (Stable Diffusion, Midjourney).
Задача: Превращать краткие/неясные запросы в детализированные, эффективные промпты.
Действия:
Детализируй: Субъект, действие, фон.
Добавь: Стиль (фото, арт, 3D, рендер, специфичный), освещение, атмосферу.
Уточни: Композицию (кадр: крупный, средний, общий).
Включи: Ключевые слова качества (высокая детализация, 8k, фотореалистично).
Выход: Улучшенный, структурированный промпт.
Примеры Улучшений (для контекста, не включать в сам промпт):
Плохой: кошка
Улучшенный: Фотореалистичный рыжий кот породы мейн-кун, спящий, свернувшись калачиком, в мягком кресле у окна, утренний солнечный свет, уютная атмосфера, детализированный мех, снимок крупным планом
Плохой: пейзаж
Улучшенный: Эпический фантастический пейзаж, плавучие острова, соединенные светящимися мостами, закат с двумя лунами, водопады, низвергающиеся в облака внизу, стиль цифровой живописи, высокая детализация, яркие цвета, волшебная атмосфера."""


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
            "generateParams": { "query": f'{prompt}' }
        }
        if style and style != "DEFAULT": params["style"] = style
        data = {'pipeline_id': (None, pipeline), 'params': (None, json.dumps(params), 'application/json')}
        try:
            response = requests.post(self.URL + 'key/api/v1/pipeline/run', headers=self.AUTH_HEADERS, files=data, timeout=60)
            response.raise_for_status()
            data = response.json()
            print(f"Generation request response: {data}")
            if 'uuid' in data: return data['uuid']
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
                response = requests.get(self.URL + 'key/api/v1/pipeline/status/' + request_id, headers=self.AUTH_HEADERS, timeout=30)
                response.raise_for_status()
                data = response.json()
                status = data.get('status', 'UNKNOWN')
                print(f"Attempt {21-attempts}/20: Status = {status}")
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
            except requests.exceptions.RequestException as e: print(f"Network error checking status: {e}. Retrying...")
            except Exception as e: print(f"Error checking status: {e}. Response: {response.text if 'response' in locals() else 'N/A'}"); return None
            attempts -= 1; time.sleep(delay)
        print("Generation timed out."); return None


# --- Image Composition Function (Minor refactoring for clarity) ---
def overlay_logo(background_base64, logo_bytes, position, card_width, card_height):
    """Overlays logo (already processed by rembg) onto background (as base64)."""
    try:
        # Decode background
        bg_image_data = base64.b64decode(background_base64)
        background = Image.open(io.BytesIO(bg_image_data)).convert("RGBA")

        # Optional: Apply basic background retouching here if desired
        # background = ImageOps.autocontrast(background.convert("RGB"), cutoff=0.5).convert("RGBA")
        # enhancer_sharp = ImageEnhance.Sharpness(background); background = enhancer_sharp.enhance(1.1)

        # Ensure background matches target size
        if background.size != (card_width, card_height):
             print(f"Warning: Background size {background.size} differs from target {card_width}x{card_height}. Resizing.")
             background = background.resize((card_width, card_height), Image.Resampling.LANCZOS)

        # Open logo from bytes (already processed by rembg)
        logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")

        # Calculate logo size
        max_logo_w = card_width // 4
        max_logo_h = card_height // 4
        logo.thumbnail((max_logo_w, max_logo_h), Image.Resampling.LANCZOS)
        logo_w, logo_h = logo.size
        print(f"Resized logo dimensions: {logo_w}x{logo_h}")

        # Calculate position
        margin = int(card_width * 0.03)
        x, y = 0, 0
        if position == 'top-left': x, y = margin, margin
        elif position == 'top-right': x, y = card_width - logo_w - margin, margin
        elif position == 'bottom-left': x, y = margin, card_height - logo_h - margin
        elif position == 'bottom-right': x, y = card_width - logo_w - margin, card_height - logo_h - margin
        elif position == 'center': x, y = (card_width - logo_w) // 2, (card_height - logo_h) // 2
        else: x, y = margin, margin; print(f"Warning: Unknown logo position '{position}', defaulting to top-left.")
        paste_position = (x, y)
        print(f"Pasting logo at: {paste_position}")

        # Paste logo
        background.paste(logo, paste_position, logo)

        # Save final image to buffer
        final_image_buffer = io.BytesIO()
        background.save(final_image_buffer, format='PNG')
        final_image_buffer.seek(0)

        # Optional: Save final result for debugging
        # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # background.save(os.path.join("results", f"final_{timestamp}.png"))

        return final_image_buffer

    except Exception as e:
        print(f"Error during image composition: {e}")
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
        response = giga_client.chat(messages, model="GigaChat") # Используем GigaChat-Pro или другую подходящую модель

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
    position = request.form.get('position')
    mode = request.form.get('mode') # 'generate' or 'upload'

    print(f"Received Data: Mode='{mode}', Position='{position}', Logo='{logo_file.filename}'")

    if not mode or mode not in ['generate', 'upload']:
        return jsonify({"error": "Некорректный режим работы."}), 400
    if not position:
        return jsonify({"error": "Необходимо выбрать позицию логотипа."}), 400
    if logo_file.filename == '':
         return jsonify({"error": "Не выбран файл логотипа."}), 400

    # --- Process Logo (Save & Remove Background) ---
    logo_path = None # Initialize logo_path
    processed_logo_bytes = None
    try:
        filename = secure_filename(f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{logo_file.filename}")
        logo_path = os.path.join(UPLOAD_FOLDER, filename)
        logo_file.save(logo_path)
        print(f"Logo saved temporarily to: {logo_path}")

        with open(logo_path, 'rb') as f_in:
             input_bytes = f_in.read()
        processed_logo_bytes = remove(input_bytes) # Remove background
        print("Logo background removed.")

    except Exception as e:
        print(f"Error processing logo: {e}")
        if logo_path and os.path.exists(logo_path): # Clean up if save succeeded but rembg failed
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
            if not prompt or not style:
                 return jsonify({"error": "Необходимо ввести промпт и выбрать стиль для генерации."}), 400

            api = FusionBrainAPI(API_URL, API_KEY, SECRET_KEY)
            pipeline_id = api.get_pipeline()
            uuid = api.generate(prompt, pipeline_id, TARGET_WIDTH, TARGET_HEIGHT, style)
            background_base64 = api.check_generation(uuid)
            if not background_base64:
                 # api.check_generation should have printed the error
                 return jsonify({"error": "Не удалось сгенерировать фоновое изображение."}), 500
            print("Background generated successfully.")

        elif mode == 'upload':
            if 'backgroundFile' not in request.files:
                 return jsonify({"error": "Файл фона не был загружен."}), 400
            bg_file = request.files['backgroundFile']
            if bg_file.filename == '':
                 return jsonify({"error": "Не выбран файл фона."}), 400

            print(f"Upload Mode: Background File='{bg_file.filename}'")
            # Read file and encode to base64
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
            processed_logo_bytes, # Pass bytes after rembg
            position,
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