"""Optional Photoshop-style editable layer-mask TIFF writer.

Stores the original CMYK in both the standard TIFF image (with normal alpha)
and in the Photoshop ImageSourceData layer payload (with a separate USER_LAYER_MASK).
This does not require Photoshop. GIMP/Krita recognition depends on importer support.
"""
from pathlib import Path

import numpy as np
import tifffile


def guardar_tiff_editable(path: Path, cmyk: np.ndarray, alpha: np.ndarray,
                         icc: bytes, dpi) -> None:
    from psdtags import (
        PsdBlendMode, PsdChannel, PsdChannelId, PsdClippingType,
        PsdCompressionType, PsdFormat, PsdKey, PsdLayer, PsdLayerFlag,
        PsdLayerMask, PsdLayers, PsdRectangle, PsdString, PsdUserMask, TiffImageSourceData,
    )

    height, width = cmyk.shape[:2]
    a = np.rint(np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    rect = PsdRectangle(0, 0, height, width)
    channels = [
        PsdChannel(
            channelid=[PsdChannelId.CHANNEL0, PsdChannelId.CHANNEL1,
                       PsdChannelId.CHANNEL2, PsdChannelId.CHANNEL3][i],
            compression=PsdCompressionType.ZIP,
            data=np.ascontiguousarray(cmyk[..., i]),
        )
        for i in range(4)
    ]
    # -2 is a user layer mask, not the composite alpha (-1).
    channels.append(PsdChannel(
        channelid=PsdChannelId.USER_LAYER_MASK,
        compression=PsdCompressionType.ZIP,
        data=np.ascontiguousarray(a),
    ))
    layer = PsdLayer(
        name='Ilustración original (máscara editable)',
        rectangle=rect,
        channels=channels,
        mask=PsdLayerMask(rectangle=rect, default_color=255),
        opacity=255,
        blendmode=PsdBlendMode.NORMAL,
        clipping=PsdClippingType.BASE,
        flags=PsdLayerFlag.PHOTOSHOP5,
        blending_ranges=(),
        info=[PsdString(PsdKey.UNICODE_LAYER_NAME,
                        'Ilustración original (máscara editable)')],
    )
    source = TiffImageSourceData(
        name='Illustration Extraction',
        psdformat=PsdFormat.LE32BIT,
        layers=PsdLayers(key=PsdKey.LAYER, has_transparency=False,
                         layers=[layer]),
        usermask=PsdUserMask(),
    )
    options = dict(
        photometric='separated',
        planarconfig='contig',
        extrasamples=['unassalpha'],
        iccprofile=icc,
        compression='deflate',
        metadata=None,
        extratags=[source.tifftag(maxworkers=1)],
    )
    if dpi and len(dpi) >= 2 and dpi[0] > 0 and dpi[1] > 0:
        options.update(resolution=(float(dpi[0]), float(dpi[1])),
                       resolutionunit='inch')
    pixels = np.dstack((cmyk, a))
    tifffile.imwrite(path, pixels, **options)

    # Verify both the ordinary TIFF channels and the independent editable mask.
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        result = page.asarray()
        if (page.samplesperpixel != 5 or
                list(page.extrasamples) != [tifffile.EXTRASAMPLE.UNASSALPHA] or
                not np.array_equal(result[..., :4], cmyk) or
                not np.array_equal(result[..., 4], a)):
            raise RuntimeError('TIFF editable: canales compuestos alterados')
        tag = page.tags.get('InterColorProfile')
        if tag is None or tag.value != icc:
            raise RuntimeError('TIFF editable: perfil ICC alterado')
    reopened = TiffImageSourceData.fromtiff(str(path))
    if not reopened.layers or len(reopened.layers.layers) != 1:
        raise RuntimeError('TIFF editable: capa no recuperable')
    channels = {c.channelid: c.data for c in reopened.layers.layers[0].channels}
    if (PsdChannelId.USER_LAYER_MASK not in channels or
            not np.array_equal(channels[PsdChannelId.USER_LAYER_MASK], a) or
            reopened.layers.layers[0].mask.rectangle != rect):
        raise RuntimeError('TIFF editable: máscara de capa no recuperable')
    for i, key in enumerate([PsdChannelId.CHANNEL0, PsdChannelId.CHANNEL1,
                             PsdChannelId.CHANNEL2, PsdChannelId.CHANNEL3]):
        if key not in channels or not np.array_equal(channels[key], cmyk[..., i]):
            raise RuntimeError(f'TIFF editable: canal de capa {i} alterado')
