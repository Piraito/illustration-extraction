# illustration-extraction

Extracción **experimental** de ilustraciones escaneadas sobre papel claro mediante una máscara alfa gradual. Proyecto pensado para procesamiento por lotes y posterior revisión en GIMP o Krita.

## Estado

Herramienta lista para aplicar **con revisión visual por ilustración** a la colección de tiburones. El método recomendado es `acuarela`, validado visualmente en la acuarela de prueba; no es un extractor genérico validado para cualquier papel o color. Se conservan las dimensiones de los escaneos y no se modifican los originales.

La denominación `legacy` se conserva solo como **alias histórico** en la CLI y en los informes de las pruebas antiguas. `acuarela` ejecuta exactamente el mismo algoritmo, sin modificación de píxeles ni parámetros. 
\n## Procedimiento definitivo para el libro de tiburones (20 noviembre 2026)

**Método recomendado:** `acuarela` (predeterminado). Las variantes `adaptive`, `legacy-plus` y `connected-wash` no han producido una mejora visual útil sobre `10.psd`; se conservan solo para trazabilidad. El TIFF editable CMYK con perfil original y máscara real se ha comprobado en Krita. Las demás acuarelas requieren revisión individual; no se garantiza un recorte perfecto.

**Ejecutar desde** `/SISE/proyectos/Agaden/Tiburones/Ilustraciones Natalia` en Paul:

```bash
cd illustration-extraction
git pull
.venv/bin/python -m pip install -r requirements-layered.txt
.venv/bin/python -m unittest discover -s tests -p 'test_layered_tiff.py' -v
.venv/bin/python src/extract_illustrations.py \
  "../escaneadas-natalia/ESCANEADO IMAGENES LIBRO" \
  "../ilustraciones-extraidas-acuarela" \
  --solo-psd --mask-method acuarela --output-format both
```

- `--solo-psd` evita procesar el JPG RGB `23.jpg`; `23.psd` sí se procesa. **No mueve ni borra el JPG**.
- `--output-format both` genera por cada `NN.psd` los archivos `NN.tif` (CMYK + alfa, para maquetación) y `NN_editable.tif` (mismo CMYK y máscara de capa editable para corrección en Krita).
- La salida se crea en `ilustraciones-extraidas-acuarela`, carpeta **nueva** distinta de `ilustraciones-extraidas` y de todas las pruebas anteriores.
- No se sobrescriben TIFF existentes. Los archivos ya generados se omiten; si necesitas reprocesar, usa una nueva carpeta de salida. Los problemas se registran en `errores_procesamiento.txt` y el proceso devuelve código de error si hay fallos.
- Si algún PSD concreto falla, revisar el registro y el TIFF de ese archivo; no dar por correcto todo el lote solo por haber generado algunos archivos.
- Comprobar `*_editable.tif` en Krita: responder **Sí** cuando ofrezca leer los datos PSD incrustados, revisar tonos y bordes, corregir manualmente la máscara si es necesario. **Las correcciones manuales en Krita no actualizan automáticamente el TIFF convencional `NN.tif`**: hay que exportar después la versión corregida destinada a maquetación, preservando CMYK y perfil ICC.
- En Scribus utilizar los TIFF definitivos tras revisión, no asumir que la máscara de todas las ilustraciones será óptima sin inspección.
- Se mantienen las cuatro muestras CMYK del compuesto original, ICC, tamaño y resolución cuando está disponible. No hay conversión CMYK del original, ni prueba de interoperabilidad Scribus requerida.

El resto de secciones recopila investigación y experimentos históricos y **no sustituye este procedimiento**.

## Instalación en entorno virtual (macOS y Linux)

Requisitos: Python 3.10+ y, para leer PSD, ImageMagick 6 o 7 (en Ubuntu, comando `convert`).
ImageMagick se instala **en el sistema**, no dentro del entorno virtual Python.

- macOS (Homebrew): `brew install imagemagick`
- Arch Linux: `sudo pacman -S imagemagick`

Clona el repositorio y crea su entorno aislado:

```bash
git clone https://github.com/Piraito/illustration-extraction.git
cd illustration-extraction
bash setup.sh
```

`setup.sh` crea `.venv/`, actualiza pip e instala las dependencias de `requirements.txt`.
Si se quiere elegir intérprete: `PYTHON=python3.12 bash setup.sh`.

