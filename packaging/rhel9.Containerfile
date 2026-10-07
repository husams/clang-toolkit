# RHEL 9-compatible build/test image (Rocky Linux 9 == RHEL 9 userspace).
# podman build -f packaging/rhel9.Containerfile -t ctk-rhel9 .
# podman run --rm --network=none ctk-rhel9
FROM docker.io/rockylinux/rockylinux:9

COPY scripts/build-rhel9.sh /tmp/ctk-dependencies/scripts/build-rhel9.sh
RUN DEPS_ONLY=1 bash /tmp/ctk-dependencies/scripts/build-rhel9.sh \
 && dnf clean all
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /src
COPY . .
# Populate Python dependencies while building the image, before offline validation.
RUN rm -rf build .venv && uv sync
ENV UV_OFFLINE=1

CMD ["bash", "-c", "SKIP_DEPS=1 BUILD_DIR=/src/build/dev bash scripts/build-rhel9.sh"]
