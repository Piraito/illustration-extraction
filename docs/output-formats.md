# Diseño de formatos de salida

**Estado:** propuesta de interfaz aprobada para desarrollo, **no implementada** salvo el modo actual `tiff-alpha`.

## Objetivo

Extraer ilustraciones sin modificar el color de la imagen compuesta original. El cálculo de la máscara puede realizarse en RGB temporal, pero los canales CMYK del original y sus bytes ICC deben pasar intactos al archivo exportado. Las imágenes completas, incluido el papel, deben seguir siendo recuperables cuando se utilice la salida editable.

## CLI prevista

```bash
python src/extract_illustrations.py INPUT OUTPUT --output-format tiff-alpha
python src/extract_illustrations.py INPUT OUTPUT --output-format tiff-layer-mask
python src/extract_illustrations.py INPUT OUTPUT --output-format both
```

- `--output-format`: `tiff-alpha` (predeterminado), `tiff-layer-mask`, `both`.
- Sin `--output-format`, **comportamiento anterior sin cambios**.
- `--recursivo`, `--magick` y los parámetros de máscara se mantienen comunes.
- Una única lectura, composición y segmentación de la imagen por entrada, reutilizando la máscara para cada salida seleccionada.
- Los modos no implementados deberán rechazarse expresamente si se exponen antes de estar disponibles; no generar un archivo distinto bajo su nombre.

## Nombres y productos

Para `10.psd`:

| Modo | Salida |
| --- | --- |
| `tiff-alpha` | `10.tif` |
| `tiff-layer-mask` | `10_editable.tif` |
| `both` | `10.tif` y `10_editable.tif` |

La exportación auxiliar `10_mascara.png` sigue existiendo **en la implementación actual**, como recurso de diagnóstico; su futura opcionalidad se decidirá aparte. No es parte de la máscara incrustada.

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
