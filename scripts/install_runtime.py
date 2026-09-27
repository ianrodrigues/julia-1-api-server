"""Install pinned upstream Julia code without cloning Git LFS weights.

Run with the same Python interpreter used to serve the app, after requirements.txt.
The temporary download contains only package sources; weights are fetched by the
application into the persistent Hugging Face cache on first startup.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from shutil import copy2

from huggingface_hub import snapshot_download

from app.config import JULIA_REVISION


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="supersonic-julia-runtime-") as directory:
        snapshot = snapshot_download(
            repo_id="SupersonicLabs/Julia-1",
            revision=JULIA_REVISION,
            local_dir=directory,
            allow_patterns=["pyproject.toml", "julia/**", "README.md", "LICENSE*", "NOTICE*"],
        )
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-deps", snapshot],
            check=True,
        )
        documentation = Path(sys.prefix) / "share" / "doc" / "supersonic-julia"
        documentation.mkdir(parents=True, exist_ok=True)
        for source in Path(snapshot).iterdir():
            if source.is_file() and (
                source.name == "README.md" or source.name.startswith(("LICENSE", "NOTICE"))
            ):
                copy2(source, documentation / source.name)


if __name__ == "__main__":
    main()
