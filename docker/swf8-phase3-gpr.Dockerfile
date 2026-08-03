# SWF-8 Phase-3 CHIPS → GPR plotter image
#
# Thin overlay on the prebuilt swf8-jupyter (ps_eor 1.0 / ml-gpr / torch) stack.
# Ships:
#   - /usr/local/bin/phase3-gpr-plot   (ENTRYPOINT)
#   - /opt/phase3_gpr/                (CLI + VAE fitters)
#   - ffmpeg                          (GIF stitch)
#
# Build (from Karabo-Pipeline repo root):
#   docker build -f docker/swf8-phase3-gpr.Dockerfile \
#     --build-arg BASE=ghcr.io/d3v-null/swf8-jupyter:numpy2-pass \
#     -t ghcr.io/d3v-null/swf8-jupyter:phase3-gpr .
#
# Smoke:
#   docker run --rm ghcr.io/d3v-null/swf8-jupyter:phase3-gpr --help
#   docker run --rm -v $PWD/out:/out ghcr.io/d3v-null/swf8-jupyter:phase3-gpr \
#     run --grid URL --out /out --obsid 1442001088
ARG BASE=ghcr.io/d3v-null/swf8-jupyter:numpy2-pass
FROM ${BASE}

LABEL org.opencontainers.image.title="swf8-jupyter-phase3-gpr" \
      org.opencontainers.image.description="MWA Phase-3 CHIPS → LOFAR-style GPR combined PNG + ffmpeg GIF" \
      org.opencontainers.image.source="https://github.com/d3v-null/Karabo-Pipeline" \
      org.opencontainers.image.vendor="SWF-8"

USER root
SHELL ["/bin/bash", "-lc"]

ENV DEBIAN_FRONTEND=noninteractive \
    PHASE3_FITTER_DIR=/opt/phase3_gpr/gpr_emulator \
    PYTHONPATH=/opt/phase3_gpr \
    MPLCONFIGDIR=/tmp/mpl \
    OPENBLAS_NUM_THREADS=8 \
    OMP_NUM_THREADS=8 \
    MKL_NUM_THREADS=8

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get --no-install-recommends install -y ffmpeg curl ca-certificates \
    && command -v ffmpeg && command -v curl

COPY docker/phase3_gpr /opt/phase3_gpr
RUN test -f /opt/phase3_gpr/phase3_gpr_cli.py && \
    test -f /opt/phase3_gpr/gpr_emulator/vae_z6.5_n2000_9params_2latent_v0.0.pt && \
    test -f /opt/phase3_gpr/gpr_emulator/vae_z6.8_n2000_9params_2latent_v0.0.pt && \
    test -f /opt/phase3_gpr/gpr_emulator/vae_z7.0_n2000_9params_2latent_v0.0.pt && \
    printf '%s\n' '#!/bin/bash' \
      'exec python /opt/phase3_gpr/phase3_gpr_cli.py "$@"' \
      > /usr/local/bin/phase3-gpr-plot && \
    chmod 755 /usr/local/bin/phase3-gpr-plot && \
    mkdir -p /tmp/mpl && chmod 1777 /tmp/mpl && \
    phase3-gpr-plot --help >/dev/null && \
    python -c "from ps_eor import ml_gpr, pspec; import torch; print('runtime OK', torch.__version__)"

# Default entrypoint = the CLI. Override with --entrypoint bash for a shell.
ENTRYPOINT ["phase3-gpr-plot"]
CMD ["--help"]

# Keep jovyan uid for bind-mount friendliness on shared FS; root also works.
ARG NB_UID=1000
USER ${NB_UID}
WORKDIR /tmp
