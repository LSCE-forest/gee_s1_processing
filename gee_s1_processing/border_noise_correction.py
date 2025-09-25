"""
Version: v1.1
Date: 2021-03-11
Authors: Adopted from Hird et al. 2017 Remote Sensing (supplementary material): http://www.mdpi.com/2072-4292/9/12/1315)
Description: This script applied additional border noise correction
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import helper

if TYPE_CHECKING:
    from ee.image import Image


# ---------------------------------------------------------------------------//
# Additional Border Noise Removal
# ---------------------------------------------------------------------------//


def maskAngLT452(image: Image) -> Image:
    """
    mask out angles >= 45.23993

    Parameters
    ----------
    image : Image
        image to apply the border noise masking

    Returns
    -------
    Image
        Masked image

    """
    ang = image.select(["angle"])
    return image.updateMask(ang.lt(45.23993)).set(
        "system:time_start", image.get("system:time_start")
    )


def maskAngGT30(image: Image) -> Image:
    """
    mask out angles <= 30.63993

    Parameters
    ----------
    image : Image
        image to apply the border noise masking

    Returns
    -------
    Image
        Masked image

    """

    ang = image.select(["angle"])
    return image.updateMask(ang.gt(30.63993)).set(
        "system:time_start", image.get("system:time_start")
    )


def maskEdge(image: Image) -> Image:
    """
    Remove edges.

    Parameters
    ----------
    image : Image
        image to apply the border noise masking

    Returns
    -------
    Image
        Masked image

    """

    mask = (
        image.select(0).unitScale(-25, 5).multiply(255).toByte()
    )  # .connectedComponents(ee.Kernel.rectangle(1,1), 100)
    return image.updateMask(mask.select(0)).set("system:time_start", image.get("system:time_start"))


def f_mask_edges(image: Image) -> Image:
    """
    Function to mask out border noise artefacts

    Parameters
    ----------
    image : Image
        image to apply the border noise correction to

    Returns
    -------
    Image
        Corrected image

    """

    db_img = helper.lin_to_db(image)
    output = maskAngGT30(db_img)
    output = maskAngLT452(output)
    # output = maskEdge(output)
    output = helper.db_to_lin(output)
    return output.set("system:time_start", image.get("system:time_start"))
