#!/usr/bin/env python3
"""
Version: v1.2
Date: 2021-04-01
Authors: Mullissa A., Vollrath A., Braun, C., Slagter B., Balling J.,
Gou Y., Gorelick N.,  Reiche J.
Description: A wrapper function to derive the Sentinel-1 ARD
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
class S1FilterConfig:
    """The structured type for configuring speckle
    filters to apply to Sentinel-1
    apply_border_noise_correction : boolean
        Apply border noise correction if True
    apply_terrain_flattening : boolean
        Apply terrain flattening if True
    apply_speckle_filtering : boolean
        Apply speckel filtering if True
    dem : string
        Digital elevation Model used for terrain corrections. See
    speckle_filter_framework : string
    speckle_filter : string
    speckle_filter_kernel_size : integer
    speckle_filter_nr_of_images : integer
    terrain_flattening_model : string
    terrain_flattening_additional_layover_shadow_buffer :  integer
    """

    apply_border_noise_correction: bool = True
    apply_terrain_flattening: bool = True
    apply_speckle_filtering: bool = True
    dem: str = "USGS/SRTMGL1_003"
    speckle_filter_framework: str = "MONO"
    speckle_filter: str = "BOXCAR"
    speckle_filter_kernel_size: int = 13
    speckle_filter_nr_of_images: int = 10
    terrain_flattening_model: str = "DIRECT"
    terrain_flattening_additional_layover_shadow_buffer: int = 0


def s1_preproc(col: ImageCollection, filter_params: S1FilterConfig):
    """
    Applies preprocessing to a collection of S1 images to return
    an analysis ready sentinel-1 data.

    Parameters
    ----------
    col : ImageCollection
        GEE image collection to be preprocessed
    filter_params : S1FilterConfig
        Parameter Dataclass that determines the data selection
        and image processing parameters.

    Raises
    ------
    ValueError
    Warning


    Returns
    -------
    ImageCollection
        A processed Sentinel-1 image collection

    """
    APPLY_BORDER_NOISE_CORRECTION = filter_params.apply_border_noise_correction
    APPLY_TERRAIN_FLATTENING = filter_params.apply_terrain_flattening
    APPLY_SPECKLE_FILTERING = filter_params.apply_speckle_filtering
    SPECKLE_FILTER_FRAMEWORK = filter_params.speckle_filter_framework
    SPECKLE_FILTER = filter_params.speckle_filter
    SPECKLE_FILTER_KERNEL_SIZE = filter_params.speckle_filter_kernel_size
    SPECKLE_FILTER_NR_OF_IMAGES = filter_params.speckle_filter_nr_of_images
    TERRAIN_FLATTENING_MODEL = filter_params.terrain_flattening_model
    DEM = filter_params.dem
    TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER = (
        filter_params.terrain_flattening_additional_layover_shadow_buffer
    )

    ###########################################
    # 1. CHECK PARAMETERS
    ###########################################

    if APPLY_BORDER_NOISE_CORRECTION is None:
        APPLY_BORDER_NOISE_CORRECTION = True
    if APPLY_TERRAIN_FLATTENING is None:
        APPLY_TERRAIN_FLATTENING = True
    if APPLY_SPECKLE_FILTERING is None:
        APPLY_SPECKLE_FILTERING = True
    if SPECKLE_FILTER_FRAMEWORK is None:
        SPECKLE_FILTER_FRAMEWORK = "MULTI BOXCAR"
    if SPECKLE_FILTER is None:
        SPECKLE_FILTER = "GAMMA MAP"
    if SPECKLE_FILTER_KERNEL_SIZE is None:
        SPECKLE_FILTER_KERNEL_SIZE = 7
    if SPECKLE_FILTER_NR_OF_IMAGES is None:
        SPECKLE_FILTER_NR_OF_IMAGES = 10
    if TERRAIN_FLATTENING_MODEL is None:
        TERRAIN_FLATTENING_MODEL = "VOLUME"
    if TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER is None:
        TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER = 0

    model_required = ["DIRECT", "VOLUME"]
    if TERRAIN_FLATTENING_MODEL not in model_required:
        raise ValueError("ERROR!!! Parameter TERRAIN_FLATTENING_MODEL not correctly defined")  # noqa: E501

    frame_needed = ["MONO", "MULTI"]
    if SPECKLE_FILTER_FRAMEWORK not in frame_needed:
        raise ValueError("ERROR!!! SPECKLE_FILTER_FRAMEWORK not correctly defined")  # noqa: E501

    format_sfilter = ["BOXCAR", "LEE", "GAMMA MAP", "REFINED LEE", "LEE SIGMA"]
    if SPECKLE_FILTER not in format_sfilter:
        raise ValueError("ERROR!!! SPECKLE_FILTER not correctly defined")

    if TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER < 0:
        raise ValueError(
            "ERROR!!! TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER not correctly defined"  # noqa: E501
        )

    if SPECKLE_FILTER_KERNEL_SIZE <= 0:
        raise ValueError("ERROR!!! SPECKLE_FILTER_KERNEL_SIZE not correctly defined")  # noqa: E501

    bands = col.first().bandNames().getInfo()
    if not [
        band
        for band in bands
        if band
        in [
            "VV",
            "VH",
        ]
    ]:
        raise Warning(
            "Filters only apply to VH and VV bands. No gee_s1_ard filters have been applied"  # noqa: E501
        )
    ###########################################
    # 2. ADDITIONAL BORDER NOISE CORRECTION
    ###########################################

    if APPLY_BORDER_NOISE_CORRECTION:
        col = col.map(bnc.f_mask_edges)
        print("Additional border noise correction is completed")  # noqa: T201
    else:
        col = col

    ########################
    # 3. SPECKLE FILTERING
    #######################

    if APPLY_SPECKLE_FILTERING:
        if SPECKLE_FILTER_FRAMEWORK == "MONO":
            col = ee.ImageCollection(
                sf.MonoTemporal_Filter(col, SPECKLE_FILTER_KERNEL_SIZE, SPECKLE_FILTER)  # noqa: E501
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
            print("Multi-temporal speckle filtering is completed")  # noqa: T201, E501

    ########################
    # 4. TERRAIN CORRECTION
    #######################

    if APPLY_TERRAIN_FLATTENING:
        col = trf.slope_correction(
            col,
            TERRAIN_FLATTENING_MODEL,
            ee.Image(DEM),
            TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER,
        )
    return col
