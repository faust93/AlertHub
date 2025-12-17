import logging
import requests
import jinja2
from requests.exceptions import RequestException
import config

class NtfyNotify:
    NTFY_SERVER = config.NTFY_SERVER

    def __init__(self, ntfy_token: str):
        if not ntfy_token:
            raise ValueError("Ntfy access token must be provided")
        self.ntfy_token = ntfy_token
        self.env = jinja2.Environment(
            autoescape=False,
            trim_blocks=False,
            lstrip_blocks=False
        )

    def render_message(self, template: str, context: dict) -> str:
        tpl = self.env.from_string(template)
        return tpl.render(context)

    def send_raw_message(self, topic: str, priority: int, title: str, msg: str):
        payload = {
            "topic": topic,
            "title": title,
            "message": msg,
            "priority": priority
        }

        headers = {
            "Authorization": "Bearer " + self.ntfy_token
        }

        try:
            response = requests.post(self.NTFY_SERVER, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()

            if not result.get("id", False):
                logging.error("Ntfy API error: %s", result)
                return {"ok": False, "response": result}
            else:
                return {"ok": True, "response": result}

        except RequestException as e:
            logging.error("Ntfy send_message failed: %s", e)
            return {"ok": False, "response": str(e)}

    def send_alert(self, topic: str, priority: int, title: str, template: str, alert: dict):
        msg = self.render_message(template, alert)

        payload = {
            "topic": topic,
            "title": title,
            "message": msg,
            "priority": priority,
            "actions": [
                {
                "action": "view",
                "label": "Open Alert",
                "url": config.BASE_URL + "/home/alerts/" + alert['alert_id']
                }
            ]
        }

        headers = {
            "Authorization": "Bearer " + self.ntfy_token
        }

        try:
            response = requests.post(self.NTFY_SERVER, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()

            if not result.get("id", False):
                logging.error("Ntfy API error: %s", result)
                return {"ok": False, "response": result}
            else:
                return {"ok": True, "response": result}

        except RequestException as e:
            logging.error("Ntfy send_message failed: %s", e)
            return {"ok": False, "response": str(e)}
