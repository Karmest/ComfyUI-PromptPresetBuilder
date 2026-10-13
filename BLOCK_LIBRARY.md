# Reusable Block Library (experimental)

This fork extends **Prompt Preset Builder** with a categorized block library.
It does not add any workflow nodes or change the output STRING socket. Existing
presets and legacy inline rows remain supported.

## Use

1. Restart ComfyUI once after installing this branch.
2. Open **Prompt Preset Builder** and click **Library...**.
3. Create blocks organized by category, search, edit, delete, and select several
   blocks to add them as linked rows. New categories need no restart.
4. Edit a linked block via **Library... -> Edit**, or click **↗** on its row to
   detach it as independently editable text.
5. Existing **Save / Save as** controls store combinations of linked and free-text
   rows. Use `\\n\\n` as separator when combining instructions into paragraphs.
6. Connect the usual STRING output to Qwen Prompt Enhancer's extra_instructions.

## Storage and compatibility

The shared block library lives at:

    <ComfyUI>/user/prompt_preset_builder/blocks.json

This library is shared by users of the same ComfyUI server, unlike the original
per-user preset files. Do not put sensitive instructions there on a multi-user
server.

A linked row stores block_id plus an initial text snapshot. At execution, the
live block text is read and used, and the node cache changes when linked text
changes. If the block disappears or the workflow is moved without its library,
the saved snapshot is used rather than losing the instruction. All existing
workflow rows and preset JSON continue to work without migration.

Each write is atomic and preserves a one-revision backup at blocks.json.bak.
For an exact, reproducible frozen combination, detach the blocks and save the
result as a separate preset, or version the blocks.json library along with
the workflow.

## Testing

The PR includes Python unit tests, Python syntax checks, and JS syntax checks.
The ComfyUI frontend still needs manual testing prior to merging to main.

Run the pure Python tests:

    python -m unittest discover -s tests -p test_block_store.py -v
