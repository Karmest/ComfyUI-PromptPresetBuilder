import { api } from "../../scripts/api.js";

const BASE = "/prompt_preset_builder";
let styled = false;

function applyStyles() {
    if (styled) return;
    styled = true;
    const style = document.createElement("style");
    style.textContent = [
        ".ppb-block-back { position:fixed; inset:0; z-index:10010; background:rgba(0,0,0,.65); display:flex; align-items:center; justify-content:center; }",
        ".ppb-block-dialog { box-sizing:border-box; width:min(740px,95vw); max-height:90vh; background:var(--comfy-menu-bg,#272727); color:var(--input-text,#eee); border:1px solid #666; border-radius:9px; padding:15px; display:flex; flex-direction:column; gap:10px; font:13px sans-serif; }",
        ".ppb-block-bar { display:flex; align-items:center; flex-wrap:wrap; gap:8px; }",
        ".ppb-block-dialog input, .ppb-block-dialog select, .ppb-block-dialog textarea { color:inherit; background:var(--comfy-input-bg,#222); border:1px solid #666; padding:6px; border-radius:4px; box-sizing:border-box; }",
        ".ppb-block-dialog button { background:var(--comfy-input-bg,#333); color:inherit; border:1px solid #666; border-radius:4px; padding:6px 9px; cursor:pointer; }",
        ".ppb-block-list { overflow:auto; min-height:100px; max-height:45vh; border:1px solid #555; border-radius:5px; }",
        ".ppb-block-entry { padding:8px; display:flex; align-items:center; gap:10px; border-bottom:1px solid #444; }",
        ".ppb-block-entry > div { flex:1; min-width:0; overflow-wrap:anywhere; }",
        ".ppb-block-entry small { opacity:.7; display:block; margin-top:3px; }",
        ".ppb-block-editor { display:flex; flex-direction:column; gap:7px; padding:9px; border:1px solid #777; border-radius:5px; }",
        ".ppb-block-editor textarea { min-height:145px; width:100%; resize:vertical; }",
        ".ppb-block-error { color:#ff9999; min-height:16px; white-space:pre-wrap; }",
    ].join("\n");
    document.head.appendChild(style);
}

function element(tag, className, label) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (label !== undefined) node.textContent = label;
    return node;
}

