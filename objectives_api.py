"""CRUD HTTP endpoints for the separate visual objectives library."""
from uuid import uuid4

from aiohttp import web
from server import PromptServer

from .objective_store import load_objectives, save_objectives


def normalize(body):
    if not isinstance(body, dict):
        raise ValueError("Expected JSON object")
    obj = {}
    for field, limit in (("name", 120), ("description", 500), ("instruction", 4000)):
        val = body.get(field, "")
        if not isinstance(val, str) or not val.strip() or len(val) > limit:
            raise ValueError(f"Invalid {field}")
        obj[field] = val.strip()
    return obj


server = getattr(PromptServer, "instance", None)
if server is not None:
    routes = server.routes

    @routes.get("/prompt_preset_builder/objectives")
    async def list_objectives(request):
        try:
            return web.json_response({"objectives": load_objectives()})
        except (ValueError, OSError) as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/prompt_preset_builder/objective")
    async def create_objective(request):
        try:
            new = normalize(await request.json())
            all_objectives = load_objectives()
            if any(x["name"].casefold() == new["name"].casefold() for x in all_objectives):
                return web.json_response({"error": "Objective name already exists"}, status=409)
            new["id"] = "goal.custom." + uuid4().hex
            all_objectives.append(new)
            save_objectives(all_objectives)
            return web.json_response({"objective": new}, status=201)
        except (ValueError, OSError) as e:
            return web.json_response({"error": str(e)}, status=400)

    @routes.post("/prompt_preset_builder/objective/update")
    async def update_objective(request):
        try:
            body = await request.json()
            new = normalize(body)
            selected_id = body.get("id")
            all_objectives = load_objectives()
            selected = next((x for x in all_objectives if x["id"] == selected_id), None)
            if selected is None:
                return web.json_response({"error": "Objective not found"}, status=404)
            if any(x["id"] != selected_id and x["name"].casefold() == new["name"].casefold() for x in all_objectives):
                return web.json_response({"error": "Objective name already exists"}, status=409)
            selected.update(new)
            save_objectives(all_objectives)
            return web.json_response({"objective": selected})
        except (ValueError, OSError) as e:
            return web.json_response({"error": str(e)}, status=400)

    @routes.post("/prompt_preset_builder/objective/delete")
    async def delete_objective(request):
        try:
            body = await request.json()
            selected_id = body.get("id")
            if not isinstance(selected_id, str) or not selected_id.startswith("goal.custom."):
                return web.json_response({"error": "Built-in objectives cannot be deleted"}, status=400)
            current = load_objectives()
            remaining = [x for x in current if x["id"] != selected_id]
            if len(current) == len(remaining):
                return web.json_response({"error": "Objective not found"}, status=404)
            save_objectives(remaining)
            return web.json_response({"ok": True})
        except (ValueError, OSError) as e:
            return web.json_response({"error": str(e)}, status=400)
