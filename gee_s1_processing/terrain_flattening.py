"""
Version: v1.0
Date: 2021-03-12
Description: This code is adopted from
Vollrath, A., Mullissa, A., & Reiche, J. (2020).
Angular-Based Radiometric Slope Correction for Sentinel-1 on Google Earth Engine.
Remote Sensing, 12(11), [1867]. https://doi.org/10.3390/rs12111867
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import ee

if TYPE_CHECKING:
    from ee.image import Image
    from ee.imagecollection import ImageCollection


def slope_correction(
    collection: ImageCollection,
    TERRAIN_FLATTENING_MODEL: str,
    DEM: str,
    TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER: int,
) -> ImageCollection:
    """

    Parameters
    ----------
    collection : ImageCollection
        DESCRIPTION.
    TERRAIN_FLATTENING_MODEL : str
        The radiometric terrain normalization model, either volume or direct
    DEM : str
        The DEM to be used
    TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER : int
        The additional buffer to account for the passive layover and shadow
    Returns
    -------
    ImageCollection
        An image collection where radiometric terrain normalization is
        implemented on each image

    """

    ninetyRad = ee.Image.constant(90).multiply(math.pi / 180)

    def _volumetric_model_SCF(theta_iRad: Image, alpha_rRad: Image) -> Image:
        """

        Parameters
        ----------
        theta_iRad : Image
            The scene incidence angle
        alpha_rRad : Image
            Slope steepness in range

        Returns
        -------
        Image
            Applies the volume model in the radiometric terrain normalization

        """

        # Volume model
        nominator = (ninetyRad.subtract(theta_iRad).add(alpha_rRad)).tan()
        denominator = (ninetyRad.subtract(theta_iRad)).tan()
        return nominator.divide(denominator)

    def _direct_model_SCF(theta_iRad: Image, alpha_rRad: Image, alpha_azRad: Image) -> Image:
        """

        Parameters
        ----------
        theta_iRad : Image
            The scene incidence angle
        alpha_rRad : Image
            Slope steepness in range
        alpha_azRad : Image
            DESCRIPTION

        Returns
        -------
        Image
            Applies the direct model in the radiometric terrain normalization

        """
        # Surface model
        nominator = (ninetyRad.subtract(theta_iRad)).cos()
        denominator = alpha_azRad.cos().multiply(
            (ninetyRad.subtract(theta_iRad).add(alpha_rRad)).cos()
        )
        return nominator.divide(denominator)

    def _erode(image: Image, distance: int) -> Image:
        """


        Parameters
        ----------
        image : Image
            Image to apply the erode function to
        distance : int
            The distance to apply the buffer

        Returns
        -------
        Image
            An image that is masked to conpensate for passive layover
            and shadow depending on the given distance

        """
        # buffer function (thanks Noel)

        d = (
            image.Not()
            .unmask(1)
            .fastDistanceTransform(30)
            .sqrt()
            .multiply(ee.Image.pixelArea().sqrt())
        )

        return image.updateMask(d.gt(distance))

    def _masking(alpha_rRad: Image, theta_iRad: Image, buffer: int) -> Image:
        """

        Parameters
        ----------
        alpha_rRad : Image
            Slope steepness in range
        theta_iRad : Image
            The scene incidence angle
        buffer : int
            DESCRIPTION.

        Returns
        -------
        Image
            An image that is masked to conpensate for passive layover
            and shadow depending on the given distance

        """
        # calculate masks
        # layover, where slope > radar viewing angle
        layover = alpha_rRad.lt(theta_iRad).rename("layover")
        # shadow
        shadow = alpha_rRad.gt(
            ee.Image.constant(-1).multiply(ninetyRad.subtract(theta_iRad))
        ).rename("shadow")
        # combine layover and shadow
        mask = layover.And(shadow)
        # add buffer to final mask
        if buffer > 0:
            mask = _erode(mask, buffer)
        return mask.rename("no_data_mask")

    def _correct(image: Image) -> Image:
        """


        Parameters
        ----------
        image : Image
            Image to apply the radiometric terrain normalization to

        Returns
        -------
        Image
            Radiometrically terrain corrected image

        """

        bandNames = image.bandNames()

        geom = image.geometry()
        proj = image.select(1).projection()

        elevation = DEM.resample("bilinear").reproject(proj, None, 10).clip(geom)

        # calculate the look direction
        heading = ee.Terrain.aspect(image.select("angle")).reduceRegion(
            ee.Reducer.mean(), image.geometry(), 1000
        )

        # in case of null values for heading replace with 0
        heading = ee.Dictionary(heading).combine({"aspect": 0}, False).get("aspect")

        heading = ee.Algorithms.If(
            ee.Number(heading).gt(180), ee.Number(heading).subtract(360), ee.Number(heading)
        )

        # the numbering follows the article chapters
        # 2.1.1 Radar geometry
        theta_iRad = image.select("angle").multiply(math.pi / 180)
        phi_iRad = ee.Image.constant(heading).multiply(math.pi / 180)

        # 2.1.2 Terrain geometry
        alpha_sRad = ee.Terrain.slope(elevation).select("slope").multiply(math.pi / 180)

        aspect = ee.Terrain.aspect(elevation).select("aspect").clip(geom)

        aspect_minus = aspect.updateMask(aspect.gt(180)).subtract(360)

        phi_sRad = (
            aspect.updateMask(aspect.lte(180))
            .unmask()
            .add(aspect_minus.unmask())
            .multiply(-1)
            .multiply(math.pi / 180)
        )

        # elevation = DEM.reproject(proj,None, 10).clip(geom)

        # 2.1.3 Model geometry
        # reduce to 3 angle
        phi_rRad = phi_iRad.subtract(phi_sRad)

        # slope steepness in range (eq. 2)
        alpha_rRad = (alpha_sRad.tan().multiply(phi_rRad.cos())).atan()

        # slope steepness in azimuth (eq 3)
        alpha_azRad = (alpha_sRad.tan().multiply(phi_rRad.sin())).atan()

        # 2.2
        # Gamma_nought
        gamma0 = image.divide(theta_iRad.cos())

        if TERRAIN_FLATTENING_MODEL == "VOLUME":
            # Volumetric Model
            scf = _volumetric_model_SCF(theta_iRad, alpha_rRad)

        if TERRAIN_FLATTENING_MODEL == "DIRECT":
            scf = _direct_model_SCF(theta_iRad, alpha_rRad, alpha_azRad)

        # apply model for Gamm0
        gamma0_flat = gamma0.multiply(scf)

        # get Layover/Shadow mask
        mask = _masking(alpha_rRad, theta_iRad, TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER)
        output = gamma0_flat.mask(mask).rename(bandNames).copyProperties(image)
        output = ee.Image(output).addBands(image.select("angle"), None, True)

        return output.set("system:time_start", image.get("system:time_start"))

    return collection.map(_correct)