async function send(path, payload) {
    const response = await api.fetchApi(BASE + path, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed: " + response.status);
    return data;
}

export async function fetchBlockLibrary() {
    const response = await api.fetchApi(BASE + "/blocks");
    const data = await response.json();
    if (!response.ok || !Array.isArray(data.blocks)) {
        throw new Error(data.error || "Could not load block library");
    }
    return data.blocks;
}

export function openBlockLibrary({ onAdd, onUpdated, draft = null, onDraftSaved = null }) {
    applyStyles();
    const back = element("div", "ppb-block-back");
    const dialog = element("div", "ppb-block-dialog");
    back.appendChild(dialog);
    const titleBar = element("div", "ppb-block-bar");
    const title = element("strong", "", "Reusable Block Library");
    title.style.flex = "1";
    const closeButton = element("button", "", "Close");
    titleBar.append(title, closeButton);
    dialog.appendChild(titleBar);

    const filters = element("div", "ppb-block-bar");
    const category = element("select");
    const search = element("input");
    search.placeholder = "Search blocks...";
    search.style.flex = "1";
    const newButton = element("button", "", "+ New block");
    filters.append(category, search, newButton);
    dialog.appendChild(filters);

    const list = element("div", "ppb-block-list");
    dialog.appendChild(list);
    const status = element("div", "ppb-block-error");
    status.setAttribute("role", "status");
    dialog.appendChild(status);
    const editor = element("div", "ppb-block-editor");
    editor.style.display = "none";
    dialog.appendChild(editor);

    let blocks = [];
    const selected = new Set();
    const footer = element("div", "ppb-block-bar");
    const count = element("span", "", "0 selected");
    count.style.flex = "1";
    const addButton = element("button", "", "Add selected to node");
    footer.append(count, addButton);
    dialog.appendChild(footer);

    function close() { back.remove(); }
    closeButton.addEventListener("click", close);
    back.addEventListener("mousedown", (event) => {
        if (event.target === back) close();
    });

    function notify() { onUpdated?.(); }
    function setError(message) { status.textContent = message || ""; }

    async function reload() {
        try {
            blocks = await fetchBlockLibrary();
            selected.forEach((id) => {
                if (!blocks.some((b) => b.id === id)) selected.delete(id);
            });
            renderFilters();
            renderList();
            setError("");
        } catch (e) {
            setError(e.message);
        }
    }

    function renderFilters() {
        const prev = category.value;
        const categories = ["All", ...new Set(blocks.map((b) => b.category))].sort((a, b) =>
            a === "All" ? -1 : b === "All" ? 1 : a.localeCompare(b));
        category.replaceChildren();
        for (const name of categories) {
            const option = element("option", "", name);
            option.value = name;
            category.appendChild(option);
        }
        category.value = categories.includes(prev) ? prev : "All";
    }

    function renderList() {
        list.replaceChildren();
        const query = search.value.trim().toLocaleLowerCase();
        const shown = blocks.filter((b) => (category.value === "All" || b.category === category.value)
            && [b.category, b.name, b.description || "", b.text].join(" ").toLocaleLowerCase().includes(query));
        for (const block of shown) {
            const item = element("div", "ppb-block-entry");
            const checkbox = element("input");
            checkbox.type = "checkbox";
            checkbox.checked = selected.has(block.id);
            checkbox.setAttribute("aria-label", "Select " + block.name);
            checkbox.addEventListener("change", () => {
                if (checkbox.checked) selected.add(block.id);
                else selected.delete(block.id);
                count.textContent = selected.size + " selected";
            });
            const details = element("div");
            details.appendChild(element("strong", "", block.name));
            details.appendChild(element("small", "", block.category +
                (block.description ? " — " + block.description : "")));
            const edit = element("button", "", "Edit");
            edit.addEventListener("click", () => showEditor(block));
            const remove = element("button", "", "Delete");
            remove.addEventListener("click", async () => {
                if (!window.confirm("Delete '" + block.name + "'? Linked rows will use their saved text snapshot.")) return;
                try {
                    await send("/block/delete", { id: block.id });
                    notify();
                    await reload();
                } catch (e) { setError(e.message); }
            });
            item.append(checkbox, details, edit, remove);
            list.appendChild(item);
        }
        if (!shown.length) list.appendChild(element("div", "ppb-block-entry", "No matching blocks"));
        count.textContent = selected.size + " selected";
    }

    function showEditor(block = null, initial = null) {
        editor.replaceChildren();
        editor.style.display = "flex";
        const heading = element("strong", "", block ? "Edit block" : "New block");
        const c = element("input"); c.placeholder = "Category (e.g. Realism)";
        c.value = block?.category || initial?.category || (category.value !== "All" ? category.value : "");
        const n = element("input"); n.placeholder = "Block name";
        n.value = block?.name || initial?.name || "";
        const d = element("input"); d.placeholder = "Description (optional)";
        d.value = block?.description || "";
        const t = element("textarea"); t.placeholder = "Instruction text";
        t.value = block?.text || initial?.text || "";
        const actions = element("div", "ppb-block-bar");
        const cancel = element("button", "", "Cancel");
        cancel.addEventListener("click", () => { editor.style.display = "none"; });
        const save = element("button", "", "Save block");
        save.addEventListener("click", async () => {
            const body = { category: c.value, name: n.value, description: d.value, text: t.value };
            if (block) body.id = block.id;
            save.disabled = true;
            try {
                const saved = await send(block ? "/block/update" : "/block", body);
                if (!block && initial && saved.block) onDraftSaved?.(saved.block);
                editor.style.display = "none";
                notify();
                await reload();
            } catch (e) { setError(e.message); }
            finally { save.disabled = false; }
        });
        actions.append(cancel, save);
        editor.append(heading, c, n, d, t, actions);
        n.focus();
    }

    newButton.addEventListener("click", () => showEditor());
    category.addEventListener("change", renderList);
    search.addEventListener("input", renderList);
    addButton.addEventListener("click", () => {
        const chosen = blocks.filter((b) => selected.has(b.id));
        for (const b of chosen) onAdd(b);
        selected.clear();
        count.textContent = "0 selected";
        if (chosen.length) close();
    });
    // Stop ComfyUI canvas keyboard/drag events while editing text in the modal.
    for (const event of ["keydown", "keyup", "wheel", "pointerdown"]) {
        dialog.addEventListener(event, (e) => e.stopPropagation());
    }
    document.body.appendChild(back);
    reload();
    if (draft) showEditor(null, draft);
    else search.focus();
}
