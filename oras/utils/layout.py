__author__ = "Matteo Mortari"
__copyright__ = "Copyright The ORAS Authors."
__license__ = "Apache-2.0"

import json
import pathlib

import oras.defaults

# Constants for OCI layout validation
OCI_LAYOUT_FILE = "oci-layout"
OCI_LAYOUT_VERSION_PIN = "1.0.0"
OCI_INDEX_MEDIA_TYPE = "application/vnd.oci.image.index.v1+json"
OCI_INDEX_SCHEMA_VERSION = 2
OCI_BLOBS_DIR = "blobs"


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

    # Validate mediaType
    if "mediaType" not in index_data:
        raise ValueError(
            f"File '{oras.defaults.oci_image_index_file}' must contain 'mediaType' property"
        )
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
