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

Admite JPG, JPEG y PSD; convierte CMYK con ICC incorporado a sRGB y guarda un PNG RGBA de 8 bits/canal y su máscara en grises (8 bits). Mantiene dimensiones en píxeles y, con `--recursivo`, estructura de subcarpetas. Registra fallos en `errores_procesamiento.txt`. No sobrescribe PNG ya existentes. Si coinciden nombres base con extensiones diferentes (por ejemplo `23.psd` y `23.jpg`), añade `_psd` o `_jpg` al nombre de salida.

## Restricciones

- La composición visible de los PSD procede de `PSD[0]` de ImageMagick; requiere comprobar su fidelidad con PSD reales que contengan Smart Objects.
- CMYK con perfil ICC incrustado se convierte a sRGB usando LittleCMS vía Pillow; CMYK sin ICC se rechaza. Los RGB sin ICC se interpretan como sRGB.
- La colección detectada es CMYK de 8 bits con FOGRA39, salvo un JPG sRGB; el PNG de salida utiliza 8 bits/canal. PSD HDR/32-bit float y perfiles excepcionales no están validados.
- La versión actual **corrige RGB cerca de bordes**. No implementa todavía el modo alternativo de conservar el RGB sin modificar; la elección está expresamente aplazada.
- No garantiza conservar aguadas casi indistinguibles del papel ni eliminar todos los halos. Revisar los bordes sobre fondo claro y oscuro.
- No se incluyen escaneos de ilustraciones en este repositorio.

## Siguientes pruebas

1. Validar PSD CMYK FOGRA39 real con Smart Objects, perfil ICC y composición de referencia.
2. Probar distintas ilustraciones, colores de papel y resoluciones; medir pérdidas de aguadas, halos y alteraciones interiores.
3. Generalizar la detección de fondo sin suposiciones de pigmento rosa.
4. Evaluar los dos modos de RGB (original o corregido cerca del borde), **sin decidirlos todavía**.
5. Añadir pruebas automáticas, métricas y opciones de revisión en GIMP/Krita.

En Ubuntu con ImageMagick 6, el comando predeterminado es `convert`; en sistemas que solo proporcionan ImageMagick 7 usar `--magick magick`.

**Nota de migración:** si procesaste archivos con la versión anterior, retira los PNG de salida antiguos antes de repetir: el script omite archivos de salida existentes.
