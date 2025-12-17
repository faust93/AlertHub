import logging
import requests
import jinja2
from requests.exceptions import RequestException
import config
import apprise

class AppriseNotify:
    def __init__(self):
        self.ap_h = apprise.Apprise()
        self.env = jinja2.Environment(
            autoescape=False,
            trim_blocks=False,
            lstrip_blocks=False
        )

    def render_message(self, template: str, context: dict) -> str:
        tpl = self.env.from_string(template)
        return tpl.render(context)

    def send_raw_message(self, uri: str, title: str, msg: str):
        self.ap_h.add(uri)

        try:
            response = self.ap_h.notify(
                body=msg,
                title=title
            )

            if not response:
                logging.error("Apprise error: notification failed")
                return {"ok": False, "response": "failed"}
            else:
                return {"ok": True, "response": "successful"}

        except Exception as e:
            logging.error("Apprise send_message_alert failed: %s", e)
            return {"ok": False, "response": str(e)}

    def send_alert(self, uri: str, title: str, template: str, alert: dict):
        msg = self.render_message(template, alert)
        self.send_raw_message(uri, title, msg)
