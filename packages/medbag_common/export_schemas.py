"""Write a JSON Schema file per shared type into schemas/ (for anyone not reading Python)."""

import json
from pathlib import Path

from pydantic import BaseModel

from medbag_common import types as T

out = Path(__file__).parent / "schemas"
out.mkdir(exist_ok=True)
for name in dir(T):
    obj = getattr(T, name)
    if isinstance(obj, type) and issubclass(obj, BaseModel) and obj not in (BaseModel, T.ImageModel):
        if obj.__module__ == T.__name__:
            schema = obj.model_json_schema(mode="serialization")
            (out / f"{name}.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2))
            print(name)
