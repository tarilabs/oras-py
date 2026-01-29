```
podman manifest rm quay.io/mmortari/oci-image-from-scratch-like-artifact:multiarch
podman manifest create quay.io/mmortari/oci-image-from-scratch-like-artifact:multiarch
podman build --format=oci --platform linux/amd64 -f Containerfile . --manifest quay.io/mmortari/oci-image-from-scratch-like-artifact:multiarch
podman build --format=oci --platform linux/arm64 -f Containerfile . --manifest quay.io/mmortari/oci-image-from-scratch-like-artifact:multiarch
podman manifest push quay.io/mmortari/oci-image-from-scratch-like-artifact:multiarch
podman manifest rm quay.io/mmortari/oci-image-from-scratch-like-artifact:multiarch
```

and

```
skopeo copy --multi-arch all docker://quay.io/mmortari/oci-image-from-scratch-like-artifact:multiarch oci:oras/tests/ocilayout_data/ocilayout2:latest
```