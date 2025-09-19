"""Test the wrapper pipeline."""

from gee_s1_processing.wrapper import (
    SpeckleFilterConfig,
    TerrainNormalizationConfig,
    get_analysis_ready_data,
)


def test_get_ard(s1_test_col):
    col = get_analysis_ready_data(
        s1_test_col, SpeckleFilterConfig(), TerrainNormalizationConfig(), True
    )
    assert (
        col.size().getInfo() == s1_test_col.size().getInfo()
    ), f"Filtered count {col.size.getInfo()} != Unfiltered count {s1_test_col.size().getInfo()}"
