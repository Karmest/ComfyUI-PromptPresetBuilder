# Planificador visual por objetivos — MVP experimental

Nueva rama: feature/objective-driven-planner. El flujo manual sigue disponible.

## Dos nodos independientes

- **Objetivos - Prompt Builder** (tipo PromptObjectiveBuilder): elige un objetivo y entrega system_prompt + prompt para el primer Qwen Image 2.1 Prompt Enhancer (i2i). Los objetivos se pueden crear o editar sin reiniciar.
- **Bloques - Prompt Builder** (tipo PromptPresetBuilder): mantiene la biblioteca actual y los presets manuales. Su nueva entrada opcional selection_json resuelve IDs elegidos por el evaluador. Las filas manuales no se modifican.

## Conexiones

1. Objetivos.system_prompt -> EvaluadorPE.system_prompt
2. Objetivos.prompt -> EvaluadorPE.prompt
3. Imagen original -> EvaluadorPE.image_1. Usa loader i2i y preset i2i.
4. EvaluadorPE.positive_prompt -> Bloques.selection_json
5. Objetivos.max_blocks -> Bloques.max_selected_blocks (asegura el límite también si el modelo lo incumple).
6. Objetivos.final_prompt -> GeneradorPE.prompt.
7. Bloques.prompt -> GeneradorPE.extra_instructions (en tu versión local modificada del PE).
8. Imagen original -> GeneradorPE.image_1. Usa loader i2i y preset i2i.
9. GeneradorPE.positive_prompt -> text encoder / cadena de edición Qwen habitual.

Si tu Prompt Enhancer no tiene la entrada extra_instructions, necesitas un nodo de concatenación STRING para unir Objetivos.final_prompt y Bloques.prompt y conectar el texto resultante a GeneradorPE.prompt.

El mismo loader PE i2i puede alimentar ambos Enhancers, pero hay dos inferencias consecutivas.

## Objetivos iniciales

- Mejora automática: corregir defectos visibles.
- Restauración profunda: reparar imágenes muy deterioradas.
- Realismo absoluto: eliminar apariencia sintética.
- Fidelidad máxima: preservar contenido e identidad.
- Mejorar fotos con personas: cuidar rostros, piel, manos y proporciones.

Los objetivos se administran dentro del nodo Objetivos y se guardan en ComfyUI/user/prompt_preset_builder/objectives.json, con copia .bak.

## Contrato de selección

El evaluador recibe el catálogo con ID, categoría, nombre y descripción. No recibe los textos completos de los bloques. Devuelve JSON con selected_block_ids (IDs existentes y sin repetición) y campos opcionales image_type, observations y reason.

El Prompt Enhancer original extrae rewritten_prompt. Si el evaluador devuelve un JSON sin ese campo, positive_prompt conserva el JSON completo aunque parse_ok sea false. En este uso, esa bandera sola no representa un fallo; nuestro Builder valida por separado la estructura y los IDs. También acepta JSON envuelto en rewritten_prompt.

Con selection_json conectado, la selección automática reemplaza las filas manuales solo durante esa ejecución; no borra ni guarda otros presets. Si el JSON es inválido, hay IDs inexistentes o repetidos, o aparecen dos objetos JSON completos, el flujo falla explícitamente. Si hay un JSON inicial válido seguido de texto repetitivo del modelo, recuperamos el primer objeto y registramos un aviso. Se validan TODOS los IDs antes de limitar la selección. Si el evaluador elige más bloques que max_selected_blocks, se conservan los primeros por orden de prioridad y se avisa en el registro. Sin selection_json, el Builder conserva su comportamiento anterior.

Límites iniciales: catálogo de hasta 250 bloques y 36 000 caracteres; selección de 1 a 12 bloques. Recomendado: 4–5.

### Ajuste recomendado del primer Prompt Enhancer (evaluador)

- Loader PE: i2i; preset PE: i2i; thinking: activado.
- Baja max_length de 8192 a **2048** para la primera prueba. El evaluador solo necesita un JSON corto y el valor anterior permitió una repetición de texto de más de 8000 caracteres. Si corta el JSON antes de completarlo, aumenta a 3072.
- Si el muestreo da resultados inestables, prueba temperature 0.3–0.5 (en lugar de 1.0). Mantén seed fijo durante las pruebas comparativas.
- El segundo Prompt Enhancer, que genera instrucciones detalladas, puede conservar su max_length anterior.

La limitación de tokens se configura en el primer PE, no en el Builder de Objetivos. La reparación del parser evita perder respuestas donde el modelo devolvió un JSON completo antes de repetir texto, pero **no detiene** por sí misma la generación sobrante.

## Gate de validación antes de fusionar

1. Abrir presets y workflows v1 sin regresión.
2. «Realismo absoluto» sobre un render, IDs válidos.
3. «Mejora automática» sobre imagen oscura, desenfocada y de baja resolución.
4. «Mejorar fotos con personas» sobre retrato deteriorado.
5. JSON malo e IDs desconocidos deben fallar, no elegir por defecto.
6. Editar un bloque debe cambiar la salida siguiente sin reinicio.
7. Medir latencia y tasa de selección válida en al menos 10 imágenes.

**Estado: DRAFT.** La compatibilidad en ComfyUI y la utilidad del evaluador con imágenes reales todavía deben comprobarse manualmente.
