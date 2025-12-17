from enum import IntEnum
import yaml, json
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Union
from simpleeval import SimpleEval, NameNotDefined, InvalidExpression
import logging
import config
from utils.telegram import TelegramNotify
from utils.ntfy import NtfyNotify
from utils.apprise import AppriseNotify

TZ = ZoneInfo(config.TZ)

class NotifyChannel(IntEnum):
    NONE = 0
    EMAIL = 1
    TELEGRAM = 2
    NTFY = 3
    APPRISE = 4

class AlertDSL:
    def __init__(self, db_h, alert, schedule, maintenance):
        self.context = None
        self.db = db_h
        self.VARIABLES = {
            "alert": alert,
            "schedule": schedule,
            "maintenances": maintenance,
            "NotifyChannel": NotifyChannel
        }
        self.BUILTIN_FUNCTIONS = {
            "log_info": lambda *args: log_info(*args),
            "notify": lambda *args, **kwargs: notify(*args, **kwargs, __context__=self.context, __db__=self.db),
            "send_message": send_message,
            "mute_time": lambda: check_mute_time(__context__=self.context),
            "maintenance": lambda: check_maintenance(__context__=self.context),
        }

    def run_dsl(self, script: str):
        try:
            dsl = yaml.safe_load(script)
        except yaml.YAMLError as e:
            logging.error(f"YAML parsing error: {e}")
            return None

        self.context = self.VARIABLES.copy()

        if "vars" in dsl:
            for key, value in dsl["vars"].items():
                if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                    self.context[key] = self.evaluate_expression(value)
                else:
                    self.context[key] = value

        if "templates" in dsl:
            self.context['templates'] = {}
            for key, value in dsl["templates"].items():
                if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                    self.context['templates'][key] = self.evaluate_expression(value)
                elif isinstance(value, int):
                    res = self.db.getTemplate(value)
                    if res is not None:
                        tpl = res[3]
                    else:
                        logging.error(f"Error loading template ID {value}")
                        tpl = ''
                    self.context['templates'][key] = tpl
                else:
                    self.context['templates'][key] = value

        if "steps" in dsl:
            for step in dsl["steps"]:
                self.execute_step(step)

        return self.context

    def evaluate_expression(self, expr: str) -> Any:
        if not isinstance(expr, str):
            return expr

        expr = expr.strip()
        if expr.strip().startswith("{{") and expr.strip().endswith("}}"):
            code = expr.strip()[2:-2].strip()
        else:
            code = expr

        evaluator = SimpleEval()
        evaluator.names = {
            **self.VARIABLES,
            **self.context
        }
        evaluator.functions = {
            **self.BUILTIN_FUNCTIONS,
        }

        try:
            return evaluator.eval(code)
        except NameNotDefined as e:
            logging.error(f"Variable not defined: {e}")
        except InvalidExpression as e:
            logging.error(f"Invalid expression: {code}")
        except Exception as e:
            logging.error(f"Code exception '{code}': {e}")

    def execute_step(self, step: Dict):
        if "print" in step:
            value = self.evaluate_expression(step["print"])
            logging.info(value)

        elif "set" in step:
            for key, value_expr in step["set"].items():
                value = self.evaluate_expression(value_expr)
                self.context[key] = value

        elif "if" in step:
            cond = self.evaluate_expression(step["if"]["condition"])
            branch = "then" if cond else "else"
            for substep in step["if"].get(branch, []):
                self.execute_step(substep)

        elif "while" in step:
            while self.evaluate_expression(step["while"]["condition"]):
                for substep in step["while"]["steps"]:
                    self.execute_step(substep)

        elif "for" in step:
            var_name = step["for"]["var"]
            iterable_expr = step["for"]["in"]
            substeps = step["for"].get("steps", [])

            iterable = self.evaluate_expression(iterable_expr)

            if not hasattr(iterable, '__iter__'):
                logging.error(f"Not iterable expression: '{iterable_expr}'")
                return None

            for value in iterable:
                self.context[var_name] = value
                for substep in substeps:
                    self.execute_step(substep)

        elif "call" in step:
            call_expr = step["call"]
            result = self.evaluate_expression(call_expr)
            if result is not None:
                logging.info(f"[CALL] result: {result}")
        else:
            logging.error(f"Unknown step: {step}")

