import sys
import types
from pathlib import Path

PACKAGE_DIR = (
    Path(__file__).parents[1] / "custom_components" / "weatheri_forecast"
)

# Load pure parser/model modules as a package without importing the integration's
# Home Assistant-dependent __init__.py during local unit tests.
package = types.ModuleType("weatheri_forecast")
package.__path__ = [str(PACKAGE_DIR)]
sys.modules.setdefault("weatheri_forecast", package)

