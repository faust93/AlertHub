import logging
import requests
import jinja2
from requests.exceptions import RequestException

class TelegramNotify:
    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token: str, parse_mode: str = "Markdown"):
        if not bot_token:
            raise ValueError("Telegram bot token must be provided")
        self.bot_token = bot_token
        self.parse_mode = parse_mode
        self.api_url = f"{self.BASE_URL}/bot{self.bot_token}/sendMessage"

        self.env = jinja2.Environment(
            autoescape=False,
            trim_blocks=False,
            lstrip_blocks=False
        )

    def render_message(self, template: str, context: dict) -> str:
        tpl = self.env.from_string(template)
        return tpl.render(context)

    def send_raw_message(self, chat_id: str, msg: str):
        payload = {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": self.parse_mode
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if not result.get("ok", False):
                logging.error("Telegram API error: %s", result)
                return {"ok": False, "response": result}
            else:
                return {"ok": True, "response": result}
            return result

        except RequestException as e:
            logging.error("Telegram send_message failed: %s", e)
            return {"ok": False, "response": str(e)}

    def send_alert(self, chat_id: str, template: str, alert: dict) -> dict:
        bot_msg = self.render_message(template, alert)
        self.send_raw_message(chat_id, bot_msg)
