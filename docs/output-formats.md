# Diseño de formatos de salida

**Estado (20 noviembre 2026):** `tiff-alpha` se ha verificado estructuralmente; `tiff-layer-mask` se ha probado visualmente en Krita con colores CMYK y máscara funcional. `both` combina ambos escritores, pero el formato de lote recomendado es ahora `tiff-alpha`: Krita permite convertir directamente el alfa en máscara de capa mediante «Dividir alfa → Alfa en máscara», evitando duplicados `_editable`. No se garantiza interoperabilidad universal con otros editores.

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

### `tiff-layer-mask` — validado en Krita para la muestra

- Un **único TIFF** que contenga la imagen CMYK original completa y una **máscara de capa editable interna**, activable/desactivable, no solo una muestra alfa de la imagen acoplada.
- El comportamiento requerido es: máscara activada = imagen recortada; máscara desactivada = **todo el escaneo original con papel**, sin recomposición ni reconstrucción.
- El perfil ICC y los cuatro canales CMYK deben conservarse, junto con dimensiones y resolución; no premultiplicar ni descontaminar el color.
- Candidato técnico: etiquetas privadas de capas estilo Photoshop (`ImageSourceData` / 37724, mediante biblioteca como `psdtags`). Es **una propuesta de implementación**, no un formato de máscara de capa interoperable garantizado.
- Antes de declarar este modo compatible, comprobar **guardado y reapertura real** en Krita (y documentar las limitaciones de GIMP). No sustituir silenciosamente la máscara de capa por alfa simple si el programa no reconoce la estructura.
- El TIFF base deberá tener una apariencia compuesta coherente con la máscara, cuando el software respete los datos de capas, pero nunca a costa de eliminar los píxeles CMYK ocultos.

### `both` — opcional, no necesario en el flujo actual

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

## Corrección de polaridad CMYK (19 noviembre 2026)

La primera apertura del TIFF editable en Krita confirmó que la **máscara de capa sí funciona**, pero mostró colores invertidos y fondo negro. Se ha corregido la polaridad de los canales CMYK **solo dentro de la estructura de capa estilo PSD**: se guardan como `255 - canal_CMYK_TIFF`, para que el importador PSD los interprete correctamente. Los cuatro canales del TIFF convencional y el ICC permanecen intactos. La prueba de lectura verifica el retorno a los valores originales al desinvertirlos. **Pendiente de confirmación visual con un TIFF recién generado en Krita**; no sobrescribir automáticamente archivos previos.

## Validación manual en Krita — 20 noviembre 2026

El usuario confirmó que el TIFF editable regenerado tras la corrección de polaridad CMYK **se ve correctamente en Krita**. En la prueba anterior había confirmado explícitamente que la máscara era reconocida y funcionaba, aunque los colores eran incorrectos. Tras la corrección, informa «está bien en krita»; por ello se considera validada la combinación básica de capas, máscara y color para la ilustración probada. No equivale a certificar compatibilidad universal ni a verificar de nuevo por separado cada operación de activación/desactivación de la máscara en otros documentos.

Se mantiene el modo `tiff-alpha` y el modo `tiff-layer-mask` como alternativas. Próxima fase: evaluar calidad de segmentación en varias acuarelas y decidir si optimizar los píxeles ocultos en la salida no editable.

## Cierre de investigación y aplicación al lote (20 noviembre 2026)

La prueba real en Krita de `10_editable.tif` validó la lectura del CMYK original con máscara de capa separada. En el análisis posterior, `legacy` fue visualmente superior a `adaptive`; las variantes `legacy-plus` y `connected-wash` no aportaron una mejora significativa, por lo que no se recomienda su uso en producción. Mantener `acuarela` como método predeterminado (`legacy` queda como alias histórico); preservar los experimentos solamente como historial técnico.

La línea de comandos final se documenta al comienzo de [README.md](../README.md). El resultado recomendado es `--mask-method acuarela --output-format tiff-alpha`, con salida a carpeta nueva. En Krita, abrir el TIFF convencional y usar clic derecho en la capa → «Dividir alfa → Alfa en máscara»; revisar y retocar la máscara, guardar un archivo de trabajo y reexportar el TIFF para maquetación si se modifica. Esta prueba no constituye una validación de Scribus, que no es requisito del proyecto.

Las menciones anteriores a validaciones pendientes documentan hitos históricos; queda cerrada la comprobación inicial de Krita sobre la ilustración de prueba, no la revisión de las restantes ilustraciones.

## Denominación del método definitivo

El método seleccionado tras las comparaciones visuales se denomina **`acuarela`**. Es exactamente el algoritmo antes llamado `legacy`, sin cambios matemáticos ni cromáticos. La CLI acepta `legacy` como alias de compatibilidad, pero los ejemplos y el procedimiento de producción usan `--mask-method acuarela`. Los nombres históricos en resultados de diagnóstico se conservan para trazabilidad.

## Simplificación del flujo final (20 noviembre 2026)

El usuario comprobó que Krita permite convertir el alfa existente de un TIFF convencional en una máscara de capa editable mediante **clic derecho sobre la capa → Dividir alfa → Alfa en máscara**. Ya no hace falta exportar un segundo archivo `_editable.tif`. El método recomendado es `acuarela` y la salida única es `tiff-alpha` (predeterminado); el modo `tiff-layer-mask` queda disponible únicamente como alternativa histórica. Las dependencias extra `requirements-layered.txt` no son necesarias para el procedimiento normal; basta el entorno de `requirements.txt`. Los TIFF originales permanecen intactos mientras se trabaje sobre copias en Krita.
