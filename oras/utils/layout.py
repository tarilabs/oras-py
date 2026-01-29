__author__ = "Matteo Mortari"
__copyright__ = "Copyright The ORAS Authors."
__license__ = "Apache-2.0"

import json
import pathlib
from typing import TYPE_CHECKING

import requests

import oras.defaults
from oras.logger import logger
from oras.utils.fileio import read_json

if TYPE_CHECKING:
    from oras.provider import Registry

# Constants for OCI layout validation
OCI_LAYOUT_FILE = "oci-layout"
OCI_LAYOUT_VERSION_PIN = "1.0.0"
OCI_INDEX_MEDIA_TYPE = "application/vnd.oci.image.index.v1+json"
OCI_MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
OCI_INDEX_SCHEMA_VERSION = 2
OCI_BLOBS_DIR = "blobs"
OCI_REF_NAME_ANNOTATION = "org.opencontainers.image.ref.name"


def _validate_oci_layout_file(layout_dir: pathlib.Path) -> None:
    """
    Validate the oci-layout file in an OCI layout directory.

    :param layout_dir: path to the OCI layout directory
    :type layout_dir: pathlib.Path
    :raises FileNotFoundError: if oci-layout file doesn't exist
    :raises ValueError: if file content is invalid
    """
    layout_file = layout_dir / OCI_LAYOUT_FILE

    # Check file exists
    if not layout_file.exists():
        raise FileNotFoundError(
            f"Required file '{OCI_LAYOUT_FILE}' not found in {layout_dir}"
        )

    # Parse JSON
    try:
        with open(layout_file, "r") as f:
            layout_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"File '{OCI_LAYOUT_FILE}' is not valid JSON: {e}")

    # Validate structure
    if not isinstance(layout_data, dict):
        raise ValueError(f"File '{OCI_LAYOUT_FILE}' must contain a JSON object")

    # Validate imageLayoutVersion exists
    if "imageLayoutVersion" not in layout_data:
        raise ValueError(
            f"File '{OCI_LAYOUT_FILE}' must contain 'imageLayoutVersion' property"
        )

    # > (...) version at the time changes to the layout are made, and will pin a given version until changes to the image layout are required.
    # At this time, that means pinning `1.0.0`.
    version = layout_data["imageLayoutVersion"]
    if not isinstance(version, str) or not version == OCI_LAYOUT_VERSION_PIN:
        raise ValueError(
            f"imageLayoutVersion must be a string starting with '{OCI_LAYOUT_VERSION_PIN}', got: {version}"
        )


def _validate_index_json(layout_dir: pathlib.Path) -> None:
    """
    Validate the index.json file in an OCI layout directory.

    :param layout_dir: path to the OCI layout directory
    :type layout_dir: pathlib.Path
    :raises FileNotFoundError: if index.json doesn't exist
    :raises ValueError: if file content is invalid
    """
    index_file = layout_dir / oras.defaults.oci_image_index_file

    # Check file exists
    if not index_file.exists():
        raise FileNotFoundError(
            f"Required file '{oras.defaults.oci_image_index_file}' not found in {layout_dir}"
        )

    # Parse JSON
    try:
        with open(index_file, "r") as f:
            index_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"File '{oras.defaults.oci_image_index_file}' is not valid JSON: {e}"
        )

    # Validate structure
    if not isinstance(index_data, dict):
        raise ValueError(
            f"File '{oras.defaults.oci_image_index_file}' must contain a JSON object"
        )

    # Validate schemaVersion
    if "schemaVersion" not in index_data:
        raise ValueError(
            f"File '{oras.defaults.oci_image_index_file}' must contain 'schemaVersion' property"
        )
    if index_data["schemaVersion"] != OCI_INDEX_SCHEMA_VERSION:
        raise ValueError(
            f"schemaVersion must be {OCI_INDEX_SCHEMA_VERSION}, got: {index_data['schemaVersion']}"
        )

    # Validate mediaType (optional, but must be correct when present)
    # Per OCI spec: SHOULD be used, and when used MUST be application/vnd.oci.image.index.v1+json
    if "mediaType" in index_data:
        if index_data["mediaType"] != OCI_INDEX_MEDIA_TYPE:
            raise ValueError(
                f"mediaType must be '{OCI_INDEX_MEDIA_TYPE}', got: {index_data['mediaType']}"
            )


