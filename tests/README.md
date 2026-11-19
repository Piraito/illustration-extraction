# Pruebas del proyecto

## Estructura TIFF con máscara de capa

Con Python virtual:

```bash
.venv/bin/python -m pip install -r requirements-layered.txt
.venv/bin/python -m unittest discover -s tests -p 'test_layered_tiff.py' -v
```

`test_layered_tiff.py` construye un CMYK sintético y un alfa gradual, escribe TIFF con `ImageSourceData` y máscara de usuario, y verifica lectura de canales CMYK, ICC y máscara integrada. **No verifica automáticamente el reconocimiento de la máscara por Krita o GIMP**.

Para probar con una ilustración real:

```bash
.venv/bin/python src/extract_illustrations.py ../pruebas/ ../resultados-editables/ --output-format both
```

Abre el `*_editable.tif` en Krita y comprueba si aparece una **máscara de capa editable** asociada a la imagen original. Desactívala y comprueba que reaparece el papel completo. Si solo se abre como una capa con alfa, no cumple la aceptación del modo editable: informa de ello y no lo consideres validado.

## Prueba TIFF CMYK + alfa (histórica)

`make_cmyka_test.py` genera un TIFF CMYK+A diagnóstico, con o sin perfil ICC suministrado mediante `--icc`; no es necesario para ejecutar el extractor. **No se requiere ExifTool ni instalar herramientas del sistema** para estas pruebas Python. Se mantiene únicamente como prueba estructural auxiliar.

La validación con Scribus no forma parte de las tareas actuales.
