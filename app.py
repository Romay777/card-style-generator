import json
import time
import requests
import base64
import os
import datetime
import io # For handling images in memory
from flask import Flask, request, jsonify, send_file
from PIL import Image # Import Pillow
from werkzeug.utils import secure_filename # For safe filenames
from rembg import remove

# --- Configuration --- (Move API Keys outside code in production!)
API_KEY = '8DA5C10BB6C112ABC8A1631455344B59'
SECRET_KEY = '25EA78E09DB215C238DB649EFB737BBE'
API_URL = 'https://api-key.fusionbrain.ai/'
# Card dimensions (Should match Kandinsky's output if possible, or resize later)
# Common card aspect ratio ~1.59. Let's stick to your original generation size.
TARGET_WIDTH = 1032
TARGET_HEIGHT = 648
UPLOAD_FOLDER = 'uploads' # Temporary storage for uploaded logos
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("results", exist_ok=True) # Keep results folder if needed for debugging


# --- FusionBrain API Class (Keep as is, maybe minor logging adjustments) ---
class FusionBrainAPI:
    def __init__(self, url, api_key, secret_key):
        self.URL = url
        self.AUTH_HEADERS = {
            'X-Key': f'Key {api_key}',
            'X-Secret': f'Secret {secret_key}',
        }

    def get_pipeline(self):
        print("Getting pipeline...")
        try:
            response = requests.get(self.URL + 'key/api/v1/pipelines', headers=self.AUTH_HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            if not data:
                raise ValueError("API did not return pipeline list.")
            print(f"Pipeline info: {data[0]}")
            return data[0]['id'] # Assuming first one is Kandinsky 3.1
        except Exception as e:
            print(f"Error getting pipeline: {e}")
            raise

    def generate(self, prompt, pipeline, width, height, style):
        print(f"Starting generation: P='{prompt}', S='{style}', W={width}, H={height}")
        params = {
            "type": "GENERATE",
            "numImages": 1,
            "width": width,
            "height": height,
            "generateParams": {
                "query": f'{prompt}'
            }
        }
        if style and style != "DEFAULT": # Don't send style if it's empty or DEFAULT
             params["style"] = style

        data = {
            'pipeline_id': (None, pipeline),
            'params': (None, json.dumps(params), 'application/json')
        }
        try:
            response = requests.post(self.URL + 'key/api/v1/pipeline/run', headers=self.AUTH_HEADERS, files=data, timeout=60)
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

    def check_generation(self, request_id, attempts=20, delay=10):
        print(f"Checking status for UUID: {request_id}")
        while attempts > 0:
            try:
                response = requests.get(self.URL + 'key/api/v1/pipeline/status/' + request_id, headers=self.AUTH_HEADERS, timeout=30)
                response.raise_for_status()
                data = response.json()
                status = data.get('status', 'UNKNOWN')
                print(f"Attempt {21-attempts}/20: Status = {status}")

                if status == 'DONE':
                    if data.get('censored', False):
                        print("Warning: Generation result is censored.")
                    if data.get('result') and data['result'].get('files'):
                         return data['result']['files'][0] # Return first image base64
                    else:
                         print(f"Status 'DONE' but no image data found. Response: {data}")
                         return None # Indicate failure or no image
                elif status == 'FAIL':
                    error_desc = data.get('errorDescription', 'Unknown generation error')
                    print(f"Generation failed: {error_desc}")
                    return None # Indicate failure
                # No need to print PROCESSING/INITIAL every time if it's working
                # elif status in ('PROCESSING', 'INITIAL'):
                #     print(f"Status: {status}. Waiting...")

            except requests.exceptions.RequestException as e:
                print(f"Network error checking status: {e}. Retrying...")
            except Exception as e:
                 print(f"Error checking status: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
                 # Don't retry on unexpected errors, likely permanent issue
                 return None

            attempts -= 1
            time.sleep(delay)

        print("Generation timed out.")
        return None # Indicate failure


# --- Image Composition Function ---
def overlay_logo(background_data_base64, logo_path, position, card_width, card_height):
    """Overlays logo onto background. Returns final image as BytesIO object."""
    try:
        with open(logo_path, 'rb') as f_in:
            input_bytes = f_in.read()

        output_bytes = remove(input_bytes)

        # Decode background image
        bg_image_data = base64.b64decode(background_data_base64)
        background = Image.open(io.BytesIO(bg_image_data)).convert("RGBA")

        # Ensure background matches target size (API might slightly deviate)
        if background.size != (card_width, card_height):
             print(f"Warning: Generated image size {background.size} differs from target {card_width}x{card_height}. Resizing.")
             background = background.resize((card_width, card_height), Image.Resampling.LANCZOS)


        # Open logo and ensure it has alpha channel
        logo = Image.open(io.BytesIO(output_bytes)).convert("RGBA")

        # --- Calculate logo size (Example: Max 1/4 width, Max 1/4 height) ---
        max_logo_w = card_width // 4
        max_logo_h = card_height // 4
        logo.thumbnail((max_logo_w, max_logo_h), Image.Resampling.LANCZOS)
        logo_w, logo_h = logo.size
        print(f"Resized logo dimensions: {logo_w}x{logo_h}")

        # --- Calculate position coordinates ---
        margin = int(card_width * 0.03) # 3% margin from edge
        x, y = 0, 0

        if position == 'top-left':
            x, y = margin, margin
        elif position == 'top-right':
            x, y = card_width - logo_w - margin, margin
        elif position == 'bottom-left':
            x, y = margin, card_height - logo_h - margin
        elif position == 'bottom-right':
            x, y = card_width - logo_w - margin, card_height - logo_h - margin
        elif position == 'center':
            x, y = (card_width - logo_w) // 2, (card_height - logo_h) // 2
        else: # Default to top-left if position is unknown
             x, y = margin, margin
             print(f"Warning: Unknown logo position '{position}', defaulting to top-left.")

        paste_position = (x, y)
        print(f"Pasting logo at: {paste_position}")

        # Paste logo onto background using logo's alpha channel as mask
        background.paste(logo, paste_position, logo)

        # Save final image to a BytesIO buffer
        final_image_buffer = io.BytesIO()
        background.save(final_image_buffer, format='PNG') # Use PNG to preserve transparency if needed
        final_image_buffer.seek(0) # Rewind buffer to the beginning

        # Optional: Save for debugging
        # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # background.save(os.path.join("results", f"composed_{timestamp}.png"))

        return final_image_buffer

    except FileNotFoundError:
         print(f"Error: Logo file not found at {logo_path}")
         raise
    except Exception as e:
        print(f"Error during image composition: {e}")
        raise


# --- Flask App ---
app = Flask(__name__, static_folder='.', static_url_path='') # Serve static files from current dir

@app.route('/')
def index():
    # Serve the main HTML page
    return app.send_static_file('index.html')

@app.route('/generate-card', methods=['POST'])
def generate_card_endpoint():
    start_time = time.time()
    print("\n--- Received request for card generation ---")

    # 1. Get data from form
    if 'logo' not in request.files:
        return jsonify({"error": "Логотип не был загружен."}), 400

    logo_file = request.files['logo']
    prompt = request.form.get('prompt')
    style = request.form.get('style')
    position = request.form.get('position')

    print(f"Received Data: Prompt='{prompt}', Style='{style}', Position='{position}', Logo='{logo_file.filename}'")

    if not prompt:
        return jsonify({"error": "Необходимо ввести промпт."}), 400
    if not style:
        return jsonify({"error": "Необходимо выбрать стиль."}), 400
    if not position:
        return jsonify({"error": "Необходимо выбрать позицию логотипа."}), 400

    # 2. Save logo temporarily
    if logo_file.filename == '':
         return jsonify({"error": "Не выбран файл логотипа."}), 400

    try:
        filename = secure_filename(f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{logo_file.filename}")
        logo_path = os.path.join(UPLOAD_FOLDER, filename)
        logo_file.save(logo_path)
        print(f"Logo saved temporarily to: {logo_path}")
    except Exception as e:
        print(f"Error saving logo: {e}")
        return jsonify({"error": f"Ошибка сохранения логотипа: {e}"}), 500

    # 3. Generate Background via API
    generated_image_base64 = None
    try:
        api = FusionBrainAPI(API_URL, API_KEY, SECRET_KEY)
        pipeline_id = api.get_pipeline() # Get pipeline ID for each request (in case it changes)
        uuid = api.generate(prompt, pipeline_id, TARGET_WIDTH, TARGET_HEIGHT, style)
        generated_image_base64 = api.check_generation(uuid)

        if not generated_image_base64:
            # api.check_generation already prints errors
            return jsonify({"error": "Не удалось сгенерировать фоновое изображение."}), 500

    except Exception as e:
        print(f"Critical API error: {e}")
        # Clean up saved logo if generation fails early
        if os.path.exists(logo_path):
             os.remove(logo_path)
        return jsonify({"error": f"Ошибка при взаимодействии с API: {e}"}), 500


    # 4. Composite Image
    final_image_buffer = None
    try:
        final_image_buffer = overlay_logo(
            generated_image_base64,
            logo_path,
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
    finally:
        # Clean up the temporary logo file regardless of composition success/failure
        if os.path.exists(logo_path):
            os.remove(logo_path)
            print(f"Temporary logo cleaned up: {logo_path}")

    # 5. Send Result Back
    end_time = time.time()
    print(f"--- Request processed successfully in {end_time - start_time:.2f} seconds ---")

    return send_file(
        final_image_buffer,
        mimetype='image/png', # Send as PNG
        as_attachment=False # Display inline
    )

if __name__ == '__main__':
    print("Starting Flask server...")
    # Use host='0.0.0.0' to make it accessible on your network (use with caution)
    # Debug=True automatically reloads on code changes, but disable for production
    app.run(debug=True, port=5000)