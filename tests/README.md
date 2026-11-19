# Comprobación de TIFF CMYK + alfa en Scribus

La compatibilidad de cinco canales CMYK+A no está validada con la versión concreta de Scribus del usuario. Esta prueba es **diagnóstica**, no una prueba de extracción de acuarelas.

## Generar TIFF de cinco canales

Con el entorno virtual activo:

```bash
python -m pip install tifffile
python tests/make_cmyka_test.py /tmp/test_cmyka_sin_perfil.tif
```

Ese fichero carece deliberadamente de perfil ICC: sirve **solo para ver si se interpreta alfa**; no sirve para validar color de imprenta.

Para probar el flujo de gestión de color, extrae el perfil ICC auténtico de un PSD de la colección (requiere ExifTool):

```bash
sudo apt install libimage-exiftool-perl
exiftool -icc_profile -b "/ruta/10.psd" > /tmp/original_fogra39.icc
python tests/make_cmyka_test.py /tmp/test_cmyka_fogra39.tif --icc /tmp/original_fogra39.icc
```

El generador comprueba cabecera y espacio CMYK del ICC, estructura TIFF (Photometric=Separated, SamplesPerPixel=5, ExtraSamples=UnassociatedAlpha), y que al releer el TIFF los cuatro canales CMYK y el alfa coincidan exactamente.

## Validación en Scribus (manual)

1. Abre un documento de prueba con gestión de color activada y coloca un rectángulo de fondo intenso.
2. Importa el TIFF **con ICC** encima del rectángulo en un marco de imagen.
3. Comprueba que las esquinas son transparentes, que hay una transición alfa suave, y que la ventana rectangular interior es transparente. Verifica que Scribus no lo interpreta como un TIFF CMYK sin transparencia.
4. Verifica que reconoce el ICC incrustado, sin asignar un perfil de sustitución.
5. Exporta PDF/X-4 según vuestro flujo habitual, **sin forzar la conversión general de las imágenes a otro perfil**. El Output Intent del PDF/X-4 es independiente del perfil ICC de cada imagen.
6. Comprueba el PDF con la previsualización de separaciones y, si es posible, un inspector de objetos PDF. La vista correcta no basta: interesa constatar que el objeto conserva CMYK y el tratamiento de transparencia (p. ej., una máscara suave) y que no se ha rasterizado a RGB sin querer.

## Criterios de aceptación

- TIFF: cinco muestras de 8 bits, cuatro CMYK originales sin alteración + alfa no premultiplicado, perfil ICC correcto.
- Scribus: apariencia correcta tanto sobre blanco como sobre un fondo fuerte; muestra ICC, sin convertir los canales CMYK indebidamente.
- PDF/X-4: transparencia operativa y perfiles/color correctos dentro del flujo habitual.
- Si falla un criterio, **no incorporar CMYKA TIFF al extractor** hasta determinar la causa.

No subir PSD, JPEG de la colección ni perfiles ICC propietarios al repositorio público.
