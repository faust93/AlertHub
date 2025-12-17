import yaml,logging
from typing import Any, Dict, List, Union
from simpleeval import SimpleEval, NameNotDefined, InvalidExpression

from voluptuous import (
    Schema,
    Required,
    Optional,
    Any,
    Match,
    MultipleInvalid,
    Invalid
)
from voluptuous import PREVENT_EXTRA, ALLOW_EXTRA, REMOVE_EXTRA

class PipelineValidator:
    def __init__(self):
        self.ValidExpression = Match(r'^\{\{.*\}\}$|^[^{}]*$', msg="Expression must be either inside {{ }}, or not.")
        self.TemplatesStep = {
            Required("templates"): { str: object }
        }
        self.SetStep = {
            Required("set"): { str: object }
        }
        self.CallStep = {
            Required("call"): object
        }
        self.IfStep = {
            Required("if"): {
                Required("condition"): self.ValidExpression,
                Required("then"): self.validate_steps_list,
                Optional("else"): self.validate_steps_list,
            }
        }
        self.WhileStep = {
            Required("while"): {
                Required("condition"): self.ValidExpression,
                Required("steps"): self.validate_steps_list,
            }
        }
        self.ForStep = {
            Required("for"): {
                Required("var"): str,
                Required("in"): str,
                Required("steps"): self.validate_steps_list,
            }
        }
        self.Step = Schema(Any(
            self.SetStep,
            self.ForStep,
            self.IfStep,
            self.WhileStep,
            self.CallStep,
        ), extra=PREVENT_EXTRA)

        self.SCRIPT_SCHEMA = Schema({
            Optional("templates", default={}): { str: object },
            Optional("vars", default={}): { str: object },
            Optional("steps", default=[]): [self.Step],
        }, extra=PREVENT_EXTRA)


    def validate_steps_list(self, value):
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            raise Invalid('Expected a list of steps or a single step dict')
        for idx, item in enumerate(value):
            try:
                self.Step(item)
            except Exception as e:
                raise Invalid(f'Invalid step at index {idx}: {e}')
        return value

    def validate_pipeline(self, pipeline):
        try:
            dsl = yaml.safe_load(pipeline)
        except yaml.YAMLError as e:
            logging.error(f"YAML parsing error: {e}")
            return True, f"YAML parsing error: {e}"
        try:
            return False, self.SCRIPT_SCHEMA(dsl)
        except (MultipleInvalid, Invalid) as e:
            logging.error(f"YAML parsing error: {e}")
            return True, f"YAML validation error: {e.msg}\nError path: {' -> '.join(str(x) for x in e.path)}"
