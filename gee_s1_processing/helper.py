"""
Version: v1.2
Date: 2021-02-11
Authors: Mullissa A., Vollrath A., Braun, C., Slagter B., Balling J., Gou Y., Gorelick N.,  Reiche J.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import ee

if TYPE_CHECKING:
    from ee.image import Image


def lin_to_db(image: Image) -> Image:
    """
    Convert backscatter from linear to dB.

    Parameters
    ----------
    image : Image
        Image to convert

    Returns
    -------
    Image
        output image

    """
    bandNames = image.bandNames().remove("angle")
    db = ee.Image.constant(10).multiply(image.select(bandNames).log10()).rename(bandNames)
    return image.addBands(db, None, True)


def db_to_lin(image: Image) -> Image:
    """
    Convert backscatter from dB to linear.

    Parameters
    ----------
    image : Image
        Image to convert

    Returns
    -------
    Image
        output image

    """
    bandNames = image.bandNames().remove("angle")
    lin = ee.Image.constant(10).pow(image.select(bandNames).divide(10)).rename(bandNames)
    return image.addBands(lin, None, True)


def lin_to_db2(image: Image) -> Image:
    """
    Convert backscatter from linear to dB by removing the ratio band.

    Parameters
    ----------
    image : Image
        Image to convert

    Returns
    -------
    Image
        Converted image

    """
    db = ee.Image.constant(10).multiply(image.select(["VV", "VH"]).log10()).rename(["VV", "VH"])
    return image.addBands(db, None, True)


def add_ratio_lin(image: Image) -> Image:
    """
    Adding ratio band for visualization

    Parameters
    ----------
    image : Image
        Image to use for creating band ratio

    Returns
    -------
    Image
        Image containing the ratio band

    """
    ratio = image.addBands(image.select("VV").divide(image.select("VH")).rename("VVVH_ratio"))

    return ratio.set("system:time_start", image.get("system:time_start"))
