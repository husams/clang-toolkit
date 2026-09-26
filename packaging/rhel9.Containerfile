# RHEL 9-compatible build/test image (Rocky Linux 9 == RHEL 9 userspace).
# podman build -f packaging/rhel9.Containerfile -t ctk-rhel9 .
# podman run --rm ctk-rhel9
FROM docker.io/rockylinux/rockylinux:9

RUN dnf -y install dnf-plugins-core epel-release \
 && dnf config-manager --set-enabled crb \
 && dnf -y install clang clang-devel llvm-devel cmake ninja-build git \
        zlib-devel libzstd-devel libxml2-devel ncurses-devel libffi-devel \
 && dnf clean all
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}" UV_PYTHON=3.14
RUN uv python install 3.14

WORKDIR /src
COPY . .
RUN rm -rf build .venv

CMD cmake --preset dev && cmake --build --preset dev && ctest --preset dev \
 && uv sync && uv run pytest
