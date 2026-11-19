# illustration-extraction

Extracción **experimental** de ilustraciones escaneadas sobre papel claro mediante una máscara alfa gradual. Proyecto pensado para procesamiento por lotes y posterior revisión en GIMP o Krita.

## Estado

Prototipo basado en una acuarela de prueba. **No es un extractor genérico validado**: los umbrales cromáticos actuales están calibrados para papel claro y aguadas rosadas. Se conservan las dimensiones de los escaneos y no se modifican los originales.

## Instalación

Python 3.10+ e ImageMagick 7 (comando `magick`) para leer el compuesto visible de los PSD.

```bash
python -m pip install -r requirements.txt
```

## Uso

```bash
python src/extract_illustrations.py "/ruta/escaneos" "/ruta/salida"
python src/extract_illustrations.py "/ruta/escaneos" "/ruta/salida" --recursivo
```

Admite JPG, JPEG y PSD; guarda un PNG RGBA de 16 bits/canal y un PNG de máscara en grises (16 bits). Mantiene dimensiones en píxeles y, con `--recursivo`, estructura de subcarpetas. Registra fallos en `errores_procesamiento.txt`. No sobrescribe PNG ya existentes. **Atención:** dos entradas con el mismo nombre base y extensiones distintas pueden colisionar.

## Restricciones

- La composición visible de los PSD procede de `PSD[0]` de ImageMagick; requiere comprobar su fidelidad con PSD reales que contengan Smart Objects.
- Los PSD de 32 bits flotantes se leen mediante TIFF flotante intermedio, pero se rechazan valores fuera de 0..1; la gestión ICC/HDR integral está pendiente.
- El PNG de salida usa 16 bits enteros, no 32 bits flotantes.
- La versión actual **corrige RGB cerca de bordes**. No implementa todavía el modo alternativo de conservar el RGB sin modificar; la elección está expresamente aplazada.
- No garantiza conservar aguadas casi indistinguibles del papel ni eliminar todos los halos. Revisar los bordes sobre fondo claro y oscuro.
- No se incluyen escaneos de ilustraciones en este repositorio.

## Siguientes pruebas

1. Validar un PSD real con Smart Objects, perfil ICC y 32 bits flotantes frente a la composición de referencia.
2. Probar distintas ilustraciones, colores de papel y resoluciones; medir pérdidas de aguadas, halos y alteraciones interiores.
3. Generalizar la detección de fondo sin suposiciones de pigmento rosa.
4. Evaluar los dos modos de RGB (original o corregido cerca del borde), **sin decidirlos todavía**.
5. Añadir pruebas automáticas, métricas y opciones de revisión en GIMP/Krita.