def _validate_blobs_directory(layout_dir: pathlib.Path) -> None:
    """
    Validate the blobs directory in an OCI layout directory.

    :param layout_dir: path to the OCI layout directory
    :type layout_dir: pathlib.Path
    :raises FileNotFoundError: if blobs directory doesn't exist
    :raises ValueError: if blobs exists but is not a directory
    """
    blobs_dir = layout_dir / OCI_BLOBS_DIR

    # Check directory exists
    if not blobs_dir.exists():
        raise FileNotFoundError(
            f"Required directory '{OCI_BLOBS_DIR}' not found in {layout_dir}"
        )

    # Validate it's a directory (not a file)
    if not blobs_dir.is_dir():
        raise ValueError(
            f"'{OCI_BLOBS_DIR}' must be a directory, not a file in {layout_dir}"
        )


def validate_oci_layout(path: str) -> str:
    """
    Validate that a path is a valid OCI layout directory.

    Checks that the directory contains valid 'oci-layout' and 'index.json' files,
    and a 'blobs' directory according to the OCI Image Layout Specification.

    :param path: path to validate as OCI layout
    :type path: str
    :return: absolute path to the validated OCI layout directory
    :rtype: str
    :raises FileNotFoundError: if path or required files/directories don't exist
    :raises ValueError: if path is not a directory or validation fails
    """
    # Normalize path
    layout_path = pathlib.Path(path).expanduser().resolve()

    # Validate path exists
    if not layout_path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    # Validate path is a directory
    if not layout_path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    # Validate blobs directory
    _validate_blobs_directory(layout_path)

    # Validate oci-layout file
    _validate_oci_layout_file(layout_path)

    # Validate index.json file
    _validate_index_json(layout_path)

    # Return absolute path
    return str(layout_path)


def is_oci_layout(path: str) -> bool:
    """
    Check if a path is a valid OCI layout directory.

    :param path: path to check
    :type path: str
    :return: True if path is a valid OCI layout, False otherwise
    :rtype: bool
    """
    try:
        validate_oci_layout(path)
        return True
    except (FileNotFoundError, ValueError, OSError):
        return False


def get_ordered_blobs(layout_path: str, tag: str = "latest") -> list[str]:
    """
    Traverse an OCI layout and collect blob digests in dependency order for pushing.

    Returns digests with algorithm prefix (e.g., "sha256:...") in the order:
    - Layer blobs (bottom to top)
    - Config blob
    - Manifest blob(s)
    - Index blob (if multi-arch)

    :param layout_path: path to OCI layout directory
    :type layout_path: str
    :param tag: tag to look up in annotations (default: "latest")
    :type tag: str
    :return: list of digest strings including algorithm prefix
    :rtype: list[str]
    :raises FileNotFoundError: if layout, index, or blob files don't exist
    :raises ValueError: if tag annotation not found or invalid structure
    """
    # Validate and normalize path
    layout_path = validate_oci_layout(layout_path)
    layout_dir = pathlib.Path(layout_path)

    # Read index.json
    index_file = layout_dir / oras.defaults.oci_image_index_file
    index_data = read_json(str(index_file))

    # Find manifest with matching tag annotation
    target_digest = None
    for manifest_entry in index_data.get("manifests", []):
        annotations = manifest_entry.get("annotations", {})
        if annotations.get(OCI_REF_NAME_ANNOTATION) == tag:
            target_digest = manifest_entry["digest"]
            break

    if not target_digest:
        raise ValueError(f"Tag '{tag}' not found in index")

    # Collect blobs in dependency order
    collected = []
    _process_manifest(layout_dir, target_digest, collected)
    return collected


def _process_manifest(
    layout_dir: pathlib.Path, digest: str, collected: list[str]
) -> None:
    """
    Recursively process a manifest blob and collect dependencies.

    :param layout_dir: path to OCI layout directory
    :type layout_dir: pathlib.Path
    :param digest: digest of manifest to process (with algorithm prefix)
    :type digest: str
    :param collected: list to accumulate digests (mutated in place)
    :type collected: list[str]
    :raises FileNotFoundError: if blob file doesn't exist
    :raises ValueError: if manifest structure is invalid
    """
    # Construct blob path: blobs/sha256/abc123...
    algorithm, hash_value = digest.split(":", 1)
    blob_path = layout_dir / OCI_BLOBS_DIR / algorithm / hash_value

    if not blob_path.exists():
        raise FileNotFoundError(f"Blob not found: {blob_path}")

    # Read manifest blob
    manifest = read_json(str(blob_path))
    media_type = manifest.get("mediaType", "")

    if media_type == OCI_MANIFEST_MEDIA_TYPE:
        # Image manifest: layers -> config -> manifest
        for layer in manifest.get("layers", []):
            layer_digest = layer["digest"]
            if layer_digest not in collected:
                collected.append(layer_digest)

        config_digest = manifest.get("config", {}).get("digest")
        if config_digest and config_digest not in collected:
            collected.append(config_digest)

        if digest not in collected:
            collected.append(digest)

    elif media_type == OCI_INDEX_MEDIA_TYPE:
        # Image index: recurse on sub-manifests, then add index
        for sub_manifest in manifest.get("manifests", []):
            _process_manifest(layout_dir, sub_manifest["digest"], collected)

        if digest not in collected:
            collected.append(digest)

    else:
        raise ValueError(
            f"Unsupported manifest mediaType: {media_type}. "
            f"Expected '{OCI_MANIFEST_MEDIA_TYPE}' or '{OCI_INDEX_MEDIA_TYPE}'"
        )


