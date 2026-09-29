from pathlib import Path

import pytest
import yaml

from src.catalog.index import CatalogIndex
from src.catalog.parse import load_catalogs
from src.normalize.major import MajorParser

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def catalogs():
    return load_catalogs(ROOT / "catalogs" / "source")


@pytest.fixture(scope="session")
def index(catalogs):
    aliases = yaml.safe_load((ROOT / "config" / "majors-alias.yaml").read_text(encoding="utf-8"))
    return CatalogIndex(catalogs, aliases)


@pytest.fixture(scope="session")
def parser(index):
    return MajorParser(index)
