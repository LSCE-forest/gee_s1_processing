#!/usr/bin/env python3
"""
Version: v1.2
Date: 2025-09-19
Authors: Mullissa A., Vollrath A., Braun, C., Slagter B., Balling J.,
Gou Y., Gorelick N.,  Reiche J.
Description: The modified wrapper function to derive the Sentinel-1 ARD
"""

from dataclasses import dataclass

import ee
from ee.imagecollection import ImageCollection

from . import border_noise_correction as bnc
from . import speckle_filter as sf
from . import terrain_flattening as trf

###########################################
# DO THE JOB
###########################################


@dataclass
class TerrainNormalizationConfig:
    """The structured type to configure terrain normalization
    apply_terrain_flattening : boolean
        Apply terrain flattening if True
    dem : string
        Digital elevation Model used for terrain corrections
    terrain_flattening_model : string
    terrain_flattening_additional_layover_shadow_buffer :  integer
    angle_band : str
        Name of the band giving information on the incidence angle.
    """

    terrain_flattening_model: str = "VOLUME"
    terrain_flattening_additional_layover_shadow_buffer: int = 3
    dem: str = "USGS/SRTMGL1_003"
    angle_band: str = "angle"


@dataclass
class SpeckleFilterConfig:
    """The structured type for configuring speckle
    filters to apply to Sentinel-1
    speckle_filter_framework : string
    speckle_filter : string
    speckle_filter_kernel_size : integer
    speckle_filter_nr_of_images : integer
    """

    speckle_filter_framework: str = "MONO"
    speckle_filter: str = "BOXCAR"
    speckle_filter_kernel_size: int = 3
    speckle_filter_nr_of_images: int = 10


def terrain_normalization_wrapper(
    col: ImageCollection, terrain_normalization_params: TerrainNormalizationConfig
) -> ImageCollection:
    """
    Applies terrain normalization to a collection of GEE images.

    Parameters
    ----------
    col : ImageCollection
        GEE image collection to apply terrain normalization to
    terrain_normalization_params : TerrainNormalizationConfig
        Parameter dataclass to configure the terrain normalization

    Raises
    ------
    ValueError

    Returns
    -------
    ImageCollection
        Image Collection with normalized terrain.
    """
    TERRAIN_FLATTENING_MODEL = terrain_normalization_params.terrain_flattening_model or "VOLUME"
    DEM = terrain_normalization_params.dem or "USGS/SRTMGL1_003"
    TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER = (
        terrain_normalization_params.terrain_flattening_additional_layover_shadow_buffer or 0
    )
    ANGLE_BAND = terrain_normalization_params.angle_band or "angle"

    if ANGLE_BAND not in col.first().bandNames().getInfo():
        raise ValueError(
            "ERROR!!! Parameter ANGLE_BAND does not correspond to any band of the image collection"
        )
    if TERRAIN_FLATTENING_MODEL not in ["DIRECT", "VOLUME"]:
        raise ValueError("ERROR!!! Parameter TERRAIN_FLATTENING_MODEL not correctly defined")
    if TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER < 0:
        raise ValueError(
            "ERROR!!! TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER not correctly defined"
        )

    col = trf.slope_correction(
        col,
        TERRAIN_FLATTENING_MODEL,
        ee.Image(DEM),
        TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER,
    )
    print("Terrain normalization is completed")  # noqa: T201, E501
    return col


def speckle_filter_wrapper(col: ImageCollection, speckle_filter_params: SpeckleFilterConfig):
    """
    Applies preprocessing to a collection of S1 images to return
    an analysis ready sentinel-1 data.

    Parameters
    ----------
    col : ImageCollection
        GEE image collection to be preprocessed
    speckle_filter_params : SpeckleFilterConfig
        Parameter Dataclass that determines the data selection
        and image processing parameters.

    Raises
    ------
    ValueError

    Returns
    -------
    ImageCollection
        A processed Sentinel-1 image collection

    """
    SPECKLE_FILTER_FRAMEWORK = speckle_filter_params.speckle_filter_framework or "MONO"
    SPECKLE_FILTER = speckle_filter_params.speckle_filter or "BOXCAR"
    SPECKLE_FILTER_KERNEL_SIZE = speckle_filter_params.speckle_filter_kernel_size or 3
    SPECKLE_FILTER_NR_OF_IMAGES = speckle_filter_params.speckle_filter_nr_of_images or 10

    if SPECKLE_FILTER_FRAMEWORK not in ["MONO", "MULTI"]:
        raise ValueError("ERROR!!! SPECKLE_FILTER_FRAMEWORK not correctly defined")

    if SPECKLE_FILTER not in ["BOXCAR", "LEE", "GAMMA MAP", "REFINED LEE", "LEE SIGMA"]:
        raise ValueError("ERROR!!! SPECKLE_FILTER not correctly defined")

    if SPECKLE_FILTER_KERNEL_SIZE <= 0:
        raise ValueError("ERROR!!! SPECKLE_FILTER_KERNEL_SIZE not correctly defined")

    bands = col.first().bandNames().getInfo()
    if not [band for band in bands if band in ["VV", "VH"]]:
        raise ValueError("Filters only apply to VH and VV bands.")

    if SPECKLE_FILTER_FRAMEWORK == "MONO":
        col = ee.ImageCollection(
            sf.MonoTemporal_Filter(col, SPECKLE_FILTER_KERNEL_SIZE, SPECKLE_FILTER)
        )
        print("Mono-temporal speckle filtering is completed")  # noqa: T201
    else:
        col = ee.ImageCollection(
            sf.MultiTemporal_Filter(
                col,
                SPECKLE_FILTER_KERNEL_SIZE,
                SPECKLE_FILTER,
                SPECKLE_FILTER_NR_OF_IMAGES,
            )
        )
        print("Multi-temporal speckle filtering is completed")  # noqa: T201

    return col


def get_analysis_ready_data(
    col: ImageCollection,
    speckle_filter_config: SpeckleFilterConfig | None = None,
    terrain_normalization_config: TerrainNormalizationConfig | None = None,
    additional_border_noise_correction: bool = False,
) -> ImageCollection:
    """Get analysis ready data.

    Parameters
    ----------
    col : ImageCollection
        GEE image collection to process>
    speckle_filter_config : SpeckleFilterConfig | None
        Configuration dataclass for speckle filtering. Defaults to None.
    terrain_normalization_config : TerrainNormalizationConfig | None
        Configuration dataclass for terrain normalization. Defaults to None.
    additional_border_noise_correction : bool
        Apply additional border noise correction on True. Defaults to False.

    Returns
    -------
    ImageCollection
        Analysis Ready Data.
    """
    if additional_border_noise_correction:
        col = col.map(bnc.f_mask_edges)
        print("Additional border noise correction is completed")  # noqa: T201

    if speckle_filter_config:
        col = speckle_filter_wrapper(col, speckle_filter_config)

    if terrain_normalization_config:
        col = terrain_normalization_wrapper(col, terrain_normalization_config)

    return col