def _digest_to_blob_path(layout_dir: pathlib.Path, digest: str) -> pathlib.Path:
    """
    Convert digest string to blob file path in OCI layout.

    :param layout_dir: path to OCI layout directory
    :type layout_dir: pathlib.Path
    :param digest: digest with algorithm prefix (e.g., "sha256:abc123...")
    :type digest: str
    :return: path to blob file (e.g., layout_dir/blobs/sha256/abc123...)
    :rtype: pathlib.Path
    """
    algorithm, hash_value = digest.split(":", 1)
    return layout_dir / OCI_BLOBS_DIR / algorithm / hash_value


def _create_layer_dict(blob_path: pathlib.Path, digest: str, media_type: str) -> dict:
    """
    Create a layer dict for upload_blob from blob file.

    :param blob_path: path to blob file
    :type blob_path: pathlib.Path
    :param digest: digest with algorithm prefix
    :type digest: str
    :param media_type: media type for the blob
    :type media_type: str
    :return: layer dict with digest, size, mediaType
    :rtype: dict
    """
    size = blob_path.stat().st_size
    return {
        "digest": digest,
        "size": size,
        "mediaType": media_type or oras.defaults.unknown_config_media_type,
    }


def push_from_layout(
    provider: "Registry",
    target: str,
    layout_path: str,
    tag: str = "latest",
    do_chunked: bool = False,
    chunk_size: int = oras.defaults.default_chunksize,
) -> requests.Response:
    """
    Push an OCI layout to a remote registry.

    :param provider: Registry provider instance for uploading
    :type provider: oras.provider.Registry
    :param target: target registry/repository with destination tag (e.g., "ghcr.io/user/repo:v1.0")
    :type target: str
    :param layout_path: path to OCI layout directory
    :type layout_path: str
    :param tag: source tag to read from the layout's index.json annotations (default: "latest")
    :type tag: str
    :param do_chunked: use chunked upload for large blobs
    :type do_chunked: bool
    :param chunk_size: chunk size for chunked uploads
    :type chunk_size: int
    :return: response from the final manifest upload
    :rtype: requests.Response
    :raises FileNotFoundError: if layout or blobs don't exist
    :raises ValueError: if layout is invalid or tag not found
    """
    # Validate and normalize path
    layout_path = validate_oci_layout(layout_path)
    layout_dir = pathlib.Path(layout_path)

    # Parse container from target
    container = provider.get_container(target)

    # Get ordered blobs (layers -> config -> manifest -> index)
    ordered_blobs = get_ordered_blobs(layout_path, tag)

    logger.debug(f"Pushing {len(ordered_blobs)} blobs from OCI layout to {target}")

    # Upload each blob in dependency order
    last_response = None

    for digest in ordered_blobs:
        # Convert digest to file path
        blob_path = _digest_to_blob_path(layout_dir, digest)

        # Verify blob exists
        if not blob_path.exists():
            raise FileNotFoundError(f"Blob not found: {blob_path}")

        # Read blob to check if it's JSON and get mediaType
        try:
            blob_data = read_json(str(blob_path))
            media_type = blob_data.get("mediaType", "")

            # Check if it's a manifest or index
            if media_type in [OCI_MANIFEST_MEDIA_TYPE, OCI_INDEX_MEDIA_TYPE]:
                # Upload as manifest
                logger.debug(f"Uploading manifest/index: {digest}")
                response = provider.upload_manifest(blob_data, container)
            else:
                # It's JSON but not a manifest (likely a config)
                # Upload as blob with layer dict
                logger.debug(f"Uploading config blob: {digest}")
                layer = _create_layer_dict(blob_path, digest, media_type)
                response = provider.upload_blob(
                    str(blob_path), container, layer, do_chunked, chunk_size
                )
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Not JSON - must be a binary layer blob
            logger.debug(f"Uploading layer blob: {digest}")
            layer = _create_layer_dict(
                blob_path, digest, oras.defaults.default_blob_media_type
            )
            response = provider.upload_blob(
                str(blob_path), container, layer, do_chunked, chunk_size
            )

        # Check response status
        provider._check_200_response(response)
        last_response = response

    logger.debug(f"Successfully pushed {len(ordered_blobs)} blobs to {target}")
    return last_response