class FilterParser:
    def __init__(self, data):
        self.data = data

    def parse_and_evaluate(self, expression: str) -> bool:
        expression = expression.strip()
        or_parts = self._split_by_operator(expression, '||')
        if len(or_parts) > 1:
            results = []
            for part in or_parts:
                results.append(self._evaluate_and_expression(part.strip()))
            return any(results)
        return self._evaluate_and_expression(expression)

    def _split_by_operator(self, expression: str, operator: str) -> list:
        parts = []
        current = ""
        i = 0
        while i < len(expression):
            if expression[i] == '(':
                paren_count = 1
                j = i + 1
                while j < len(expression) and paren_count > 0:
                    if expression[j] == '(':
                        paren_count += 1
                    elif expression[j] == ')':
                        paren_count -= 1
                    j += 1
                current += expression[i:j]
                i = j
            elif i <= len(expression) - len(operator) and expression[i:i+len(operator)] == operator:
                parts.append(current.strip())
                current = ""
                i += len(operator)
            else:
                current += expression[i]
                i += 1
        parts.append(current.strip())
        return parts

    def _evaluate_and_expression(self, expression: str) -> bool:
        and_parts = self._split_by_operator(expression, '&')
        if len(and_parts) > 1:
            results = []
            for part in and_parts:
                results.append(self._evaluate_condition(part.strip()))
            return all(results)

        return self._evaluate_condition(expression)

    def _get_nested_value(self, key_path: str) -> Any:
        keys = key_path.split('.')
        current = self.data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise KeyError(f"Key path '{key_path}' not found in alert data")
        return current

    def _evaluate_condition(self, condition: str) -> bool:
        if condition.startswith('(') and condition.endswith(')'):
            paren_count = 0
            is_properly_enclosed = True
            for i, char in enumerate(condition[:-1]):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0 and i != len(condition) - 2:
                        is_properly_enclosed = False
                        break
            if is_properly_enclosed:
                return self.parse_and_evaluate(condition[1:-1])

        operators = ['==', '!=', '>=', '<=', '>', '<']
        for op in operators:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()

                    if (right.startswith('"') and right.endswith('"')) or \
                       (right.startswith("'") and right.endswith("'")):
                        right = right[1:-1]

                    return self._compare_values(left, op, right)
        raise ValueError(f"Invalid condition: {condition}")

    def _compare_values(self, left: str, operator: str, right: str) -> bool:
        try:
            left_value = self._get_nested_value(left)
        except KeyError as e:
            raise ValueError(f"Field '{left}' not found in alert data")
        try:
            if right.isdigit() or (right.startswith('-') and right[1:].isdigit()):
                right_value = int(right)
                if isinstance(left_value, str) and left_value.isdigit():
                    left_value = int(left_value)
                elif isinstance(left_value, str) and left_value.replace('.', '').replace('-', '').isdigit():
                    left_value = float(left_value)
            elif right.replace('.', '').replace('-', '').isdigit():
                right_value = float(right)
                if isinstance(left_value, str) and left_value.replace('.', '').replace('-', '').isdigit():
                    left_value = float(left_value)
            else:
                right_value = right
        except:
            right_value = right

        if operator == '==':
            return left_value == right_value
        elif operator == '!=':
            return left_value != right_value
        elif operator == '>':
            return left_value > right_value
        elif operator == '<':
            return left_value < right_value
        elif operator == '>=':
            return left_value >= right_value
        elif operator == '<=':
            return left_value <= right_value
        else:
            raise ValueError(f"Unsupported operator: {operator}")


