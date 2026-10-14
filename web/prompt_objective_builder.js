import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const TYPE = "PromptObjectiveBuilder";
let cssReady = false;

function isolate(node) {
    for (const event of ["keydown", "keyup", "keypress", "wheel", "pointerdown"]) {
        node.addEventListener(event, (e) => e.stopPropagation());
    }
    return node;
}
function make(tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined && text !== null) el.textContent = text;
    if (className) el.className = className;
    return isolate(el);
}
function css() {
    if (cssReady) return;
    cssReady = true;
    const st = document.createElement("style");
    st.textContent = [
        ".po-root { display:flex;flex-direction:column;gap:6px;padding:6px;box-sizing:border-box;color:var(--input-text,#ddd);font:12px sans-serif; }",
        ".po-root select,.po-dialog input,.po-dialog textarea { width:100%;box-sizing:border-box;background:var(--comfy-input-bg,#222);color:var(--input-text,#ddd);border:1px solid #555;border-radius:5px;padding:5px; }",
        ".po-bar { display:flex;gap:5px;align-items:center; }",
        ".po-bar > select { flex:1;min-width:0; }",
        ".po-root button,.po-dialog button { cursor:pointer;color:inherit;background:var(--comfy-input-bg,#222);border:1px solid #555;border-radius:5px;padding:5px 8px; }",
        ".po-desc { color:var(--descrip-text,#aaa);min-height:26px;font-size:12px;line-height:1.4; }",
        ".po-back { position:fixed;inset:0;background:#000a;z-index:11000;display:flex;justify-content:center;align-items:center; }",
        ".po-dialog { box-sizing:border-box;display:flex;flex-direction:column;gap:10px;background:var(--comfy-menu-bg,#292929);color:var(--input-text,#eee);padding:16px;border:1px solid #777;border-radius:10px;width:min(650px,94vw);max-height:90vh;overflow:auto;font:13px sans-serif; }",
        ".po-dialog textarea { min-height:135px;resize:vertical; }",
        ".po-status { color:#ef9999;min-height:15px; }",
    ].join("\n");
    document.head.appendChild(st);
}
async function getObjectives() {
    const response = await api.fetchApi("/prompt_preset_builder/objectives");
    const data = await response.json();
    if (!response.ok || !Array.isArray(data.objectives)) throw Error(data.error || "Cannot load objectives");
    return data.objectives;
}
async function post(path, data) {
    const response = await api.fetchApi("/prompt_preset_builder/" + path, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data),
    });
    const body = await response.json();
    if (!response.ok) throw Error(body.error || "Operation failed");
    return body;
}
function setup(node) {
    css();
    const widget = node.widgets?.find((w) => w.name === "objective_id");
    if (!widget) return;
    widget.hidden = true;
    widget.type = "hidden";
    widget.computeSize = () => [0, -4];
    const root = make("div", undefined, "po-root");
    const row = make("div", undefined, "po-bar");
    const select = make("select");
    const manage = make("button", "Editar objetivos");
    const refresh = make("button", "↻");
    refresh.title = "Actualizar lista";
    const description = make("div", "", "po-desc");
    const status = make("div", "", "po-status");
    row.append(select, manage, refresh);
    root.append(row, description, status);
    let objectives = [];

    function paint() {
        const obj = objectives.find((o) => o.id === widget.value);
        description.textContent = obj?.description || "Objetivo no encontrado. Selecciona otro o restaura el objetivo.";
        node.setDirtyCanvas?.(true, true);
    }
    async function reload(pick) {
        try {
            objectives = await getObjectives();
            select.replaceChildren();
            for (const obj of objectives) {
                const opt = make("option", obj.name);
                opt.value = obj.id;
                select.appendChild(opt);
            }
            if (pick) widget.value = pick;
            if (!objectives.some((o) => o.id === widget.value)) {
                const missing = make("option", "(Objetivo no disponible: " + widget.value + ")");
                missing.value = widget.value;
                select.appendChild(missing);
            }
            select.value = widget.value;
            paint();
            status.textContent = "";
        } catch (error) {
            status.textContent = error.message;
        }
    }
    node.poReload = reload;
    select.addEventListener("change", () => {
        widget.value = select.value;
        paint();
    });
    refresh.addEventListener("click", () => reload());

    function showEditor() {
        const backdrop = make("div", undefined, "po-back");
        const dialog = make("div", undefined, "po-dialog");
        const bar = make("div", undefined, "po-bar");
        const heading = make("strong", "Biblioteca de objetivos");
        heading.style.flex = "1";
        const close = make("button", "Cerrar");
        close.addEventListener("click", () => backdrop.remove());
        bar.append(heading, close);
        const current = make("select");
        const newOpt = make("option", "+ Nuevo objetivo");
        newOpt.value = "__new__";
        current.appendChild(newOpt);
        for (const obj of objectives) {
            const opt = make("option", obj.name);
            opt.value = obj.id;
            current.appendChild(opt);
        }
        current.value = objectives.some((o) => o.id === widget.value) ? widget.value : "__new__";
        const name = make("input");
        name.placeholder = "Nombre en español";
        const desc = make("input");
        desc.placeholder = "Descripción breve en español";
        const instruction = make("textarea");
        instruction.placeholder = "Reglas del objetivo (en inglés)";
        const feedback = make("div", "", "po-status");
        const action = make("div", undefined, "po-bar");
        const save = make("button", "Guardar objetivo");
        const del = make("button", "Eliminar objetivo");
        function fill() {
            const obj = objectives.find((o) => o.id === current.value);
            name.value = obj?.name || "";
            desc.value = obj?.description || "";
            instruction.value = obj?.instruction || "";
            del.disabled = !obj?.id?.startsWith("goal.custom.");
        }
        current.addEventListener("change", fill);
        fill();
        save.addEventListener("click", async () => {
            save.disabled = true;
            try {
                const data = {name:name.value,description:desc.value,instruction:instruction.value};
                const creating = current.value === "__new__";
                if (!creating) data.id = current.value;
                const result = await post(creating ? "objective" : "objective/update", data);
                backdrop.remove();
                await reload(result.objective.id);
                for (const n of app.graph?.nodes ?? []) if (n !== node) n.poReload?.();
            } catch (e) { feedback.textContent = e.message; }
            finally { save.disabled = false; }
        });
        del.addEventListener("click", async () => {
            if (!window.confirm("¿Eliminar este objetivo personalizado?")) return;
            try {
                await post("objective/delete", {id:current.value});
                backdrop.remove();
                if (widget.value === current.value) widget.value = "goal.auto";
                await reload();
                for (const n of app.graph?.nodes ?? []) if (n !== node) n.poReload?.();
            } catch (e) { feedback.textContent = e.message; }
        });
        action.append(save, del);
        dialog.append(bar, current, name, desc, instruction, action, feedback);
        backdrop.appendChild(dialog);
        backdrop.addEventListener("mousedown", (e) => { if (e.target === backdrop) backdrop.remove(); });
        document.body.appendChild(backdrop);
        name.focus();
    }
    manage.addEventListener("click", showEditor);

    const dom = node.addDOMWidget("po_ui", "po", root, {serialize:false,hideOnZoom:false,getMinHeight:()=>91});
    const baseLayout = node.getLayoutWidgets;
    node.getLayoutWidgets = function () {
        const widgets = baseLayout ? baseLayout.call(this) : (this.widgets ?? []).filter((x) => !x.hidden);
        const idx = widgets.indexOf(dom);
        if (idx > 0) { widgets.splice(idx, 1); widgets.unshift(dom); }
        return widgets;
    };
    reload();
    node.size = [430, Math.max(235, node.computeSize()[1])];
}

app.registerExtension({
    name:"PromptPresetBuilder.Objectives",
    async beforeRegisterNodeDef(nodeType,nodeData) {
        if (nodeData.name !== TYPE) return;
        const onCreate = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const out = onCreate?.apply(this, arguments);
            setup(this);
            return out;
        };
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const out = onConfigure?.apply(this, arguments);
            this.poReload?.();
            return out;
        };
    },
});
