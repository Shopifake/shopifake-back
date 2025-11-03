"""Helpers for generating Shopifake deployment lock files."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class ImageMetadata:
    """Container image details."""

    repository: str
    tag: Optional[str] = None
    digest: Optional[str] = None
    tag_prefix: Optional[str] = None

    def to_mapping(self) -> Dict[str, str]:
        """Return a serialisable mapping, skipping empty values."""

        data: Dict[str, str] = {"repository": self.repository}
        if self.tag:
            data["tag"] = self.tag
        if self.digest:
            data["digest"] = self.digest
        return data


@dataclass
class ServiceLock:
    """Lock information for a single service or infrastructure component."""

    submodule_path: str
    git_sha: str
    image: ImageMetadata
    notes: Optional[str] = None

    def to_mapping(self) -> Dict[str, object]:
        """Return a serialisable mapping for JSON/YAML export."""

        payload: Dict[str, object] = {
            "submodule_path": self.submodule_path,
            "git_sha": self.git_sha,
            "image": self.image.to_mapping(),
        }
        if self.notes:
            payload["notes"] = self.notes
        return payload


def run_git_command(args: List[str], cwd: Path) -> str:
    """Execute a git command and return the trimmed stdout."""

    process = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {process.stderr.strip()}")
    return process.stdout.strip()


def list_submodules(root: Path, scope: Iterable[str]) -> Dict[str, str]:
    """Return mapping submodule path -> commit SHA for given scope."""

    paths = list(scope)
    status = run_git_command(["submodule", "status", "--recursive", *paths], root)
    result: Dict[str, str] = {}
    for line in status.splitlines():
        if not line:
            continue
        parts = line.strip().split()
        sha = parts[0].lstrip("+-")
        submodule_path = parts[1]
        result[submodule_path] = sha
    return result


def load_image_metadata(path: Optional[Path]) -> Dict[str, ImageMetadata]:
    """Load mapping service -> image metadata from a JSON/YAML file."""

    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Image metadata file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    metadata: Dict[str, ImageMetadata] = {}
    for service, details in data.items():
        repository = details.get("repository")
        if not repository:
            raise ValueError(f"Missing repository for service '{service}'")
        metadata[service] = ImageMetadata(
            repository=repository,
            tag=details.get("tag"),
            digest=details.get("digest"),
            tag_prefix=details.get("tag_prefix"),
        )
    return metadata


def build_service_locks(
    root: Path,
    submodules_scope: Iterable[str],
    image_metadata: Dict[str, ImageMetadata],
    services_filter: Optional[List[str]],
    default_registry: str,
    default_tag_prefix: Optional[str],
) -> Dict[str, ServiceLock]:
    """Construct lock entries for each submodule."""

    service_commits = list_submodules(root, submodules_scope)
    locks: Dict[str, ServiceLock] = {}

    for path, sha in service_commits.items():
        service_name = Path(path).name
        if services_filter and service_name not in services_filter:
            continue

        image = image_metadata.get(
            service_name,
            ImageMetadata(
                repository=f"{default_registry}/{service_name}",
                tag=None,
                tag_prefix=default_tag_prefix,
            ),
        )

        # Determine final tag value
        final_tag = image.tag
        if image.tag_prefix:
            final_tag = f"{image.tag_prefix}{sha[:7]}"
        elif final_tag is None:
            final_tag = sha[:7]

        resolved_image = ImageMetadata(
            repository=image.repository,
            tag=final_tag,
            digest=image.digest,
        )

        locks[service_name] = ServiceLock(
            submodule_path=path,
            git_sha=sha,
            image=resolved_image,
            notes=None,
        )

    if services_filter:
        missing = set(services_filter) - set(locks.keys())
        if missing:
            raise ValueError(
                "Requested services missing from submodules: "
                + ", ".join(sorted(missing))
            )

    return locks


def build_lock_payload(
    root: Path,
    services_filter: Optional[List[str]],
    image_metadata: Dict[str, ImageMetadata],
    generator_id: str,
    timestamp: datetime,
    default_registry: str,
    default_tag_prefix: Optional[str],
) -> Dict[str, object]:
    """Assemble the full lock payload."""

    timestamp = timestamp.astimezone(timezone.utc)
    service_locks = build_service_locks(
        root=root,
        submodules_scope=["services", "infra"],
        image_metadata=image_metadata,
        services_filter=services_filter,
        default_registry=default_registry,
        default_tag_prefix=default_tag_prefix,
    )

    metadata = {
        "generated_at": timestamp.isoformat(),
        "generator": generator_id,
        "source_branch": run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], root),
        "commit": run_git_command(["rev-parse", "HEAD"], root),
    }

    services_payload = {
        name: lock.to_mapping()
        for name, lock in sorted(service_locks.items())
    }

    return {
        "metadata": metadata,
        "services": services_payload,
    }


def default_output_path(timestamp: datetime) -> Path:
    """Return default path for a lock file based on timestamp."""

    ts = timestamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("locks") / f"lock-{ts}.yml"


def dump_lock(payload: Dict[str, object], output: Path, force: bool) -> Path:
    """Serialise payload to JSON/YAML compatible file."""

    if output.exists() and not force:
        raise FileExistsError(f"Lock file already exists: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return output

