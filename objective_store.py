"""Editable, persistent objective definitions for the separate Objective Builder."""
import json
import os
import shutil
from pathlib import Path

DEFAULT_OBJECTIVES = [
    {
        "id": "goal.auto",
        "name": "Mejora automática",
        "description": "Detectar y corregir defectos visibles sin cambiar innecesariamente la imagen.",
        "instruction": "Assess the actual image. Improve photographic quality conservatively; select only blocks addressing clearly visible weaknesses. Preserve subjects and composition.",
    },
    {
        "id": "goal.deep",
        "name": "Restauración profunda",
        "description": "Recuperar imágenes muy deterioradas, aunque tengan varios defectos simultáneos.",
        "instruction": "Identify multiple visible degradations and choose targeted restoration blocks. Allow controlled reconstruction where information is irrecoverable; avoid inventing identity or critical details.",
    },
    {
        "id": "goal.realism",
        "name": "Realismo absoluto",
        "description": "Transformar una imagen artificial o un render en una fotografía verosímil.",
        "instruction": "Identify rendering artifacts, unrealistic materials, illumination or textures. Choose blocks that improve photographic realism while preserving geometry, furniture, view and content unless explicitly authorized.",
    },
    {
        "id": "goal.fidelity",
        "name": "Fidelidad máxima",
        "description": "Mejorar claridad y aspecto manteniendo al máximo las personas y elementos originales.",
        "instruction": "Prioritize exact preservation of identities, people, materials, layout, framing, logos, text and other existing details. Choose minimally invasive improvement blocks.",
    },
    {
        "id": "goal.people",
        "name": "Mejorar fotos con personas",
        "description": "Mejorar fotos deterioradas cuidando especialmente rostros, manos e identidad.",
        "instruction": "Analyze photographic problems in a picture with people, choose blocks that restore quality while preserving recognizable facial identity, expression, pose, body proportions, skin, hands and wardrobe.",
    },
]


def objectives_path():
    import folder_paths
    return Path(folder_paths.get_user_directory()) / "prompt_preset_builder" / "objectives.json"


def load_objectives(path=None):
    path = Path(path) if path is not None else objectives_path()
    if not path.exists():
        return [dict(item) for item in DEFAULT_OBJECTIVES]
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("objectives"), list):
        raise ValueError("Invalid objectives.json format")
    seen = set()
    results = []
    for obj in data["objectives"]:
        if not isinstance(obj, dict) or not all(isinstance(obj.get(k), str) and obj[k].strip() for k in ("id", "name", "description", "instruction")):
            raise ValueError("Invalid objective")
        if obj["id"] in seen:
            raise ValueError("Duplicate objective IDs")
        seen.add(obj["id"])
        results.append(obj)
    return results


def save_objectives(values, path=None):
    path = Path(path) if path is not None else objectives_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            json.dump({"version": 1, "objectives": values}, stream, ensure_ascii=False, indent=2)
        if path.exists():
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def objective_by_id(objective_id, objectives):
    return next((x for x in objectives if x["id"] == objective_id), None)
