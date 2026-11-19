# illustration-extraction

Extracción **experimental** de ilustraciones escaneadas sobre papel claro mediante una máscara alfa gradual. Proyecto pensado para procesamiento por lotes y posterior revisión en GIMP o Krita.

## Estado

Prototipo basado en una acuarela de prueba. **No es un extractor genérico validado**: los umbrales cromáticos actuales están calibrados para papel claro y aguadas rosadas. Se conservan las dimensiones de los escaneos y no se modifican los originales.

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

Admite JPG/JPEG y PSD CMYK de 8 bits con ICC. Exporta TIFF de 8 bits con cinco canales **CMYK + alfa no premultiplicado**, conservando **sin modificar** las cuatro muestras CMYK originales y el perfil ICC incrustado. Conserva dimensiones y, cuando se pueden leer, los ppp del original. Genera también la máscara PNG de 8 bits. Para calcular alfa utiliza una conversión ICC a RGB **solo en memoria**.

El programa no sobrescribe archivos TIFF existentes. En caso de archivos homónimos como `23.psd` y `23.jpg`, genera `23_psd.tif` y `23_jpg.tif`. Con `--recursivo`, conserva las subcarpetas. Los errores quedan en `errores_procesamiento.txt`.

## Formatos de salida

`--output-format` permite elegir uno de los tres modos:

| Modo | Salida | Estado |
| --- | --- | --- |
| `tiff-alpha` (predeterminado) | `10.tif` (CMYK + alfa no premultiplicado) | Validado previamente sobre PSD real |
| `tiff-layer-mask` | `10_editable.tif` (TIFF con datos de capa CMYK y máscara editable estilo Photoshop) | Implementación experimental, pendiente de comprobar en Krita |
| `both` | Ambos TIFF | Implementación experimental |

Para disponer del nuevo modo editable en el entorno virtual:

```bash
.venv/bin/python -m pip install -r requirements-layered.txt
.venv/bin/python src/extract_illustrations.py ../pruebas ../resultados-editables --output-format both
```

Para mantener exclusivamente la salida convencional, basta con `requirements.txt` y omitir `--output-format`.

**Importante:** el modo editable escribe tanto los datos TIFF compuestos como un bloque `ImageSourceData` (37724) con una capa que contiene los cuatro canales CMYK y una máscara de usuario independiente (`USER_LAYER_MASK`, -2). La imagen original se almacena completa. Se comprueba la integridad del TIFF y de su información de capas/máscara al guardarlo, pero **todavía no se ha demostrado que Krita o GIMP importen ese canal como máscara de capa editable**. Si el editor no lo reconoce, el archivo puede abrirse como TIFF aplanado con alfa.

El programa crea todavía el PNG auxiliar de la máscara. Para las decisiones de formato y los criterios de aceptación, consulta [docs/output-formats.md](docs/output-formats.md).

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

