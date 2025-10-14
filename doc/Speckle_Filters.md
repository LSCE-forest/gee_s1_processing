# Speckle Filter Configurations

The gee_s1_ard filters are taken from this [gee_s1_ard fork](https://github.com/LSCE-forest/gee_s1_processing/) repository. See related paper [here](https://www.mdpi.com/2072-4292/13/10/1954).

| Parameter                   | Type    | Accepted Values                                          | Description                                                                                                                                     |
| --------------------------- | ------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| speckle_filter_framework    | string  | 'MONO', 'MULTI'                                          | Whether the speckle filter will be applied on a single image or to a temporal stack of images neighboring each image in the filtered collection |
| speckle_filter_nr_of_images | integer | $i\in\mathbb{N}^+$                                       | The number of images to be used by the multi-temporal speckle filter framework                                                                  |
| speckle_filter              | string  | 'BOXCAR', 'LEE', 'REFINED LEE', 'LEE SIGMA', 'GAMMA MAP' | The name of the speckle filter to use                                                                                                           |
| speckle_filter_kernel_size  | integer | {$i\in\mathbb{N}^+ \mid i//2\neq0$}                      | Size of the kernel that will be used to convolve the images                                                                                     |

## Speckle Filter Framework

SAR images are prone to speckle noise. It is similar to salt-and-pepper noise but is multiplicative, meaning that for a signal $S$, we have

$S = \large x \odot s_n$

* $\large x$: the true backscatter
* $\large s_n$: the speckle noise

The Equivalent Number of Looks (ENL) describes the degree of averaging applied to SAR measurements during data formation and postprocessing and is an indirect measure of speckle reduction (e.g., due to multilooking or speckle filtering).

In the case of linearly scaled backscatter data, ENL can be calculated as:

$ENL = \huge \frac{\mu^2}{\sigma^2}$

[(source)](https://s1-nrb.readthedocs.io/en/v1.6.0/general/enl.html)

### MONO

The MONO framework simply applies the *speckle_filter* to the individual images of the collection.

### MULTI

The MULTI framework applies a weighted average of the *speckle_filter* across images of a time series to each image of the collection.

Let:

* $\large n$ = *speckle_filter_nr_of_images*
* $\large z_{target}$ = the image that is going to be filtered with the multi-temporal framework
* $\large \hat{z}_{target}$ = the image that is going to be filtered with the multi-temporal framework after being spatially filtered (this is the output of the MONO framework)
* $\large z_{i}$ = original images selected according to *speckle_filter_nr_of_images*. They are exclusively selected with older timestamps than $\large z_{target}$, except in the edge case where there are not enough past images to satisfy *speckle_filter_nr_of_images*. This ensures that in time series applications, there is no risk of **data leakage** from the future into the training data via filters.
* $\large \hat{z}_{i}$ = spatially filtered image (inner)
* $\large r_{i}$ = $\large\frac{z_{i}}{\hat{z}_{i}}$, the ratio band. For a perfect filter, this ratio would be equal to $s_n$, the speckle noise.

The multi-temporal filtered output is:


$\huge \frac{\hat{z}_{target}}{n} \ast \sum_{i=0}^n r_{i}$


### MONO vs MULTI

|       | PROS                          | CONS                                                                                                                                                                                    |
| ----- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MONO  | Faster preprocessing          | Greater loss of detail through blurring                                                                                                                                                 |
| MULTI | Better conservation of detail | Slower preprocessing, **seasonal changes** should be considered when defining the temporal windows, **GEE memory limit exceeded exception** may occur when a tile size is set too high. |


### Geefetch Composition Methods

Before adding any of these filters to your [Geefetch](https://github.com/gbelouze/geefetch) configuration files, please note that if the chosen **Composition Method** in the configuration is anything else than **TIMESERIES** or **MOSAIC**, the **speckle filter might not be necessary**. For large enough temporal AOIs, a **MEDIAN** composition method, for instance, will already generate an efficiant de-speckeled median of all images in that time frame.

As a result, the speckle filters here might add more processing overhead than value to your data.

![alt_text](imgs/SpeckleFilters/Median_v_timeSeries.png)

As shown above, composition over a time window handles most of the noise. Consequently, for **non-TIMESERIES** compositions, we mostly observe the negative blurring effect of the filters.

On the other hand, when selecting individual images, the need for speckle filters seems more justified.

The following sections detail the five proposed filters. All images shown will be on individual SAR images (as opposed to composition over a period of time).

## Kernel Size
The kernel size used by the filters is conventionnaly set between 3x3 and 7x7. The trade-off being higher noise reduction and greater loss of detail as the kernel grows.

## Speckle Filters

### BOXCAR

BOXCAR is a basic moving average filter. Its kernel is filled with values equal to $\frac{1}{n^2}$, where $n$ is the size of the kernel.

It can reduce speckle as it smooths the image, but it acts indiscriminately, smoothing details as much as it does speckle.

![alt_text](imgs/SpeckleFilters/boxcar_mono.png)

![alt_text](imgs/SpeckleFilters/boxcar_multi.png)

### LEE

The Lee filters are **adaptive and smooth images according to the local variability** (within the kernel). This leads to better conservation of details.

* Homogeneous regions: Low variance $\Rightarrow$ output $\simeq$ local mean
* Heterogeneous regions: High variance $\Rightarrow$ output $\simeq$ unfiltered pixels

The filter applies an adaptive weighted average:

$\large s_{filtered} = (1-b)\hat{z} + b z$

* $\large z$: unfiltered pixel value
* $\large \hat{z}$: local mean in the pixel neighborhood
* $\large b \in [0,1]$: adaptive weight defined by $\large b = \frac{\sigma_x^2}{\sigma_z^2}$
* $\large \sigma_z^2$: Local variance of the original image
* $\large \sigma_x^2$: Estimated local variance of $\large x$, $\large \sigma_x^2 = \frac{\sigma_z^2 - \hat{z}^2 \eta^2}{1 + \eta^2}$
* $\large \eta = \frac{1}{\sqrt{ENL}}$


As noted in [this paper](https://linkinghub.elsevier.com/retrieve/pii/S2352938519302186), the Lee filter with a 3x3 kernel provides the best balance between feature preservation and smoothing.

![alt_text](imgs/SpeckleFilters/lee_mono.png)
![alt_text](imgs/SpeckleFilters/lee_multi.png)
The impact of **multi-temporal** filtering is often difficult to observe without toggling between layers in QGIS.

### REFINED LEE

This filter (which is not included in the paper referenced above) iterates upon the Lee filter and adds two major features.

#### Directional Filtering

While the standard Lee filter applies its adaptive filter indiscriminately of edge direction, the Refined Lee filter estimates a gradient to detect dominant edge directions for each pixel.

The local mean and variances are then computed according to the detected direction rather than the whole neighborhood.

#### Adaptive $ENL$ Estimation

The local noise variance is estimated within the kernel, allowing an adaptive estimation of $ENL$, whereas the Lee filter assumes $ENL = 5$.

#### Weighted Sum

Like the Lee filter, the filtered image is the result of a **weighted sum**, based on the directional mean and variance with the same weight $b$.

#### Nota Bene

The Refined Lee filter does not use the *speckle_filter_kernel_size* argument. It applies 3x3 and 7x7 kernels to determine edge directions and perform adaptive filtering.

![alt_text](imgs/SpeckleFilters/refined_lee.png)
### LEE SIGMA

Similar to Refined Lee, Lee Sigma iterates on the Lee filter with two major additions.

#### Strong Backscatter Retention

Before any filtering, the strongest scatterers are identified as pixels with intensity in the **98th percentile**, denoted as $\large Z_{98}$. A 3x3 window around these pixels is then examined to determine whether the number of neighboring pixels in $\large Z_{98}$ meets a threshold $T_K$.

This allows isolation of man-made structures with high backscatter values, enabling them to bypass the MMSE filter.

#### Application of MMSE within Sigma Range

Using the lookup table from [Improved sigma filter for speckle filtering of SAR imagery](https://ieeexplore.ieee.org/document/4689358), a mask is created to apply the standard Lee MMSE filter only to pixels within the Sigma range.

The Sigma range improves upon previous implementations that assumed intensity PDFs were Gaussian. It defines an empirical lookup table of Sigma ranges based on observations of speckle distributions (as described in the referenced paper).

The pixel retention logic makes this filter very efficient at reducing noise around man-made structures while preserving their details. It may not be as effective for speckle noise filtering in forests.

![alt_text](imgs/SpeckleFilters/sigma_lee_mono.png)
![alt_text](imgs/SpeckleFilters/sigma_lee_multi.png)

### GAMMA MAP

Gamma Map generates smooth gradients that can erase all features from the AOI. This [issue](https://github.com/LSCE-forest/gee_s1_processing/issues/2) describes the problem.

