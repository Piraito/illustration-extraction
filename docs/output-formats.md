# Diseño de formatos de salida

**Estado:** los tres modos ya tienen una implementación en la CLI. `tiff-layer-mask` y `both` son **experimentales** y requieren validación de interoperabilidad real con Krita.

## Objetivo

Extraer ilustraciones sin modificar el color de la imagen compuesta original. El cálculo de la máscara puede realizarse en RGB temporal, pero los canales CMYK del original y sus bytes ICC deben pasar intactos al archivo exportado. Las imágenes completas, incluido el papel, deben seguir siendo recuperables cuando se utilice la salida editable.

## CLI disponible

```bash
python src/extract_illustrations.py INPUT OUTPUT --output-format tiff-alpha
python src/extract_illustrations.py INPUT OUTPUT --output-format tiff-layer-mask
python src/extract_illustrations.py INPUT OUTPUT --output-format both
```

- `--output-format`: `tiff-alpha` (predeterminado), `tiff-layer-mask`, `both`.
- Sin `--output-format`, **comportamiento anterior sin cambios**.
- `--recursivo`, `--magick` y los parámetros de máscara se mantienen comunes.
- `--export-mask`: genera además la máscara PNG auxiliar, desactivada por defecto.
- Una única lectura, composición y segmentación de la imagen por entrada, reutilizando la máscara para cada salida seleccionada.
- El modo editable requiere instalar `requirements-layered.txt` en el entorno virtual. La ausencia de `psdtags` provoca error explícito, no una falsa salida editable.

## Nombres y productos

Para `10.psd`:

| Modo | Salida |
| --- | --- |
| `tiff-alpha` | `10.tif` |
| `tiff-layer-mask` | `10_editable.tif` |
| `both` | `10.tif` y `10_editable.tif` |

La exportación auxiliar `10_mascara.png` es **opcional** mediante `--export-mask` y está desactivada por defecto. Es una copia de diagnóstico, no parte de la máscara incrustada.

Cuando colisionen nombres como `23.psd` y `23.jpg`, conservar la convención `23_psd.*` / `23_jpg.*` antes de añadir el sufijo `_editable`. No sobrescribir archivos existentes, ni dejar un TIFF incompleto en caso de fallo.

## Semántica de cada formato

### `tiff-alpha` — actual

- TIFF de cinco muestras: **C, M, Y, K, alfa no premultiplicado** (`ExtraSamples=UNASSALPHA`).
- RGB se utiliza solo para analizar el contenido.
- Los cuatro canales CMYK y el perfil ICC deben ser idénticos a los de la imagen compuesta importada; conservar dimensiones y resolución.
- No implica máscara de capa editable dentro de un editor. Desactivar la transparencia puede no revelar el contenido oculto en GIMP/Krita.

### `tiff-layer-mask` — experimental

- Un **único TIFF** que contenga la imagen CMYK original completa y una **máscara de capa editable interna**, activable/desactivable, no solo una muestra alfa de la imagen acoplada.
- El comportamiento requerido es: máscara activada = imagen recortada; máscara desactivada = **todo el escaneo original con papel**, sin recomposición ni reconstrucción.
- El perfil ICC y los cuatro canales CMYK deben conservarse, junto con dimensiones y resolución; no premultiplicar ni descontaminar el color.
- Candidato técnico: etiquetas privadas de capas estilo Photoshop (`ImageSourceData` / 37724, mediante biblioteca como `psdtags`). Es **una propuesta de implementación**, no un formato de máscara de capa interoperable garantizado.
- Antes de declarar este modo compatible, comprobar **guardado y reapertura real** en Krita (y documentar las limitaciones de GIMP). No sustituir silenciosamente la máscara de capa por alfa simple si el programa no reconoce la estructura.
- El TIFF base deberá tener una apariencia compuesta coherente con la máscara, cuando el software respete los datos de capas, pero nunca a costa de eliminar los píxeles CMYK ocultos.

### `both` — experimental

- Genera ambos formatos con **la misma máscara calculada**.
- Un fallo de uno de los formatos debe quedar registrado sin afirmar que ambos se generaron satisfactoriamente.

## Aceptación técnica

1. `tiff-alpha`: conserva los resultados ya validados en el proyecto (CMYK e ICC bit a bit, muestra alfa no premultiplicada con niveles intermedios).
2. `tiff-layer-mask`: abrir el TIFF muestra una capa CMYK con máscara editable y permite **desactivar o eliminar la máscara sin perder el fondo papel**.
3. Comparar píxel a píxel los cuatro canales CMYK visibles al desactivar la máscara contra la composición original obtenida al leer el PSD/JPG.
4. Verificar la identidad del ICC, resolución y dimensiones; comportamiento ante PSD con Smart Objects, perfiles distintos y error de formato.
5. Si la biblioteca no soporta escribir de forma fiable los datos de máscara/capas, **fallar explícitamente** y documentar la limitación: no escribir un TIFF que aparente ser editable sin serlo.
6. No requerir Photoshop ni instalar herramientas globales adicionales; bibliotecas Python en el `.venv`, salvo ImageMagick ya existente para PSD.
7. No introducir cambios en el algoritmo de segmentación ni el tratamiento cromático al implementar la interfaz de formatos.

## Fuera de alcance por ahora

- Soporte de imágenes RGB y nuevos espacios de color, pendiente de implementación aparte.
- Alternativa de corrección cromática de bordes: decisión aplazada.
- Desarrollo de plugin GIMP/Krita, también aplazado.
- Pruebas de interoperabilidad con Scribus como condición previa: **no solicitadas**.

## Implementación experimental (noviembre de 2026)

- `src/layered_tiff.py`: almacena el compuesto TIFF CMYK+A y la etiqueta 37724 con una capa CMYK completa y un canal `USER_LAYER_MASK` (-2), separado del alfa habitual.
- `--output-format`: implementado con `tiff-alpha`, `tiff-layer-mask` o `both`; default compatible con el script previo.
- `requirements-layered.txt`: dependencias Python opcionales dentro del venv; no requiere Photoshop.
- `tests/test_layered_tiff.py`: comprobación de escritura y relectura estructural (ejecución pendiente en entorno con psdtags e imagecodecs).
- **Bloqueante para declarar éxito:** abrir `*_editable.tif` en Krita, verificar que aparece una verdadera máscara de capa, desactivarla y recuperar el papel original. La verificación estructural en Python no demuestra compatibilidad de un editor.
