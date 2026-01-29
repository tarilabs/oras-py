
podman build --format=oci -f Containerfile . -t quay.io/mmortari/oci-image-from-scratch-like-artifact:singlearch
podman push quay.io/mmortari/oci-image-from-scratch-like-artifact:singlearch

```
skopeo copy --multi-arch all docker://quay.io/mmortari/oci-image-from-scratch-like-artifact:singlearch oci:oras/tests/ocilayout_data/ocilayout1:latest
```