def check_mute_time(__context__=None):
    schedule = __context__.get('schedule', None)
    if schedule is None:
        logging.warning("mute_time(): No active schedule found")
        return None
    mute_starts_str = schedule.get('mute_starts')
    mute_ends_str = schedule.get('mute_ends')

    if mute_starts_str is None or mute_ends_str is None:
        return False
    if len(mute_starts_str) < 5 or len(mute_ends_str) < 5:
        return False

    try:
        mute_starts = datetime.strptime(mute_starts_str, "%H:%M").time()
        mute_ends = datetime.strptime(mute_ends_str, "%H:%M").time()
        now = datetime.now(TZ)
    except:
        return False

    if mute_starts > mute_ends:
        if now.time() >= mute_starts or now.time() <= mute_ends:
            logging.debug("mute_time(): muted")
            return True
        else:
            logging.debug("mute_time(): not muted")
            return False
    elif now.time() >= mute_starts and now.time() <= mute_ends:
        logging.debug("mute_time(): muted")
        return True
    else:
        logging.debug("mute_time(): not muted")
        return False

def check_maintenance(__context__=None):
    mnts = __context__.get('maintenances', None)
    if mnts is None:
        logging.warning("maintenance(): No maintenances found")
        return False
    schedule = __context__.get('schedule', None)
    if schedule is None:
        logging.warning("maintenance(): No active schedule found. Skip.")
        return False
    alert = __context__.get('alert', None)
    if alert is None:
        logging.error("maintenance(): No alert in context")
        return None
    g_id = schedule.get('group_id', None)

    parser = FilterParser(alert)
    for mnt in mnts:
        try:
            if g_id in mnt['oncall_groups'] or len(mnt['oncall_groups']) == 0:
                if len(mnt['filter']) > 0:
                    res = parser.parse_and_evaluate(mnt['filter'])
                    logging.info(f"maintenance(): {res}")
                    return res
                else:
                    logging.info(f"maintenance(): True")
                    return True
        except Exception as e:
            logging.error(f"maintenance(): Filter parse error: {mnt['filter']} - {str(e)}")
    logging.info("maintenance(): False")
    return False

# send raw message using specified notification channel
def send_message(channel_id: int, uri: Any, msg: str):
    if not isinstance(channel_id, int):
        logging.error("send_message(): channel_id must be an integer")
        return None
    result = []
    if channel_id == NotifyChannel.TELEGRAM:
        if not isinstance(uri, int):
            logging.error("send_message(): telegram ID must be a number")
            return None
        tg = TelegramNotify(bot_token=config.TELEGRAM_BOT_TOKEN)
        res = tg.send_raw_message(str(uri), msg)
        result.append({"channel": channel_id, "ok": res['ok'], "user": uri})
        if not res['ok']:
            logging.error(f"send_message(): Error sending Telegram notification to {uri}")
        else:
            logging.info(f"send_message(): Notification to {uri} was sent successfully by Telegram")
    elif channel_id == NotifyChannel.NTFY:
        ntfy = NtfyNotify(ntfy_token=config.NTFY_ACCESS_TOKEN)
        res = ntfy.send_raw_message(uri, 3, 'AlertHub Notification', msg)
        result.append({"channel": channel_id, "ok": res['ok'], "user": uri})
        if not res['ok']:
            logging.error(f"send_message(): Error sending Ntfy notification to {uri}")
        else:
            logging.info(f"send_message(): Notification to {uri} was sent successfully by Ntfy")
    elif channel_id == NotifyChannel.APPRISE:
        apobj = AppriseNotify()
        res = apobj.send_raw_message(uri, 'AlertHub Notification', msg)
        result.append({"channel": channel_id, "ok": res['ok'], "user": uri})
        if not res['ok']:
            logging.error(f"send_message(): Error sending Apprise notification to {uri}")
        else:
            logging.info(f"send_message(): Notification to {uri} was sent successfully by Apprise")

    return result

