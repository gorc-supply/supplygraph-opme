"""Portable Neo4j (no Docker): JDK 21 + Neo4j Community zip + APOC + GDS jars in .runtime/.

Used when Docker Desktop is not installed (decision recorded in docs/decisions/ADR-006).
Versions are pinned in docs/VERSIONS.md; checksums are verified for the JDK and Neo4j archives.
"""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import time
import zipfile
from pathlib import Path

import requests

NEO4J_VERSION = "2026.10.2"
GDS_VERSION = "2026.10.2"
APOC_VERSION = "2026.10.2"
JDK_API = "https://api.adoptium.net/v3/assets/latest/21/hotspot?os={os}&architecture=x64&image_type=jdk"
CONF_BLOCK = """
# --- supplygraph-opme (portable dev instance) ---
server.memory.heap.initial_size=2g
server.memory.heap.max_size=2g
server.memory.pagecache.size=1g
dbms.security.procedures.unrestricted=gds.*,apoc.*
dbms.security.procedures.allowlist=gds.*,apoc.*
db.transaction.timeout=600s
"""


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return dest
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return dest


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def install(runtime: Path) -> None:
    is_win = platform.system() == "Windows"
    dl = runtime / "downloads"
    # JDK 21 (Temurin) - checksum from the Adoptium API
    meta = requests.get(JDK_API.format(os="windows" if is_win else "linux"), timeout=60).json()[0]["binary"][
        "package"
    ]
    jdk_zip = _download(meta["link"], dl / meta["name"])
    if _sha256(jdk_zip) != meta["checksum"]:
        raise RuntimeError("JDK checksum mismatch")
    # Neo4j Community - checksum published next to the archive
    suffix = "windows.zip" if is_win else "unix.tar.gz"
    url = f"https://dist.neo4j.org/neo4j-community-{NEO4J_VERSION}-{suffix}"
    neo_arc = _download(url, dl / Path(url).name)
    expected = requests.get(url + ".sha256", timeout=60).text.split()[0]
    if _sha256(neo_arc) != expected:
        raise RuntimeError("Neo4j checksum mismatch")
    if not (runtime / "jdk").exists():
        with zipfile.ZipFile(jdk_zip) as z:
            top = z.namelist()[0].split("/")[0]
            z.extractall(runtime)
        (runtime / top).rename(runtime / "jdk")
    if not (runtime / "neo4j").exists():
        if is_win:
            with zipfile.ZipFile(neo_arc) as z:
                z.extractall(runtime)
        else:
            import tarfile

            with tarfile.open(neo_arc) as t:
                t.extractall(runtime, filter="data")
        (runtime / f"neo4j-community-{NEO4J_VERSION}").rename(runtime / "neo4j")
        plugins = runtime / "neo4j" / "plugins"
        _download(
            f"https://github.com/neo4j/graph-data-science/releases/download/{GDS_VERSION}/"
            f"neo4j-graph-data-science-{GDS_VERSION}.jar",
            plugins / f"neo4j-graph-data-science-{GDS_VERSION}.jar",
        )
        _download(
            f"https://github.com/neo4j/apoc/releases/download/{APOC_VERSION}/apoc-{APOC_VERSION}-core.jar",
            plugins / f"apoc-{APOC_VERSION}-core.jar",
        )
        conf = runtime / "neo4j" / "conf" / "neo4j.conf"
        conf.write_text(conf.read_text(encoding="utf-8") + CONF_BLOCK, encoding="utf-8")
        pwd = os.getenv("NEO4J_PASSWORD", "change-me-local")
        _admin(runtime, ["dbms", "set-initial-password", pwd])
    print(f"portable Neo4j {NEO4J_VERSION} ready in {runtime}")


def _env(runtime: Path) -> dict:
    env = dict(os.environ)
    env["JAVA_HOME"] = str(runtime / "jdk")
    env["PATH"] = str(runtime / "jdk" / "bin") + os.pathsep + env.get("PATH", "")
    return env


def _bin(runtime: Path, name: str) -> list[str]:
    b = runtime / "neo4j" / "bin"
    return [str(b / f"{name}.bat")] if platform.system() == "Windows" else [str(b / name)]


def _admin(runtime: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        _bin(runtime, "neo4j-admin") + args, env=_env(runtime), capture_output=True, text=True
    )


def start(runtime: Path) -> None:
    log = open(runtime / "neo4j-console.log", "a", encoding="utf-8")  # noqa: SIM115 - handed to the child process
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0
    proc = subprocess.Popen(
        _bin(runtime, "neo4j") + ["console"], env=_env(runtime), stdout=log, stderr=log, creationflags=flags
    )
    (runtime / "neo4j.pid").write_text(str(proc.pid))


def stop(runtime: Path) -> None:
    pid_file = runtime / "neo4j.pid"
    if platform.system() == "Windows":
        # the console runs a java child process: kill the whole tree started for this install
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | "
                f"Where-Object {{ $_.CommandLine -like '*{runtime.name}*neo4j*' }} | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }",
            ],
            capture_output=True,
        )
    elif pid_file.exists():
        subprocess.run(["kill", pid_file.read_text().strip()])
    pid_file.unlink(missing_ok=True)
    time.sleep(3)


def admin_import(runtime: Path, args: list[str]) -> subprocess.CompletedProcess:
    return _admin(runtime, ["database", "import", "full"] + args)
