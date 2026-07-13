"""Pure validation and normalization helpers for the public SDK facade."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from ipaddress import ip_address, ip_network
from urllib.parse import urlparse

from .errors import SandboxConfigurationError
from .files import SandboxFile
from .types import ImageSpec, RuntimeSpec
from .volumes import SandboxVolume

RUNTIME_IMAGES = {
    "python3.13": "python:3.13-slim",
    "node24": "node:24-slim",
    "node22": "node:22-slim",
}
SANDBOX_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,63}$")


def resolve_runtime_image(runtime: RuntimeSpec, image: ImageSpec) -> ImageSpec:
    """Resolve a runtime alias into a registry image."""
    if runtime is None:
        return image
    if image is not None:
        raise SandboxConfigurationError("Pass either runtime or image, not both.")
    try:
        return RUNTIME_IMAGES[runtime]
    except KeyError as exc:
        supported = ", ".join(sorted(RUNTIME_IMAGES))
        raise SandboxConfigurationError(f"Unsupported runtime {runtime!r}. Supported runtimes: {supported}.") from exc


def normalize_sandbox_name(name: str | None) -> str | None:
    """Normalize an optional Modal sandbox name."""
    if name is None:
        return None
    if not isinstance(name, str):
        raise TypeError("sandbox name must be a string.")
    value = name.strip()
    if not value:
        raise SandboxConfigurationError("sandbox name must not be empty.")
    if not SANDBOX_NAME_RE.fullmatch(value):
        raise SandboxConfigurationError(
            "sandbox name must be shorter than 64 characters and contain only letters, numbers, dashes, periods, and underscores."
        )
    return value


def normalize_tags(tags: Mapping[str, str] | None) -> dict[str, str] | None:
    """Normalize optional Modal sandbox tags."""
    if tags is None:
        return None

    normalized: dict[str, str] = {}
    for key, value in tags.items():
        if not isinstance(key, str):
            raise TypeError("sandbox tag keys must be strings.")
        if not isinstance(value, str):
            raise TypeError("sandbox tag values must be strings.")
        normalized_key = key.strip()
        if not normalized_key:
            raise SandboxConfigurationError("sandbox tag keys must not be empty.")
        normalized[normalized_key] = value
    return normalized


def coerce_sandbox_file(file: SandboxFile | Mapping[str, object]) -> SandboxFile:
    """Normalize bulk file input into a `SandboxFile`."""
    if isinstance(file, SandboxFile):
        validate_file_mode(file.mode)
        return file
    path = file.get("path")
    content = file.get("content")
    mode = coerce_file_mode(file.get("mode"))
    if not isinstance(path, str):
        raise TypeError("Sandbox file mappings must include a string 'path'.")
    if not isinstance(content, (str, bytes)):
        raise TypeError("Sandbox file mappings must include string or bytes 'content'.")
    return SandboxFile(path=path, content=content, mode=mode)


def coerce_file_mode(mode: object) -> int | None:
    """Normalize an optional mapping file mode."""
    if mode is None:
        return None
    if not isinstance(mode, int) or isinstance(mode, bool):
        raise TypeError("Sandbox file mode must be an integer.")
    validate_file_mode(mode)
    return mode


def validate_file_mode(mode: int | None) -> None:
    """Validate an optional POSIX file mode."""
    if mode is None:
        return
    if not isinstance(mode, int) or isinstance(mode, bool):
        raise TypeError("Sandbox file mode must be an integer.")
    if mode < 0 or mode > 0o7777:
        raise SandboxConfigurationError("Sandbox file mode must be between 0o0000 and 0o7777.")


def normalize_volumes(volumes: Sequence[SandboxVolume] | None) -> tuple[SandboxVolume, ...]:
    """Normalize optional volume input into an immutable tuple."""
    if volumes is None:
        return ()
    normalized = tuple(volumes)
    for volume in normalized:
        if not isinstance(volume, SandboxVolume):
            raise TypeError("volumes must contain SandboxVolume instances.")
    return normalized


def normalize_domain_allowlist(domains: Sequence[str] | None) -> tuple[str, ...]:
    """Normalize optional outbound domain allowlist values."""
    if domains is None:
        return ()
    normalized: list[str] = []
    for domain in domains:
        if not isinstance(domain, str):
            raise TypeError("outbound_domain_allowlist must contain strings.")
        value = domain.strip()
        if not value:
            raise SandboxConfigurationError("outbound_domain_allowlist values must not be empty.")
        normalized.append(validate_domain_allowlist_value(value))
    return tuple(normalized)


def validate_domain_allowlist_value(value: str) -> str:
    """Validate one Modal outbound domain allowlist entry."""
    if any(character.isspace() for character in value):
        raise SandboxConfigurationError("outbound_domain_allowlist values must not contain whitespace.")
    if any(fragment in value for fragment in ("://", "/", "\\", ":", "@")):
        raise SandboxConfigurationError("outbound_domain_allowlist values must be hostnames, not URLs.")

    wildcard = value.startswith("*.")
    hostname = value[2:] if wildcard else value
    if not hostname or len(hostname) > 253:
        raise SandboxConfigurationError("outbound_domain_allowlist values must be valid hostnames.")
    if hostname.startswith(".") or hostname.endswith(".") or ".." in hostname:
        raise SandboxConfigurationError("outbound_domain_allowlist values must be valid hostnames.")

    try:
        ip_address(hostname)
    except ValueError:
        pass
    else:
        raise SandboxConfigurationError(
            "outbound_domain_allowlist values must be domain names; use outbound_cidr_allowlist for IP ranges."
        )

    for label in hostname.split("."):
        if not label or len(label) > 63:
            raise SandboxConfigurationError("outbound_domain_allowlist values must be valid hostnames.")
        if label.startswith("-") or label.endswith("-"):
            raise SandboxConfigurationError("outbound_domain_allowlist values must be valid hostnames.")
        if not all(character.isalnum() or character == "-" for character in label):
            raise SandboxConfigurationError("outbound_domain_allowlist values must be valid hostnames.")

    return value


def validate_cidr_value(value: str, field_name: str) -> str:
    """Validate a single CIDR allowlist entry."""
    if "/" not in value:
        raise SandboxConfigurationError(f"{field_name} values must be CIDR ranges.")
    try:
        ip_network(value, strict=False)
    except ValueError as exc:
        raise SandboxConfigurationError(f"{field_name} values must be valid CIDR ranges.") from exc
    return value


def normalize_cidr_allowlist(cidrs: Sequence[str] | None, field_name: str) -> tuple[str, ...]:
    """Normalize optional CIDR allowlist values."""
    if cidrs is None:
        return ()

    normalized: list[str] = []
    for cidr in cidrs:
        if not isinstance(cidr, str):
            raise TypeError(f"{field_name} must contain strings.")
        value = cidr.strip()
        if not value:
            raise SandboxConfigurationError(f"{field_name} values must not be empty.")
        normalized.append(validate_cidr_value(value, field_name))
    return tuple(normalized)


def validate_network_policy(
    *,
    block_network: bool,
    outbound_domain_allowlist: Sequence[str],
    outbound_cidr_allowlist: Sequence[str],
    inbound_cidr_allowlist: Sequence[str],
) -> None:
    """Validate Modal network policy combinations."""
    if block_network and (outbound_domain_allowlist or outbound_cidr_allowlist or inbound_cidr_allowlist):
        raise SandboxConfigurationError(
            "block_network cannot be combined with outbound_domain_allowlist, "
            "outbound_cidr_allowlist, or inbound_cidr_allowlist."
        )


def validate_public_http_url(value: str) -> None:
    """Validate that a source URL is public HTTP(S) without embedded credentials."""
    if not isinstance(value, str):
        raise TypeError("source URL must be a string.")
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SandboxConfigurationError("source URL must be an HTTP(S) URL.")
    if parsed.username or parsed.password:
        raise SandboxConfigurationError("source URL must not include embedded credentials.")


def validate_volume_mounts(volumes: Sequence[SandboxVolume]) -> None:
    """Validate volume mount paths before passing them to Modal."""
    seen: set[str] = set()

    def add_mount(mount_path: str) -> None:
        normalized = mount_path.rstrip("/") or "/"
        if normalized in seen:
            raise SandboxConfigurationError(f"Duplicate sandbox volume mount path: {normalized}")
        seen.add(normalized)

    for volume in volumes:
        if not volume.mount_path.startswith("/"):
            raise SandboxConfigurationError("Sandbox volume mount_path must be an absolute sandbox path.")
        add_mount(volume.mount_path)
