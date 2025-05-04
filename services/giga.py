import base64
import os
import time
import uuid

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

AUTH_URL = os.environ.get('GIGA_AUTH_URL')
API_BASE_URL = os.environ.get('GIGA_API_BASE_URL')

# --- Custom Exception ---
class GigaChatAPIError(Exception):
    """Custom exception for GigaChat API errors."""
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"GigaChat API Error {status_code}: {message}")

# --- API Client Class ---
class GigaChatClient:
    """
    A client for interacting with the Sber GigaChat API.
    Handles authentication (OAuth 2.0) and provides methods
    for various API endpoints.
    """
    def __init__(self, client_id: str, client_secret: str, scope: str = "GIGACHAT_API_PERS", verify_ssl: bool = True):
        if not client_id or not client_secret:
            raise ValueError("Client ID and Client Secret cannot be empty.")
        if scope not in ["GIGACHAT_API_PERS", "GIGACHAT_API_B2B", "GIGACHAT_API_CORP"]:
             raise ValueError(f"Invalid scope '{scope}'. Must be one of GIGACHAT_API_PERS, GIGACHAT_API_B2B, GIGACHAT_API_CORP.")

        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.verify_ssl = verify_ssl

        self._access_token = None
        self._token_expires_at = 0
        self._session = requests.Session()
        self._session.verify = self.verify_ssl

        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        print(f"GigaChatClient инициализирован")

    def _get_auth_credentials_base64(self) -> str:
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return encoded_credentials

    def _authenticate(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {self._get_auth_credentials_base64()}"
        }
        payload = {"scope": self.scope}

        try:
            response = self._session.post(AUTH_URL, headers=headers, data=payload, timeout=20)
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            expires_at_raw = token_data.get("expires_at")
            if expires_at_raw is None:
                raise GigaChatAPIError(response.status_code, "Missing 'expires_at' in token response")
            if expires_at_raw > 4102444800000: # approx 2100-01-01 in ms
                 self._token_expires_at = expires_at_raw / 1000
            else:
                 self._token_expires_at = expires_at_raw
            if not self._access_token:
                 raise GigaChatAPIError(response.status_code, "Missing 'access_token' in token response")
            print("Успешно получен новый токен доступа.")
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_message = f"{e} - Response: {error_detail}"
                except requests.exceptions.JSONDecodeError:
                    error_message = f"{e} - Response: {e.response.text}"
            raise GigaChatAPIError(e.response.status_code if e.response is not None else 500,
                                   f"Ошибка аутентификации: {error_message}") from e
        except (KeyError, TypeError) as e:
            raise GigaChatAPIError(500, f"Не удалось разобрать ответ токена: {e}") from e

    def _get_valid_token(self) -> str:
        if self._access_token and time.time() < (self._token_expires_at - 60):
            return self._access_token
        else:
            print("Токен доступа истек или не найден. Аутентификация...")
            self._authenticate()
            return self._access_token

    def _make_request(self, method: str, endpoint: str, **kwargs):
        token = self._get_valid_token()
        url = f"{API_BASE_URL}{endpoint}"
        default_headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        if 'headers' in kwargs:
            default_headers.update(kwargs['headers'])
        kwargs['headers'] = default_headers
        if method.upper() in ["POST", "PUT", "PATCH"] and 'json' in kwargs and 'Content-Type' not in kwargs['headers']:
             kwargs['headers']['Content-Type'] = 'application/json'
        elif method.upper() == "POST" and 'files' in kwargs and 'Content-Type' in kwargs['headers']:
             del kwargs['headers']['Content-Type']

        try:
            response = self._session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else 500
            message = str(e)
            details = ""
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    details = error_data.get('message', e.response.text)
                except requests.exceptions.JSONDecodeError:
                    details = e.response.text
                message = f"Ошибка API запроса: {e} | Детали: {details}"
            raise GigaChatAPIError(status_code, message) from e

    def chat(self, messages: list, model: str = "GigaChat", **kwargs):
        """
        Отправляет сообщения модели чата и получает ответ.
        Соответствует POST /chat/completions.

        Args:
            messages (list): Список объектов сообщений.
            model (str): ID модели для использования (например, "GigaChat", "GigaChat-Pro").
            **kwargs: Дополнительные параметры для эндпоинта чата.

        Returns:
            dict: Полный JSON ответ в виде словаря.
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": False, # Убеждаемся, что стриминг выключен
            **kwargs
        }
        response = self._make_request("POST", "/chat/completions", json=payload)
        return response.json()