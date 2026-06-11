from __future__ import  annotations
import re
from pathlib import Path

from lumengraph import config as conf
from lumengraph.utils.logging_config import logger
from lumengraph.utils.paths import (
    OUTPUTS_DIR_NAME,
    UPLOADS_DIR_NAME,
    VIRTUAL_PATH_PREFIX,
    WORKSPACE_AGENTS_DIR_NAME,
    WORKSPACE_AGENTS_PROMPT_FILE_NAME,
    WORKSPACE_DIR_NAME
)


_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

def get_virtual_path_prefix() -> str:

    return "/" + VIRTUAL_PATH_PREFIX.strip("/")