def notify(telegram_template=0, ntfy_template=0, apprise_template=0, __context__=None, __db__=None):
    #logging.debug(f"DSL context: {__context__}")
    alert = __context__.get('alert', None)
    if alert is None:
        logging.error("No alert in context")
        return None

    if not isinstance(alert, dict):
        logging.error(f"Expected dict for alert, got {type(alert)}")
        return None

    if 'templates' not in __context__:
        __context__['templates'] = {}

    if telegram_template != 0 and isinstance(telegram_template, int):
        res = __db__.getTemplate(telegram_template)
        if res is not None:
            tpl = res[3]
            __context__['templates']['telegram'] = tpl
        else:
            logging.warning(f"notify(): Error loading telegram_template ID {telegram_template}")

    if ntfy_template != 0 and isinstance(ntfy_template, int):
        res = __db__.getTemplate(ntfy_template)
        if res is not None:
            tpl = res[3]
            __context__['templates']['ntfy'] = tpl
        else:
            logging.warning(f"notify(): Error loading ntfy_template ID {ntfy_template}")

    if apprise_template != 0 and isinstance(apprise_template, int):
        res = __db__.getTemplate(apprise_template)
        if res is not None:
            tpl = res[3]
            __context__['templates']['apprise'] = tpl
        else:
            logging.warning(f"notify(): Error loading apprise_template ID {apprise_template}")

    templates = __context__.get('templates', None)
    if templates is None:
        logging.error("Global notification templates not defined, skip notify..")
        return None

    schedule = __context__.get('schedule', None)
    if schedule is None:
        logging.warning("No active schedule found. Skip notify..")
        return None
    people = schedule.get('people', None)
    if people is None or len(people) <= 0:
        logging.info("Nobody to notify. Skipping..")
        return None
    results = []
    for person in people:
        for notify_channel in person['notifiers']:
            if notify_channel == NotifyChannel.NONE:
                logging.info(f"No notification channels defined for {person['name']}. Skip notify..")
                continue
            if notify_channel == NotifyChannel.TELEGRAM:
                tpl = templates.get('telegram')
                tg = TelegramNotify(bot_token=config.TELEGRAM_BOT_TOKEN)
                chat_id = person['telegram_id']
                if chat_id and len(chat_id) > 6:
                    logging.info(f"Notify user {person['name']} by Telegram. Alert id: {alert['alert_id']}, status: {alert['status']}")
                    alert_tmp = alert.copy()
                    starts_at = alert_tmp.get('startsAt',None)
                    ends_at = alert_tmp.get('endsAt',None)
                    updated_at = alert_tmp.get('updatedAt',None)
                    if starts_at is None or ends_at is None:
                        return None
                    dt_start = datetime.fromtimestamp(starts_at, tz=TZ)
                    dt_end = datetime.fromtimestamp(ends_at, tz=TZ)
                    alert_tmp['startsAt'] = format_with_month(dt_start)
                    alert_tmp['endsAt'] = format_with_month(dt_end)
                    if updated_at is not None:
                        dt_updated = datetime.fromtimestamp(updated_at, tz=TZ)
                        alert_tmp['updatedAt'] = format_with_month(dt_updated)
                    res = tg.send_alert(chat_id, tpl, alert_tmp)
                    results.append({"channel": notify_channel, "ok": res['ok'], "user": person['name']})
                    if not res['ok']:
                        logging.error(f"Error sending Telegram notification to {person['name']}")
                    else:
                        logging.info(f"Notification to {person['name']} was sent successfully by Telegram")
                    #logging.debug("Telegram API response: %s", res)
                else:
                    logging.error(f"No telegram ID (chat_id) for {person['name']} or it's wrong. Skip notify..")
            elif notify_channel == NotifyChannel.NTFY:
                tpl = templates.get('ntfy')
                ntfy = NtfyNotify(ntfy_token=config.NTFY_ACCESS_TOKEN)
                topic = person['ntfy']
                if topic and len(topic) > 3:
                    logging.info(f"Notify user {person['name']} by Ntfy. Alert id: {alert['alert_id']}, status: {alert['status']}")
                    alert_tmp = alert.copy()
                    starts_at = alert_tmp.get('startsAt',None)
                    ends_at = alert_tmp.get('endsAt',None)
                    updated_at = alert_tmp.get('updatedAt',None)
                    if starts_at is None or ends_at is None:
                        return None
                    dt_start = datetime.fromtimestamp(starts_at, tz=TZ)
                    dt_end = datetime.fromtimestamp(ends_at, tz=TZ)
                    alert_tmp['startsAt'] = format_with_month(dt_start)
                    alert_tmp['endsAt'] = format_with_month(dt_end)
                    if updated_at is not None:
                        dt_updated = datetime.fromtimestamp(updated_at, tz=TZ)
                        alert_tmp['updatedAt'] = format_with_month(dt_updated)
                    priority = 3
                    if alert.get('status', None) == 'firing' and alert.get('severity', None) == 'critical':
                        priority = 5
                    title = alert.get('alertname','-')
                    res = ntfy.send_alert(topic, priority, title, tpl, alert_tmp)
                    results.append({"channel": notify_channel, "ok": res['ok'], "user": person['name']})
                    if not res['ok']:
                        logging.error(f"Error sending Ntfy notification to {person['name']}")
                    else:
                        logging.info(f"Notification to {person['name']} was sent successfully by Ntfy")
                    #logging.debug("Ntfy API response: %s", res)
                else:
                    logging.error(f"No ntfy topic for {person['name']} or it's wrong. Skip notify..")
            elif notify_channel == NotifyChannel.APPRISE:
                tpl = templates.get('apprise')
                apobj = AppriseNotify()
                apprise_uri = person['apprise']
                if apprise_uri and len(apprise_uri) > 6:
                    logging.info(f"Notify user {person['name']} by Apprise. Alert id: {alert['alert_id']}, status: {alert['status']}")
                    alert_tmp = alert.copy()
                    starts_at = alert_tmp.get('startsAt',None)
                    ends_at = alert_tmp.get('endsAt',None)
                    updated_at = alert_tmp.get('updatedAt',None)
                    if starts_at is None or ends_at is None:
                        return None
                    dt_start = datetime.fromtimestamp(starts_at, tz=TZ)
                    dt_end = datetime.fromtimestamp(ends_at, tz=TZ)
                    alert_tmp['startsAt'] = format_with_month(dt_start)
                    alert_tmp['endsAt'] = format_with_month(dt_end)
                    if updated_at is not None:
                        dt_updated = datetime.fromtimestamp(updated_at, tz=TZ)
                        alert_tmp['updatedAt'] = format_with_month(dt_updated)
                    title = alert.get('alertname','-')
                    res = apobj.send_alert(apprise_uri, title, tpl, alert_tmp)
                    results.append({"channel": notify_channel, "ok": res['ok'], "user": person['name']})
                    if not res['ok']:
                        logging.error(f"Error sending Apprise notification to {person['name']}")
                    else:
                        logging.info(f"Notification to {person['name']} was sent successfully by Appris")
                else:
                    logging.error(f"No apprise uri for {person['name']} or it's wrong. Skip notify..")

    return results

def format_with_month(dt: datetime) -> str:
    offset = dt.strftime("%z")
    offset = offset[:3] + ":" + offset[3:]
    return dt.strftime("%d %b %Y %H:%M:%S") + f" ({offset})"

def format_with_numbers(dt: datetime) -> str:
    offset = dt.strftime("%z")
    offset = offset[:3] + ":" + offset[3:]
    return dt.strftime("%Y-%m-%d %H:%M:%S") + f" ({offset})"

def log_info(args):
    logging.info(args)
