"""Test that terrain normalization runs and returns image collections."""

from gee_s1_processing.wrapper import TerrainNormalizationConfig, terrain_normalization_wrapper


class TestSpeckleFilters:
    def assert_filter_runs(self, s1_test_col, palsar2_test_col, model: str):
        config = TerrainNormalizationConfig()
        config.terrain_flattening_model = model
        # S1
        config.angle_band = "angle"
        col = terrain_normalization_wrapper(s1_test_col, config)
        assert (
            col.size().getInfo() == s1_test_col.size().getInfo()
        ), f"Filtered count {col.size.getInfo()} != Unfiltered count {s1_test_col.size().getInfo()}"
        # PALSAR-2
        config.angle_band = "LIN"
        col = terrain_normalization_wrapper(palsar2_test_col, config)
        assert (
            col.size().getInfo() == palsar2_test_col.size().getInfo()
        ), f"Filtered count {col.size.getInfo()} != Unfiltered count {s1_test_col.size().getInfo()}"

    def test_direct(self, s1_test_col, palsar2_test_col):
        self.assert_filter_runs(s1_test_col, palsar2_test_col, "DIRECT")

    def test_volume(self, s1_test_col, palsar2_test_col):
        self.assert_filter_runs(s1_test_col, palsar2_test_col, "VOLUME")
