"""HTTP CRUD for reusable blocks. One shared library, no node-definition reload."""
from uuid import uuid4

from aiohttp import web
from server import PromptServer

from .block_store import load_blocks, save_blocks


def _fields(data):
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    out = {}
    for key, limit in (("category", 80), ("name", 120), ("text", 20000), ("description", 500)):
        value = data.get(key, "")
        if not isinstance(value, str):
            raise ValueError(key + " must be text")
        value = value.strip()
        if len(value) > limit:
            raise ValueError(key + " is too long")
        out[key] = value
    if not out["category"] or not out["name"] or not out["text"]:
        raise ValueError("Category, name and text are required")
    return out


def _unique(blocks, fields, exclude=None):
    key = (fields["category"].casefold(), fields["name"].casefold())
    return all(b["id"] == exclude or (b["category"].casefold(), b["name"].casefold()) != key for b in blocks)


_server = getattr(PromptServer, "instance", None)
if _server is not None:
    routes = _server.routes

    @routes.get("/prompt_preset_builder/blocks")
    async def _list_blocks(request):
        try:
            return web.json_response({"version": 1, "blocks": load_blocks()})
        except (ValueError, OSError) as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/prompt_preset_builder/block")
    async def _create_block(request):
        try:
            fields = _fields(await request.json())
            blocks = load_blocks()
            if not _unique(blocks, fields):
                return web.json_response({"error": "A block with this name already exists in the category"}, status=409)
            entry = {"id": uuid4().hex, **fields}
            blocks.append(entry)
            save_blocks(blocks)
            return web.json_response({"block": entry}, status=201)
        except (ValueError, OSError) as e:
            return web.json_response({"error": str(e)}, status=400)

    @routes.post("/prompt_preset_builder/block/update")
    async def _update_block(request):
        try:
            body = await request.json()
            block_id = body.get("id") if isinstance(body, dict) else None
            fields = _fields(body)
            blocks = load_blocks()
            entry = next((b for b in blocks if b["id"] == block_id), None)
            if entry is None:
                return web.json_response({"error": "Block not found"}, status=404)
            if not _unique(blocks, fields, exclude=block_id):
                return web.json_response({"error": "A block with this name already exists in the category"}, status=409)
            entry.update(fields)
            save_blocks(blocks)
            return web.json_response({"block": entry})
        except (ValueError, OSError) as e:
            return web.json_response({"error": str(e)}, status=400)

    @routes.post("/prompt_preset_builder/block/delete")
    async def _delete_block(request):
        try:
            body = await request.json()
            block_id = body.get("id") if isinstance(body, dict) else None
            blocks = load_blocks()
            if not any(b["id"] == block_id for b in blocks):
                return web.json_response({"error": "Block not found"}, status=404)
            save_blocks([b for b in blocks if b["id"] != block_id])
            return web.json_response({"ok": True})
        except (ValueError, OSError) as e:
            return web.json_response({"error": str(e)}, status=400)
