"""Explicit JSON recording contract; no expected teaching answers here."""
import re

PRACTICE = ["не выдана", "выдана", "нужны исправления", "критерии выполнены", "не проверено"]


def text():
    return {"type": "string", "minLength": 1, "pattern": r"\S"}


def obj(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def record_schema(version, identity, suite):
    fields = {
        "benchmark_version": {"const": version}, "case_id": {"const": identity},
        "input_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "prompt": text(), "response": text(), "execution": text(),
        "session": obj({"id": text(), "name": text(), "date": text(),
                        "kind": {"enum": ["human", "model", "self_review"]},
                        "fresh_context": {"type": "boolean"},
                        "history_messages": {"type": "integer", "minimum": 0}}),
    }
    if suite == "resume":
        fields["recovered"] = obj({
            "part": text(), "practice": {"enum": PRACTICE},
            "practice_note": text(),
            "issues": {"type": "object", "propertyNames": text(),
                       "additionalProperties": {"enum": ["open", "closed", "withdrawn"]}},
            "next_step": text(),
        })
        fields["snapshot"] = obj({"PROGRESS.md": text(), "NOTES.md": text()})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **obj(fields)}


def validate(value, schema, path="record"):
    """Validate the small JSON Schema subset emitted above, without dependencies."""
    types = {"object": dict, "string": str, "boolean": bool, "integer": int}
    kind = schema.get("type")
    if kind and type(value) is not types[kind]:
        raise ValueError(f"{path}: expected {kind}")
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path}: wrong constant")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: value outside declared enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or (
                "pattern" in schema and not re.search(schema["pattern"], value)):
            raise ValueError(f"{path}: invalid string")
    if type(value) is int and value < schema.get("minimum", value):
        raise ValueError(f"{path}: below minimum")
    if isinstance(value, dict):
        if set(schema.get("required", [])) - set(value):
            raise ValueError(f"{path}: missing required fields")
        properties = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if "propertyNames" in schema:
                validate(key, schema["propertyNames"], path + ".<key>")
            if key in properties:
                validate(item, properties[key], path + "." + key)
            elif extra is False:
                raise ValueError(f"{path}: unexpected field {key}")
            elif isinstance(extra, dict):
                validate(item, extra, path + "." + key)
