"""Test that filters run and return image collections."""

from gee_s1_processing.wrapper import SpeckleFilterConfig, speckle_filter_wrapper


class TestSpeckleFilters:
    def assert_filter_runs(self, s1_test_col, filter: str):
        config = SpeckleFilterConfig()
        config.speckle_filter = filter
        # Mono
        config.speckle_filter_framework = "MONO"
        col = speckle_filter_wrapper(s1_test_col, config)
        assert (
            col.size().getInfo() == s1_test_col.size().getInfo()
        ), f"Filtered count {col.size.getInfo()} != Unfiltered count {s1_test_col.size().getInfo()}"
        # Multi
        config.speckle_filter_framework = "MULTI"
        config.speckle_filter_nr_of_images = 3
        col = speckle_filter_wrapper(s1_test_col, config)
        assert (
            col.size().getInfo() == s1_test_col.size().getInfo()
        ), f"Filtered count {col.size.getInfo()} != Unfiltered count {s1_test_col.size().getInfo()}"

    def test_box_car(self, s1_test_col):
        self.assert_filter_runs(s1_test_col, filter="BOXCAR")

    def test_lee(self, s1_test_col):
        self.assert_filter_runs(s1_test_col, filter="LEE")

    def test_lee_sigma(self, s1_test_col):
        self.assert_filter_runs(s1_test_col, filter="LEE SIGMA")

    def test_refined_lee(self, s1_test_col):
        self.assert_filter_runs(s1_test_col, filter="REFINED LEE")

    def test_gamma_map(self, s1_test_col):
        self.assert_filter_runs(s1_test_col, filter="GAMMA MAP")