También puede hacerse manualmente:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Comprobación:

```bash
.venv/bin/python src/extract_illustrations.py --help
convert -version
```

No hace falta activar el entorno si se usa `.venv/bin/python`. Para activarlo: `source .venv/bin/activate`; para salir: `deactivate`. El directorio `.venv/` está excluido de Git.

## Uso

```bash
python src/extract_illustrations.py "/ruta/escaneos" "/ruta/salida"
python src/extract_illustrations.py "/ruta/escaneos" "/ruta/salida" --recursivo
```

Admite JPG/JPEG y PSD CMYK de 8 bits con ICC. Exporta TIFF de 8 bits con cinco canales **CMYK + alfa no premultiplicado**, conservando **sin modificar** las cuatro muestras CMYK originales y el perfil ICC incrustado. Conserva dimensiones y, cuando se pueden leer, los ppp del original. La máscara PNG auxiliar solo se genera si se solicita con `--export-mask`. Para calcular alfa utiliza una conversión ICC a RGB **solo en memoria**.

El programa no sobrescribe archivos TIFF existentes. En caso de archivos homónimos como `23.psd` y `23.jpg`, genera `23_psd.tif` y `23_jpg.tif`. Con `--recursivo`, conserva las subcarpetas. Los errores quedan en `errores_procesamiento.txt`.

## Formatos de salida

`--output-format` permite elegir uno de los tres modos:

| Modo | Salida | Estado |
| --- | --- | --- |
| `tiff-alpha` (predeterminado) | `10.tif` (CMYK + alfa no premultiplicado) | Validado previamente sobre PSD real |
| `tiff-layer-mask` | `10_editable.tif` (TIFF con datos de capa CMYK y máscara editable estilo Photoshop) | Validado visualmente en Krita con la ilustración de prueba |
| `both` | Ambos TIFF | Implementación experimental |

Para disponer del nuevo modo editable en el entorno virtual:

```bash
.venv/bin/python -m pip install -r requirements-layered.txt
.venv/bin/python src/extract_illustrations.py ../pruebas ../resultados-editables --output-format both
```

Para mantener exclusivamente la salida convencional, basta con `requirements.txt` y omitir `--output-format`.

**Importante:** el modo editable escribe tanto los datos TIFF compuestos como un bloque `ImageSourceData` (37724) con una capa que contiene los cuatro canales CMYK y una máscara de usuario independiente (`USER_LAYER_MASK`, -2). La imagen original se almacena completa. Se comprueba la integridad del TIFF y de su información de capas/máscara al guardarlo, y Krita reconoció correctamente la máscara y los colores en una prueba real tras corregir la polaridad CMYK. La compatibilidad con GIMP y otras versiones sigue sin confirmarse.

El PNG auxiliar de máscara es opcional: utilizar `--export-mask` cuando se necesite para diagnóstico. Para las decisiones de formato y los criterios de aceptación, consulta [docs/output-formats.md](docs/output-formats.md).

Ejemplo de exportación opcional de la máscara para inspección:

```bash
.venv/bin/python src/extract_illustrations.py ../pruebas ../resultados --output-format tiff-alpha --export-mask
```

Los TIFF existentes se omiten; para regenerar con la máscara auxiliar utiliza otra carpeta de salida.

## Comparar el algoritmo de máscaras (experimental)

La opción `--mask-method` permite comparar:

- `acuarela` (predeterminado): algoritmo inicial, probado en el tiburón rosa.
- `adaptive`: detección generalizada en Lab, con estimación cromática del papel desde los bordes del escaneo, compensación espacial del fondo, eliminación de pequeñas partículas aisladas y preservación de componentes coloreados separados.

El algoritmo nuevo **sigue en validación con la colección real**. Las primeras pruebas mostraron pérdida de blancos interiores y, posteriormente, de aguadas extensas de fondo. Se conserva la protección espacial del interior y se ha añadido una detección de aguadas externas de baja frecuencia: compara el color suavizado con el papel de los bordes y reduce progresivamente la confianza con la distancia a la ilustración. La corrección de aguadas requiere todavía validación visual sobre los tiburones reales. Esto puede conservar algo más de papel junto a la ilustración, deliberadamente, para priorizar la integridad de la pintura. Presupone que hay suficiente papel alrededor de las ilustraciones. Los parámetros `--umbral` y `--anchura` se interpretan en unidades Lab en `adaptive`, por lo que no son directamente equivalentes a los de `legacy`. El CMYK, el ICC, las dimensiones y el modo de TIFF se conservan sin cambios.

