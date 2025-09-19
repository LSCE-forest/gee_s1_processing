import logging
import os

import ee
import pytest
from dotenv import load_dotenv
from ee.imagecollection import ImageCollection

GEE_PROJECT_ID_ENV_NAME = "GEEFETCH_GEE_PROJECT_ID"
load_dotenv()


@pytest.fixture(scope="session")
def gee_client():
    match os.getenv(GEE_PROJECT_ID_ENV_NAME):
        case None:
            pytest.fail(
                f"Did not find {GEE_PROJECT_ID_ENV_NAME} in the environment. "
                "Cannot query Google Earth Engine."
            )
            raise RuntimeError
        case _ as project_id:
            assert isinstance(project_id, str)
            ee.Initialize(project=project_id)
            return ee


@pytest.fixture(scope="session")
def s1_test_col(gee_client) -> ImageCollection:
    return (
        gee_client.ImageCollection("COPERNICUS/S1_GRD_FLOAT")
        .filterBounds(gee_client.Geometry.Point([2.3522, 48.8566]))
        .filterDate("2022-01-01", "2022-12-31")
        .filter(gee_client.Filter.eq("instrumentMode", "IW"))
    )


@pytest.fixture(scope="session")
def palsar2_test_col(gee_client) -> ImageCollection:
    return (
        gee_client.ImageCollection("JAXA/ALOS/PALSAR-2/Level2_2/ScanSAR")
        .filterBounds(gee_client.Geometry.Point([2.3522, 48.8566]))
        .filterDate("2022-01-01", "2022-12-31")
    )


# ---
# Configure logging


def pytest_configure(config):
    """Disable the loggers."""
    for logger_name in [
        "google",
        "urllib3",
        "googleapiclient",
    ]:
        logger = logging.getLogger(logger_name)
        logger.propagate = False
