#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version: v1.2
Date: 2021-04-01
Authors: Mullissa A., Vollrath A., Braun, C., Slagter B., Balling J., Gou Y., Gorelick N.,  Reiche J.
Description: A wrapper function to derive the Sentinel-1 ARD
"""


import ee
from ee.imagecollection import ImageCollection
import border_noise_correction as bnc
import speckle_filter as sf
import terrain_flattening as trf
import helper


###########################################
# DO THE JOB
###########################################

def s1_preproc(col: ImageCollection, params: dict[str,str|int]):
    """
    Applies preprocessing to a collection of S1 images to return an analysis ready sentinel-1 data.

    Parameters
    ----------
    col : ImageColletion
        GEE image collection to be preprocessed
    params : Dictionary
        These parameters determine the data selection and image processing parameters.

    Raises
    ------
    ValueError
    Warning
        

    Returns
    -------
    ImageCollection
        A processed Sentinel-1 image collection

    """
    APPLY_BORDER_NOISE_CORRECTION = params['APPLY_BORDER_NOISE_CORRECTION']
    APPLY_TERRAIN_FLATTENING = params['APPLY_TERRAIN_FLATTENING']
    APPLY_SPECKLE_FILTERING = params['APPLY_SPECKLE_FILTERING']
    SPECKLE_FILTER_FRAMEWORK = params['SPECKLE_FILTER_FRAMEWORK']
    SPECKLE_FILTER = params['SPECKLE_FILTER']
    SPECKLE_FILTER_KERNEL_SIZE = params['SPECKLE_FILTER_KERNEL_SIZE']
    SPECKLE_FILTER_NR_OF_IMAGES = params['SPECKLE_FILTER_NR_OF_IMAGES']
    TERRAIN_FLATTENING_MODEL = params['TERRAIN_FLATTENING_MODEL']
    DEM = params['DEM']
    TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER = params['TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER']
    
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
        SPECKLE_FILTER_FRAMEWORK = 'MULTI BOXCAR'
    if SPECKLE_FILTER is None:
        SPECKLE_FILTER = 'GAMMA MAP'
    if SPECKLE_FILTER_KERNEL_SIZE is None:
        SPECKLE_FILTER_KERNEL_SIZE = 7
    if SPECKLE_FILTER_NR_OF_IMAGES is None:
        SPECKLE_FILTER_NR_OF_IMAGES = 10
    if TERRAIN_FLATTENING_MODEL is None:
        TERRAIN_FLATTENING_MODEL = 'VOLUME'
    if TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER is None:
        TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER = 0
    
    bands = col.first().bandNames().getInfo()
    if not [band for band in bands if band in ['VV', 'VH',]]:
        raise Warning("Filters only apply to VH and VV bands. No gee_s1_ard filters have been applied")
        
    model_required = ['DIRECT', 'VOLUME']
    if (TERRAIN_FLATTENING_MODEL not in model_required):
        raise ValueError("ERROR!!! Parameter TERRAIN_FLATTENING_MODEL not correctly defined")

    frame_needed = ['MONO', 'MULTI']
    if (SPECKLE_FILTER_FRAMEWORK not in frame_needed):
        raise ValueError("ERROR!!! SPECKLE_FILTER_FRAMEWORK not correctly defined")

    format_sfilter = ['BOXCAR', 'LEE', 'GAMMA MAP'
              ,'REFINED LEE', 'LEE SIGMA']
    if (SPECKLE_FILTER not in format_sfilter):
        raise ValueError("ERROR!!! SPECKLE_FILTER not correctly defined")

    if (TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER < 0):
        raise ValueError("ERROR!!! TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER not correctly defined")

    if (SPECKLE_FILTER_KERNEL_SIZE <= 0):
        raise ValueError("ERROR!!! SPECKLE_FILTER_KERNEL_SIZE not correctly defined")
    
    ###########################################
    # 2. ADDITIONAL BORDER NOISE CORRECTION
    ###########################################

    if (APPLY_BORDER_NOISE_CORRECTION):
        col = col.map(bnc.f_mask_edges)
        print('Additional border noise correction is completed')
    else:
        col = col

    ########################
    # 3. SPECKLE FILTERING
    #######################

    if (APPLY_SPECKLE_FILTERING):
        if (SPECKLE_FILTER_FRAMEWORK == 'MONO'):
            col = ee.ImageCollection(sf.MonoTemporal_Filter(col, SPECKLE_FILTER_KERNEL_SIZE, SPECKLE_FILTER))
            print('Mono-temporal speckle filtering is completed')
        else:
            col = ee.ImageCollection(sf.MultiTemporal_Filter(col, SPECKLE_FILTER_KERNEL_SIZE, SPECKLE_FILTER, SPECKLE_FILTER_NR_OF_IMAGES))
            print('Multi-temporal speckle filtering is completed')

    ########################
    # 4. TERRAIN CORRECTION
    #######################

    if (APPLY_TERRAIN_FLATTENING):
        col = (
            trf.slope_correction(
                col 
                ,TERRAIN_FLATTENING_MODEL
                ,ee.Image(DEM)
                ,TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER
        )
    )
    return col