Ejemplo desde la raíz de este repositorio, en carpetas separadas:

```bash
.venv/bin/python src/extract_illustrations.py ../pruebas ../comparacion-legacy \
  --output-format tiff-layer-mask --mask-method legacy
.venv/bin/python src/extract_illustrations.py ../pruebas ../comparacion-adaptive \
  --output-format tiff-layer-mask --mask-method adaptive
```

Prueba automática del nuevo algoritmo (sin archivos reales):

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_adaptive_mask.py' -v
```

**Importante:** la protección espacial solo puede garantizar regiones interiores identificadas por el contorno de pigmento; aguadas débiles aisladas y áreas abiertas siguen siendo problemáticas. Revisar las aguadas tenues, los bordes sobre fondos claros y oscuros, y los elementos separados antes de usar la máscara nueva para producción.

## Resultado de las pruebas visuales de máscaras

**Decisión (20 de noviembre de 2026):** mantener `--mask-method legacy` como método predeterminado y de referencia. El usuario verificó visualmente que `legacy` es claramente superior al experimento `adaptive` para las acuarelas de tiburones.

- `adaptive` inicial: pérdida importante de aguadas de color exteriores y zonas claras interiores.
- Tras protección espacial: interiores correctos, pero se seguía perdiendo gran parte de la aguada.
- Tras ampliar detección espacial con imagen suavizada: aparece un halo desenfocado artificial en vez de recuperar la textura y los bordes reales de la acuarela.

**No utilizar `adaptive` en producción** con estos escaneos. Se conserva como experimento separado para evitar perder el historial, pero no está validado. No continuar ajustando simplemente desenfoque, dilatación o umbrales. Próxima investigación: analizar casos reales de aguadas y pigmento frente a papel a escala de píxel (preferiblemente con recortes de originales y sus máscaras) y evaluar un método que respete la estructura fina sin crear halos. Ninguna modificación al proceso de color CMYK, ICC o al TIFF editable validado en Krita.

## Diagnóstico comparativo sin alterar el extractor

Para investigar por qué `legacy` preserva mejor las aguadas, ejecutar **un único PSD original**. La herramienta no crea TIFF ni modifica el PSD; emplea la misma conversión ICC a RGB temporal que el extractor y calcula ambas máscaras.

Desde la raíz del repositorio, con las rutas de la colección Agaden:

```bash
.venv/bin/python src/diagnose_masks.py \
  "../escaneadas-natalia/ESCANEADO IMAGENES LIBRO/10.psd" \
  "../diagnostico-10"
```

Salidas:
- `original_srgb.png`: vista del original (conversión desde CMYK con ICC).
- `legacy_alpha.png` y `adaptive_alpha.png`: máscaras efectivas exactas de ambos algoritmos.
- `legacy_sobre_damero.png` y `adaptive_sobre_damero.png`: composiciones diagnósticas con los colores RGB originales sin corregir sobre damero.
- `diferencia_rojo_legacy_azul_adaptive.png`: rojo significa que legacy conserva más alfa; azul que adaptive conserva más.
- `distancia_lab_papel.png`: contraste cromático respecto al papel del borde, **señal de diagnóstico**, no señal interna ni prueba de que exista pigmento.
- `informe.json`: dimensiones, referencia Lab del papel y promedios de alfa/color en zonas heurísticas.

Para medir una región elegida manualmente (coordenadas en píxeles del **PSD original**, no de la miniatura), añadir argumentos `--region` repetibles:

```bash
.venv/bin/python src/diagnose_masks.py \
  "../escaneadas-natalia/ESCANEADO IMAGENES LIBRO/10.psd" \
  "../diagnostico-10-regiones" \
  --region papel:40:40:150:150 \
  --region aguada:550:600:100:120
```

**Las coordenadas del ejemplo son ilustrativas**, deben seleccionarse en el documento real y estar dentro de sus dimensiones. Una región estadística no constituye una máscara validada o una etiqueta fiable de pigmento: requiere inspección visual. Cada ejecución debe usar una carpeta nueva; se rechaza escribir sobre una carpeta no vacía.

Pruebas unitarias sin originales:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_diagnose_masks.py' -v
```

