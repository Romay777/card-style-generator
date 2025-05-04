import requests
import json
import time

class FusionBrainAPI:
    """
    Клиент для взаимодействия с API FusionBrain.ai (Kandinsky).
    Отвечает за получение pipeline, запуск генерации изображений
    и проверку статуса генерации.
    """
    def __init__(self, url, api_key, secret_key):
        if not all([url, api_key, secret_key]):
            raise ValueError("URL, API Key, and Secret Key cannot be empty for FusionBrainAPI.")
        self.URL = url.rstrip('/') + '/' # Ensure trailing slash for consistency
        self.AUTH_HEADERS = {
            'X-Key': f'Key {api_key}',
            'X-Secret': f'Secret {secret_key}',
        }
        print(f"FusionBrainAPI initialized for URL: {self.URL}")

    def get_pipeline(self):
        """Получает ID первого доступного pipeline."""
        print("Getting FusionBrain pipeline ID...")
        endpoint = 'key/api/v1/pipelines'
        try:
            response = requests.get(self.URL + endpoint, headers=self.AUTH_HEADERS, timeout=30)
            response.raise_for_status() # Проверяет HTTP ошибки (4xx, 5xx)
            data = response.json()
            if not data or not isinstance(data, list) or 'id' not in data[0]:
                raise ValueError("API did not return a valid pipeline list.")
            pipeline_id = data[0]['id']
            print(f"Pipeline ID received: {pipeline_id}")
            return pipeline_id
        except requests.exceptions.RequestException as e:
            print(f"Network error getting pipeline: {e}")
            raise ConnectionError(f"Failed to connect to FusionBrain API at {self.URL + endpoint}: {e}") from e
        except (ValueError, KeyError, IndexError) as e:
            print(f"Error parsing pipeline response: {e}")
            raise ValueError(f"Invalid response format from FusionBrain API when getting pipeline: {e}") from e
        except Exception as e:
            print(f"Unexpected error getting pipeline: {e}")
            raise

    def generate(self, prompt: str, pipeline: str, width: int, height: int, style: str):
        """Запускает генерацию изображения."""
        print(f"Starting generation: P='{prompt[:50]}...', S='{style}', W={width}, H={height}, Pipeline='{pipeline}'")
        endpoint = 'key/api/v1/pipeline/run'
        params = {
            "type": "GENERATE",
            "numImages": 1,
            "width": width,
            "height": height,
            "generateParams": {
                "query": f'{prompt}'
            }
        }
        if style and style.upper() != "DEFAULT":
            params["style"] = style.upper()

        # Используем files для отправки JSON как multipart/form-data, как требует API
        data_payload = {
            'pipeline_id': (None, pipeline),
            'params': (None, json.dumps(params), 'application/json')
        }

        try:
            response = requests.post(self.URL + endpoint, headers=self.AUTH_HEADERS, files=data_payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            print(f"Generation request response: {data}")
            if 'uuid' in data:
                return data['uuid']
            else:
                error_msg = data.get('errorDescription', data.get('message', str(data)))
                raise ValueError(f"API error starting generation: {error_msg}")
        except requests.exceptions.RequestException as e:
            print(f"Network error starting generation: {e}")
            raise ConnectionError(f"Failed to connect to FusionBrain API at {self.URL + endpoint}: {e}") from e
        except (ValueError, KeyError) as e:
             print(f"Error parsing generation start response: {e}")
             raise ValueError(f"Invalid response format from FusionBrain API when starting generation: {e}") from e
        except Exception as e:
            print(f"Unexpected error starting generation: {e}")
            raise

    def check_generation(self, request_id: str, attempts: int = 20, delay: int = 5) -> str | None:
        """
        Проверяет статус генерации по UUID.
        Возвращает base64 строку изображения при успехе, None при ошибке или таймауте.
        """
        print(f"Checking status for UUID: {request_id} (attempts={attempts}, delay={delay}s)")
        endpoint = f'key/api/v1/pipeline/status/{request_id}'
        for attempt in range(attempts):
            try:
                response = requests.get(self.URL + endpoint, headers=self.AUTH_HEADERS, timeout=30)
                response.raise_for_status()
                data = response.json()
                status = data.get('status', 'UNKNOWN')
                print(f"Attempt {attempt + 1}/{attempts}: Status = {status}")

                if status == 'DONE':
                    if data.get('censored', False):
                        print("Warning: Generation result is censored.")
                        # Можно либо вернуть None, либо специальное значение, либо кинуть исключение
                        # return None
                        raise ValueError("Generated image was censored by the API.")

                    if data.get('result') and isinstance(data['result'].get('files'), list) and data['result']['files']:
                        print("Generation DONE. Image received.")
                        return data['result']['files'][0] # Возвращаем base64 первого изображения
                    else:
                        print(f"Status 'DONE' but no image data found. Response: {data}")
                        raise ValueError("Generation status is DONE, but no image data was returned.")

                elif status == 'FAIL':
                    error_desc = data.get('errorDescription', 'Unknown generation error')
                    print(f"Generation failed: {error_desc}")
                    raise RuntimeError(f"FusionBrain generation failed: {error_desc}")

                elif status in ['PROCESSING', 'INITIAL']:
                     print("Generation still processing...") # Просто ждем следующей попытки
                     pass
                else:
                    print(f"Unknown status received: {status}. Response: {data}")
                    # Можно подождать или считать ошибкой
                    # raise ValueError(f"Unknown generation status received: {status}")


            except requests.exceptions.RequestException as e:
                print(f"Network error checking status (Attempt {attempt + 1}): {e}. Retrying...")
                # Не прерываем цикл при временных сетевых ошибках
            except (ValueError, KeyError, RuntimeError) as e:
                 print(f"Error checking status (Attempt {attempt + 1}): {e}")
                 return None # Прерываем цикл при ошибках парсинга, цензуре или статусе FAIL
            except Exception as e:
                print(f"Unexpected error checking status (Attempt {attempt + 1}): {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
                return None # Прерываем при других неожиданных ошибках

            time.sleep(delay)

        print(f"Generation timed out after {attempts} attempts for UUID: {request_id}")
        return None