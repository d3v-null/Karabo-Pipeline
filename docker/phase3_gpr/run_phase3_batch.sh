#!/usr/bin/env bash
# Slurm / interactive helper for phase3-gpr-plot on a supercomputer.
#
# Expects either:
#   - Apptainer/Singularity SIF from ghcr.io/d3v-null/swf8-jupyter:phase3-gpr
#   - or Docker (rare on HPC)
#
# Example (Setonix / Pawsey-style):
#   export PHASE3_SIF=$MYSOFTWARE/images/swf8-jupyter_phase3-gpr.sif
#   export PHASE3_OUT=$MYSCRATCH/phase3_gpr_out
#   bash docker/phase3_gpr/run_phase3_batch.sh \
#     1442001088 1442001384 1442001680 1442001976 1442002272
set -euo pipefail

IMAGE="${PHASE3_IMAGE:-d3vnull0/swf8-jupyter:phase3-gpr}"
SIF="${PHASE3_SIF:-}"
OUT="${PHASE3_OUT:-${PWD}/phase3_gpr_out}"
GRIDS_DIR="${PHASE3_GRIDS_DIR:-}"
N_STEPS="${PHASE3_GPR_STEPS:-200}"
N_WALKERS="${PHASE3_GPR_WALKERS:-100}"
HOLD="${PHASE3_GIF_HOLD:-2.0}"
URL_TMPL="${PHASE3_URL_TEMPLATE:-https://projects.pawsey.org.au/high1.grids/grid_{obsid}.ionosub_ssins_30l_src8k_300it_8s_80kHz_i1000.yy.tar.gz}"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 OBSID [OBSID ...]" >&2
  exit 2
fi

mkdir -p "${OUT}"
OBSIDS=("$@")

run_cli() {
  # args after -- are forwarded to phase3-gpr-plot
  if [[ -n "${SIF}" ]]; then
    if ! command -v apptainer >/dev/null 2>&1 && ! command -v singularity >/dev/null 2>&1; then
      echo "PHASE3_SIF set but neither apptainer nor singularity found" >&2
      exit 1
    fi
    local rt=apptainer
    command -v apptainer >/dev/null 2>&1 || rt=singularity
    "${rt}" exec --cleanenv \
      --bind "${OUT}:/out" \
      ${GRIDS_DIR:+--bind "${GRIDS_DIR}:/grids"} \
      --env OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-8}" \
      --env OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}" \
      --env MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}" \
      --env MPLCONFIGDIR=/tmp/mpl \
      --env HOME=/tmp \
      "${SIF}" \
      phase3-gpr-plot "$@"
  else
    docker run --rm --user "$(id -u):$(id -g)" \
      -v "${OUT}:/out" \
      ${GRIDS_DIR:+-v "${GRIDS_DIR}:/grids"} \
      -e OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-8}" \
      -e OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}" \
      -e MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}" \
      -e MPLCONFIGDIR=/tmp/mpl \
      -e HOME=/tmp \
      "${IMAGE}" \
      "$@"
  fi
}

FRAMES=()
for o in "${OBSIDS[@]}"; do
  echo "==== ${o} $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="
  src="${URL_TMPL//\{obsid\}/${o}}"
  if [[ -n "${GRIDS_DIR}" && -f "${GRIDS_DIR}/grid_${o}.tar.gz" ]]; then
    src="/grids/grid_${o}.tar.gz"
  fi
  run_cli run \
    --grid "${src}" \
    --out /out \
    --obsid "${o}" \
    --n-steps "${N_STEPS}" \
    --n-walkers "${N_WALKERS}" \
    --work-dir "/out/work_${o}"
  FRAMES+=("/out/${o}_combined.png")
done

echo "==== stitch GIF $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="
run_cli gif "${FRAMES[@]}" --out /out/phase3_obsids_combined.gif --hold "${HOLD}"
echo "done → ${OUT}/phase3_obsids_combined.gif"
ls -lh "${OUT}"/*_combined.png "${OUT}"/phase3_obsids_combined.gif 2>/dev/null || true