Ninguna imagen original se sube al repositorio y no se altera el método `legacy` ni el TIFF CMYK editable.

## Experimento cromático conservador (20 noviembre 2026)

El diagnóstico visual de `10.psd` demuestra que `legacy` conserva mejor la aguada rosa que `adaptive`. Una investigación adicional **sobre los PNG reducidos de ese diagnóstico**, no sobre el PSD a resolución completa, indica que un umbral cromático suficientemente estricto para discriminar el papel añade muy pocos píxeles respecto a `legacy`; reducirlo aumenta claramente la detección espuria en el papel del borde. **No se ha demostrado una mejora visual**.

Para investigar con rigor, se añadió `src/chroma_probe.py`: es un **ensayo de diagnóstico**, no un tercer modo de extracción. Compara una señal cromática local Lab a/b (sin desenfoque ni dilatación) con el alfa exacto de `legacy`, calcula `max(legacy, cromático)` únicamente como hipótesis y muestra cuánto alfa se añade y cuánto aparece incorrectamente en el borde del papel.

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_chroma_probe.py' -v
.venv/bin/python src/chroma_probe.py \
  "../escaneadas-natalia/ESCANEADO IMAGENES LIBRO/10.psd" \
  "../diagnostico-cromatico-10"
```

Genera `01_legacy_alpha.png`, `02_candidato_cromatico.png`, `03_combinado_experimental.png`, `04_alfa_anadido.png`, `05_distancia_cromatica.png` y `informe.json`. Si el mapa `04` está casi negro, la señal nueva no aporta valor. Si se ilumina el papel, indica falsos positivos. La referencia de papel se extrae del borde y **no permite concluir** que cualquier diferencia cromática sea pigmento.

No modifica `legacy`, los TIFF, el ICC ni la imagen CMYK. No incorporar esta variante a producción sin contraste visual y mediciones sobre el PSD real.

## Experimento conservador: `legacy-plus` (solo diagnóstico)

A partir del diagnóstico real de `10.psd` se añadió `src/legacy_plus_mask.py`, que **no sustituye ni modifica** el extractor ni el formato TIFF. Es una propuesta para recuperar pigmento adicional únicamente cuando:

- el píxel muestra una diferencia **cromática local** respecto al papel de referencia, sin suavizar el color;
- el píxel está próximo a una zona que `legacy` ya conserva;
- la nueva máscara nunca reduce la opacidad de `legacy` (`max(legacy, propuesta)`).

Se evita explícitamente extender opacidad mediante un radio de desenfoque o un degradado espacial. Sigue siendo heurístico y puede incluir ruido de escaneo o pigmento falso: **no validado para exportación ni producción**.

Desde la raíz del repositorio:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_legacy_plus_mask.py' -v
.venv/bin/python src/diagnose_masks.py \
  "../escaneadas-natalia/ESCANEADO IMAGENES LIBRO/10.psd" \
  "../diagnostico-10-legacy-plus"
```

La segunda orden genera también `legacy_plus_alpha_experimental.png`, `legacy_plus_adicion_experimental.png` (únicamente alfa añadido) y `legacy_plus_sobre_damero_experimental.png`. Revisar esa última frente a `legacy_sobre_damero.png` y consultar el `informe.json`. Este análisis es previo a cualquier integración en el extractor y no implica que `legacy-plus` sea mejor visualmente.

## Experimento de continuidad cromática (solo diagnóstico)

`src/connected_wash.py` propone una nueva variante **sin modificar `legacy`**: identifica píxeles cromáticamente diferentes del papel, encuentra sus componentes conectados y acepta solo los que contienen píxeles conservados con alta confianza por `legacy`. Excluye componentes conectados al borde del escaneo para reducir falsos positivos. No usa desenfoque, distancia al sujeto, dilatación ni degradados espaciales para asignar alfa. Conserva como mínimo el alfa original.

**Exportación para inspección en Krita:** también puede seleccionarse explícitamente con `--mask-method connected-wash --output-format tiff-layer-mask`. Se usa el escritor TIFF CMYK/ICC con máscara de capa ya validado; solo cambia el alfa experimental. No se recomienda para producción y `acuarela` sigue siendo el método predeterminado.

