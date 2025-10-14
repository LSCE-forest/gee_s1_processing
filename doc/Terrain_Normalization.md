# Terrain Normalization

| Parameter                                           | Type    | Accepted Values                    | Description                                           |
| --------------------------------------------------- | ------- | ---------------------------------- | ----------------------------------------------------- |
| dem                                                 | string  | The GEE snippet of any DEM dataset | Digital Elevation Model used for terrain corrections. |
| terrain_flattening_model                            | string  | 'VOLUME', 'DIRECT'                 | The flattening model to be used.                      |
| terrain_flattening_additional_layover_shadow_buffer | integer | $i \in \mathbb{R}^+$               | Layover and shadow buffer distance.                   |

## Terrain Flattening Model

When applying a flattening model, there are two options proposed in this repo.

### DIRECT

The Direct Radiometric Terrain Normalization assumes the SAR backscatter comes mainly from surface reflections, i.e., **direct** reflections. It is suitable for bare ground, rocks, or smooth terrain.

### VOLUME

The Volume model assumes the SAR backscatter comes from volume scattering, which is notably what we get from forests and vegetation in general. The brightness is normalized assuming the radar signal is reflected through a medium rather than off a smooth surface.

In practice, I have observed that the Direct model fails to remove both bright and dark slopes, whereas the Volume model flattens the image to an even value.

## DEM

Digital Elevation Model used as a reference for terrain elevation to flatten the images. Be aware that resolution varies across DEMs, which can impact the quality of the flattened images.

## DEM Shadow Artifacts

Digital Elevation Models are prone to shadow artifacts caused by layover and foreshortening. [(ref)](https://natural-resources.canada.ca/maps-tools-publications/satellite-elevation-air-photos/radar-image-distortions)

### Layover

Layover occurs when the radar beam reaches the top of a tall feature (B) before it reaches the base (A).

![alt text](imgs/TN/layover.png)

The return signal from the top of the feature is received before the signal from the bottom. As a result, the top of the feature is displaced towards the radar from its true position on the ground and "lays over" the base of the feature (B' to A').

### Foreshortening

Foreshortening happens when the radar beam reaches the base of a tall feature tilted towards the radar (e.g., a mountain) before it reaches the top. This causes the top of the feature to appear compressed in the radar image.

![alt text](imgs/TN/foreshortening.png)

### Shadow

Both foreshortening and layover result in radar shadow. Radar shadow occurs when the radar beam cannot illuminate the ground surface. Shadows appear in the down-range dimension (i.e., towards the far range), behind vertical features or slopes with steep sides. Since the radar beam does not illuminate the surface, shadowed regions appear dark on the image because no energy is available to be backscattered.

### The Buffer

The buffer serves as a distance safety margin around the layover and shadow artifacts to ensure no pixels affected by these artifacts are included in the final image. This, however, will result in larger NaN holes in the final processed images.

## Overview

![alt text](imgs/TN/TN-demo_2.png)


![alt text](imgs/TN/TN-demo.png)

With the four configurations shown above at two different scales, we can observe the difference in performance between the Volume and Direct models. Additionally, a configuration with a layover & shadow buffer of 30 is shown to illustrate the impact of this parameter.