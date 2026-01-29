__author__ = "Matteo Mortari"
__copyright__ = "Copyright The ORAS Authors."
__license__ = "Apache-2.0"

import json
import os

import pytest

import oras.utils as utils
from oras.utils.layout import is_oci_layout, validate_oci_layout


def test_validate_oci_layout_valid_minimal(tmp_path):
    """Test validation of valid OCI layout with minimal required fields"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory (may be empty)
    (layout_dir / "blobs").mkdir()

    # Create valid oci-layout file
    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    # Create valid index.json
    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    result = validate_oci_layout(str(layout_dir))
    assert result == str(layout_dir.resolve())


def test_validate_oci_layout_valid_with_additional_fields(tmp_path):
    """Test validation of valid OCI layout with additional fields"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    # Create oci-layout file with additional fields
    oci_layout = {"imageLayoutVersion": "1.0.0", "customField": "customValue"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    # Create index.json with additional fields
    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [],
        "annotations": {"custom": "annotation"},
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    result = validate_oci_layout(str(layout_dir))
    assert result == str(layout_dir.resolve())


def test_validate_oci_layout_rejects_non_pinned_versions(tmp_path):
    """Test validation fails for versions other than the pinned version 1.0.0"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory (shared across all tests)
    (layout_dir / "blobs").mkdir()

    # Test various versions that should be rejected (only "1.0.0" is accepted)
    invalid_versions = ["1.0", "1.1.0", "1.2.3", "1.0.0-rc1", "1.0.1"]

    for version in invalid_versions:
        oci_layout = {"imageLayoutVersion": version}
        utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

        index = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
        }
        utils.write_json(index, str(layout_dir / "index.json"))

        with pytest.raises(ValueError) as exc_info:
            validate_oci_layout(str(layout_dir))
        assert "imageLayoutVersion" in str(exc_info.value)
        assert "1.0.0" in str(exc_info.value)


def test_validate_oci_layout_nonexistent_path(tmp_path):
    """Test validation fails for non-existent path"""
    nonexistent = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_oci_layout(str(nonexistent))
    assert "does not exist" in str(exc_info.value).lower()


def test_validate_oci_layout_path_is_file(tmp_path):
    """Test validation fails when path is a file, not a directory"""
    test_file = tmp_path / "file.txt"
    test_file.write_text("not a directory")

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(test_file))
    assert "not a directory" in str(exc_info.value).lower()


def test_validate_oci_layout_missing_oci_layout_file(tmp_path):
    """Test validation fails when oci-layout file is missing"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    # Create only index.json, not oci-layout
    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    with pytest.raises(FileNotFoundError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "oci-layout" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


def test_validate_oci_layout_invalid_json_in_oci_layout(tmp_path):
    """Test validation fails when oci-layout contains invalid JSON"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    # Write invalid JSON to oci-layout
    oci_layout_file = layout_dir / "oci-layout"
    oci_layout_file.write_text("{invalid json")

    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "oci-layout" in str(exc_info.value)
    assert "not valid JSON" in str(exc_info.value)


def test_validate_oci_layout_oci_layout_not_object(tmp_path):
    """Test validation fails when oci-layout is not a JSON object"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    # Write JSON array instead of object
    oci_layout_file = layout_dir / "oci-layout"
    oci_layout_file.write_text('["not", "an", "object"]')

    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "oci-layout" in str(exc_info.value)
    assert "JSON object" in str(exc_info.value)


def test_validate_oci_layout_missing_imageLayoutVersion(tmp_path):
    """Test validation fails when imageLayoutVersion property is missing"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    # Create oci-layout without imageLayoutVersion
    oci_layout = {"someOtherField": "value"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "imageLayoutVersion" in str(exc_info.value)


def test_validate_oci_layout_wrong_version_prefix(tmp_path):
    """Test validation fails when imageLayoutVersion is not exactly '1.0.0'"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory (shared across all test iterations)
    (layout_dir / "blobs").mkdir()

    # Test various invalid versions (only "1.0.0" is accepted)
    invalid_versions = ["2.0.0", "0.1.0", "10.0.0", "version 1.0"]

    for version in invalid_versions:
        oci_layout = {"imageLayoutVersion": version}
        utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

        index = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
        }
        utils.write_json(index, str(layout_dir / "index.json"))

        with pytest.raises(ValueError) as exc_info:
            validate_oci_layout(str(layout_dir))
        assert "imageLayoutVersion" in str(exc_info.value)
        assert "1.0.0" in str(exc_info.value)


def test_validate_oci_layout_version_not_string(tmp_path):
    """Test validation fails when imageLayoutVersion is not a string"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    # Test with non-string version
    oci_layout = {"imageLayoutVersion": 1.0}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "imageLayoutVersion" in str(exc_info.value)
    assert "string" in str(exc_info.value)


def test_validate_oci_layout_missing_index_json(tmp_path):
    """Test validation fails when index.json file is missing"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    # Create only oci-layout, not index.json
    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    with pytest.raises(FileNotFoundError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "index.json" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


def test_validate_oci_layout_invalid_json_in_index(tmp_path):
    """Test validation fails when index.json contains invalid JSON"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    # Write invalid JSON to index.json
    index_file = layout_dir / "index.json"
    index_file.write_text("{invalid json")

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "index.json" in str(exc_info.value)
    assert "not valid JSON" in str(exc_info.value)


def test_validate_oci_layout_index_not_object(tmp_path):
    """Test validation fails when index.json is not a JSON object"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    # Write JSON array instead of object
    index_file = layout_dir / "index.json"
    index_file.write_text('["not", "an", "object"]')

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "index.json" in str(exc_info.value)
    assert "JSON object" in str(exc_info.value)


def test_validate_oci_layout_missing_schemaVersion(tmp_path):
    """Test validation fails when schemaVersion property is missing"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    # Create index.json without schemaVersion
    index = {"mediaType": "application/vnd.oci.image.index.v1+json"}
    utils.write_json(index, str(layout_dir / "index.json"))

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "schemaVersion" in str(exc_info.value)


def test_validate_oci_layout_wrong_schemaVersion(tmp_path):
    """Test validation fails when schemaVersion is not 2"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    # Test with wrong schemaVersion
    index = {
        "schemaVersion": 1,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "schemaVersion" in str(exc_info.value)
    assert "2" in str(exc_info.value)


def test_validate_oci_layout_missing_mediaType(tmp_path):
    """Test validation fails when mediaType property is missing"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    # Create index.json without mediaType
    index = {"schemaVersion": 2}
    utils.write_json(index, str(layout_dir / "index.json"))

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "mediaType" in str(exc_info.value)


def test_validate_oci_layout_wrong_mediaType(tmp_path):
    """Test validation fails when mediaType is incorrect"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    # Test with wrong mediaType
    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "mediaType" in str(exc_info.value)
    assert "application/vnd.oci.image.index.v1+json" in str(exc_info.value)


def test_is_oci_layout_returns_true_for_valid(tmp_path):
    """Test is_oci_layout returns True for valid layout"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    # Create blobs directory
    (layout_dir / "blobs").mkdir()

    assert is_oci_layout(str(layout_dir)) is True


def test_is_oci_layout_returns_false_for_nonexistent(tmp_path):
    """Test is_oci_layout returns False for non-existent path"""
    nonexistent = tmp_path / "does_not_exist"
    assert is_oci_layout(str(nonexistent)) is False


def test_is_oci_layout_returns_false_for_missing_files(tmp_path):
    """Test is_oci_layout returns False when required files are missing"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    # Only create oci-layout, not index.json
    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    assert is_oci_layout(str(layout_dir)) is False


def test_is_oci_layout_returns_false_for_invalid_structure(tmp_path):
    """Test is_oci_layout returns False for invalid structure"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    # Wrong schemaVersion
    index = {
        "schemaVersion": 1,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    assert is_oci_layout(str(layout_dir)) is False


def test_is_oci_layout_returns_false_for_file_path(tmp_path):
    """Test is_oci_layout returns False when path is a file"""
    test_file = tmp_path / "file.txt"
    test_file.write_text("not a directory")

    assert is_oci_layout(str(test_file)) is False


def test_validate_oci_layout_missing_blobs_directory(tmp_path):
    """Test validation fails when blobs directory is missing"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    # Don't create blobs directory

    with pytest.raises(FileNotFoundError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "blobs" in str(exc_info.value).lower()
    assert "not found" in str(exc_info.value).lower()


def test_validate_oci_layout_blobs_is_file_not_directory(tmp_path):
    """Test validation fails when blobs exists but is a file, not a directory"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    # Create blobs as a file instead of directory
    (layout_dir / "blobs").write_text("not a directory")

    with pytest.raises(ValueError) as exc_info:
        validate_oci_layout(str(layout_dir))
    assert "blobs" in str(exc_info.value).lower()
    assert "directory" in str(exc_info.value).lower()


def test_validate_oci_layout_empty_blobs_directory(tmp_path):
    """Test validation succeeds with empty blobs directory"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    # Create empty blobs directory
    (layout_dir / "blobs").mkdir()

    result = validate_oci_layout(str(layout_dir))
    assert result == str(layout_dir.resolve())


def test_validate_oci_layout_blobs_with_subdirectories(tmp_path):
    """Test validation succeeds with blobs directory containing subdirectories"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    # Create blobs directory with subdirectories (typical OCI layout structure)
    blobs_dir = layout_dir / "blobs"
    blobs_dir.mkdir()
    (blobs_dir / "sha256").mkdir()
    (blobs_dir / "sha256" / "abc123").write_text("blob content")

    result = validate_oci_layout(str(layout_dir))
    assert result == str(layout_dir.resolve())


def test_is_oci_layout_returns_false_for_missing_blobs(tmp_path):
    """Test is_oci_layout returns False when blobs directory is missing"""
    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()

    oci_layout = {"imageLayoutVersion": "1.0.0"}
    utils.write_json(oci_layout, str(layout_dir / "oci-layout"))

    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
    }
    utils.write_json(index, str(layout_dir / "index.json"))

    # Don't create blobs directory

    assert is_oci_layout(str(layout_dir)) is False