La conectividad no demuestra que una región sea pigmento; el papel con dominante y las aguadas parcialmente desconectadas pueden provocar errores. Es un **experimento sin validación visual suficiente**; la exportación únicamente facilita examinarlo con zoom y editar su máscara.

Prueba sintética:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_connected_wash.py' -v
```

Para un PSD real:

```bash
.venv/bin/python src/diagnose_masks.py \
  "../escaneadas-natalia/ESCANEADO IMAGENES LIBRO/10.psd" \
  "../diagnostico-10-connected"
```

Para generar un TIFF editable **solo de 10.psd**, prepara una carpeta de entrada con esa muestra si no existe ya:

```bash
mkdir -p ../prueba-connected-10
cp "../escaneadas-natalia/ESCANEADO IMAGENES LIBRO/10.psd" ../prueba-connected-10/
.venv/bin/python src/extract_illustrations.py \\
  ../prueba-connected-10 ../resultado-connected-10 \\
  --mask-method connected-wash --output-format tiff-layer-mask
```

Abrir `../resultado-connected-10/10_editable.tif` en Krita y responder **Sí** al aviso de datos PSD incrustados. La máscara debe aparecer independiente y poder desactivarse para recuperar el papel completo. Usar otra carpeta si la salida existe.

Comparar `connected_wash_sobre_damero_experimental.png` con `legacy_sobre_damero.png`. Examinar `connected_wash_adicion_experimental.png`: solo muestra el alfa que se propone añadir. `informe.json` incluye el umbral cromático escogido, componentes aceptados y píxeles adicionales. La validación visual decidirá si se continúa o se descarta.

## Decisión final de evaluación visual (20 de noviembre de 2026)

La validación manual del TIFF `connected-wash` en Krita confirmó que el resultado era visualmente indistinguible de `legacy` a efectos prácticos. Se cierra esta línea de experimentación: **`acuarela` (denominado anteriormente `legacy`) es el mejor método probado y el único recomendado para las acuarelas examinadas**.

Las otras variantes (`adaptive`, `legacy-plus` y `connected-wash`) se conservan por trazabilidad y reproducción de las pruebas, pero no se recomiendan para maquetación. No seguir ajustando heurísticas equivalentes sin nuevas evidencias o máscaras de referencia.

Flujo recomendado: ejecutar `--mask-method acuarela --output-format tiff-layer-mask`, abrir el TIFF en Krita y retocar manualmente su máscara cuando sea necesario. Los canales CMYK originales, el ICC y la integridad del TIFF editable permanecen intactos.

## Limitaciones actuales

- **No procesa RGB** (por ejemplo `23.jpg` si es sRGB): lo registra como error hasta que se diseñe una salida que preserve RGB y su ICC.
- Los PSD se leen mediante la imagen compuesta `PSD[0]` de ImageMagick, pero el perfil ICC se extrae directamente de los recursos del PSD original. La fidelidad de la composición de Smart Objects debe evaluarse sobre tus imágenes.
- La máscara sigue calibrada para una acuarela concreta y puede perder aguadas muy tenues o crear halos. Los colores CMYK originales no se corrigen en los bordes.
- El archivo final no incluye cambios cromáticos en el interior ni en los bordes: únicamente añade alfa.
- No procesa PSD HDR/32 bits flotantes.
- No se suben ilustraciones originales al repositorio.


## Siguientes pruebas

1. Comprobar con archivos reales la composición de PSD y preservación de los cuatro canales CMYK y perfil ICC.
2. Probar distintas ilustraciones, colores de papel y resoluciones; medir pérdidas de aguadas, halos y alteraciones interiores.
3. Generalizar la detección de fondo sin suposiciones de pigmento rosa.
4. Mantener pendiente la evaluación de alternativas de corrección del borde, sin modificar el CMYK original en esta versión.
5. Ejecutar prueba estructural `python -m unittest discover -s tests -p 'test_layered_tiff.py'` y comprobar visualmente en Krita la máscara editable; añadir métricas y opciones de revisión.

En Ubuntu con ImageMagick 6, el comando predeterminado es `convert`; en sistemas que solo proporcionan ImageMagick 7 usar `--magick magick`.

**Nota de migración:** la salida principal ahora es TIFF, no PNG; utiliza una carpeta de resultados nueva para las pruebas.

