import mimetypes
import requests
import logging
from typing import Optional

# Логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_TELEGRAM_API_URL = 'https://api.telegram.org/bot'
DEFAULT_TIMEOUT = 10


def _make_telegram_request(method_url: str, data: dict, files: Optional[dict] = None) -> dict:
    try:
        response = requests.post(method_url, data=data, files=files, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        json_data = response.json()
        if not json_data.get("ok"):
            logger.warning(f"Telegram API error: {json_data}")
        return json_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error to {method_url}: {e}")
        return {
            "ok": False,
            "description": str(e),
            "error_code": getattr(e.response, 'status_code', 'REQUEST_EXCEPTION')
        }
    except Exception as e:
        logger.error(f"Unexpected error to {method_url}: {e}")
        return {
            "ok": False,
            "description": f"Unexpected error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }


def sendMessage(token: str, channel: str, text: str) -> dict:
    if not all([token, channel, text]):
        return {
            "ok": False,
            "description": "Token, channel, or text cannot be empty.",
            "error_code": "MISSING_PARAMETERS"
        }

    method_url = f"{BASE_TELEGRAM_API_URL}{token}/sendMessage"
    data = {
        "chat_id": channel,
        "text": text,
        "parse_mode": "HTML"
    }
    return _make_telegram_request(method_url, data)


def _detect_media_type(media_path: str):
    mime_type, _ = mimetypes.guess_type(media_path)
    if not mime_type:
        return "sendDocument", "document"
    if mime_type.startswith("image") and not mime_type.endswith("gif"):
        return "sendPhoto", "photo"
    if mime_type.startswith("video"):
        return "sendVideo", "video"
    if mime_type.startswith("audio"):
        return "sendAudio", "audio"
    if mime_type.endswith("gif"):
        return "sendAnimation", "animation"
    return "sendDocument", "document"

def sendMediaMessage(
    token: str,
    channel: str,
    media_path: str,
    caption: Optional[str] = None,
    performer: Optional[str] = None,
    title: Optional[str] = None
) -> dict:
    if not all([token, channel, media_path]):
        return {"ok": False, "description": "Token, channel or file path missing."}
    endpoint, field_name = _detect_media_type(media_path)
    if not endpoint:
        return {"ok": False, "description": "Unknown media type."}

    method_url = f"{BASE_TELEGRAM_API_URL}{token}/{endpoint}"
    data = {"chat_id": channel}

    if endpoint == "sendAudio":
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
        if performer:
            data["performer"] = performer
        if title:
            data["title"] = title
    else:
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
    try:
        with open(media_path, "rb") as media:
            return _make_telegram_request(method_url, data, files={field_name: media})
    except Exception as e:
        logger.error(f"Media send error: {e}")
        return {"ok": False, "description": str(e)}
