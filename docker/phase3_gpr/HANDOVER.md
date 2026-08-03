# Phase-3 CHIPS → GPR plotter — HPC handover

**Do not use `harbor.test`** — that registry is VM-local only.

## Image

| Where | Ref |
|-------|-----|
| Docker Hub (preferred if push succeeds) | `d3vnull0/swf8-jupyter:phase3-gpr` |
| Portable archive on this VM | `/home/ubuntu/Karabo-Pipeline/out/swf8-jupyter-phase3-gpr.tar.gz` |
| Local docker tag | `swf8-jupyter:phase3-gpr` |

Contains `phase3-gpr-plot` (ENTRYPOINT), VAE fitters under `/opt/phase3_gpr/gpr_emulator/`, `ffmpeg`, and the full `ps_eor` 1.0 / ml-gpr stack.

CLI writes one combined PNG per obsid (UV SEFD, 2D/1D PS, compact MCMC traces, GPR components, **residual+excess stitched ~170.9–197.7 MHz** with overlap cut at ~184.3 MHz), then can stitch PNGs into a GIF.

## Get the image onto the supercomputer

### A) Docker Hub pull (if published)

```bash
docker pull d3vnull0/swf8-jupyter:phase3-gpr
# or apptainer:
module load apptainer
apptainer pull $MYSOFTWARE/images/swf8-jupyter_phase3-gpr.sif \
  docker://d3vnull0/swf8-jupyter:phase3-gpr
```

### B) SCP the tarball (works with no registry)

From your laptop / login node that can reach this VM:

```bash
# dug: MYSOFTWARE=$DUGHPC_DATA/sw
scp ubuntu@<this-vm>:/home/ubuntu/Karabo-Pipeline/out/swf8-jupyter-phase3-gpr.tar.gz \
  $MYSOFTWARE/images/
```

On the HPC node (or a machine with Docker):

```bash
# Docker
gunzip -c $MYSOFTWARE/images/swf8-jupyter-phase3-gpr.tar.gz | docker load
# → Loaded image: swf8-jupyter:phase3-gpr

# Apptainer from the loaded docker daemon (on a build host with both):
apptainer build $MYSOFTWARE/images/swf8-jupyter_phase3-gpr.sif \
  docker-daemon://swf8-jupyter:phase3-gpr

# Or convert the tar without docker (apptainer ≥1.1):
apptainer build $MYSOFTWARE/images/swf8-jupyter_phase3-gpr.sif \
  docker-archive://$MYSOFTWARE/images/swf8-jupyter-phase3-gpr.tar.gz
# (gunzip first if your apptainer wants an uncompressed docker-archive)
gunzip -k $MYSOFTWARE/images/swf8-jupyter-phase3-gpr.tar.gz   # if needed
apptainer build $MYSOFTWARE/images/swf8-jupyter_phase3-gpr.sif \
  docker-archive://$MYSOFTWARE/images/swf8-jupyter-phase3-gpr.tar
```

## One-obsid smoke (Apptainer)

```bash
export PHASE3_SIF=$MYSOFTWARE/images/swf8-jupyter_phase3-gpr.sif
export PHASE3_OUT=$MYSCRATCH/phase3_gpr_out
mkdir -p "$PHASE3_OUT"

apptainer exec --cleanenv \
  --bind "$PHASE3_OUT":/out \
  --env OPENBLAS_NUM_THREADS=8 --env OMP_NUM_THREADS=8 \
  --env MPLCONFIGDIR=/tmp/mpl --env HOME=/tmp \
  "$PHASE3_SIF" \
  phase3-gpr-plot run \
    --grid https://projects.pawsey.org.au/high1.grids/grid_1442001088.ionosub_ssins_30l_src8k_300it_8s_80kHz_i1000.yy.tar.gz \
    --out /out --obsid 1442001088 \
    --n-steps 200 --n-walkers 100 \
    --work-dir /out/work_1442001088
```

≈ **25–35 min/obsid** @ 8 BLAS threads (3 redshift GPR fits × 200×100). Work dir ≈ **8–10 GB**; PNG ≈ **2.2 MB**.

## Five-obsid batch + GIF

Copy `docker/phase3_gpr/run_phase3_batch.sh` from this repo, then:

```bash
export PHASE3_SIF=$MYSOFTWARE/images/swf8-jupyter_phase3-gpr.sif
export PHASE3_OUT=$MYSCRATCH/phase3_gpr_out
# optional pre-downloaded: grid_<obsid>.tar.gz
# export PHASE3_GRIDS_DIR=$MYSCRATCH/high1.grids

bash run_phase3_batch.sh \
  1442001088 1442001384 1442001680 1442001976 1442002272
```

| Output | |
|--------|--|
| `$PHASE3_OUT/<obsid>_combined.png` | Full montage (obsid in panel titles) |
| `$PHASE3_OUT/<obsid>_combined.json` | Meta (steps, MHz span, split, elapsed) |
| `$PHASE3_OUT/phase3_obsids_combined.gif` | ffmpeg stitch |

## Slurm sketch

```bash
#!/bin/bash
#SBATCH --job-name=phase3-gpr
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --partition=work
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=04:00:00

module load apptainer
export PHASE3_SIF=$MYSOFTWARE/images/swf8-jupyter_phase3-gpr.sif
export PHASE3_OUT=$MYSCRATCH/phase3_gpr_out
export OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

bash $HOME/run_phase3_batch.sh \
  1442001088 1442001384 1442001680 1442001976 1442002272
```

## CLI

```text
phase3-gpr-plot run   --grid DIR|TAR.GZ|URL --out DIR [--obsid ID]
                      [--n-steps 200] [--n-walkers 100] [--redshift-idx 1]
phase3-gpr-plot batch OBSID… --out DIR [--grids-dir DIR]
phase3-gpr-plot gif   PNG… --out movie.gif [--hold 2.0]
```

Primary GPR panels: **z=6.8**. Residual/excess: fit **z=7.0** + **z=6.5**, hard-cut stitch on one freq axis at the overlap midpoint (~184.3 MHz). No blending — short MCMC can look discontinuous on excess; use full `--n-steps 200`.

## Rebuild (developers, this VM)

```bash
cd /home/ubuntu/Karabo-Pipeline
docker build -f docker/swf8-phase3-gpr.Dockerfile \
  --build-arg BASE=ghcr.io/d3v-null/swf8-jupyter:numpy2-pass \
  -t swf8-jupyter:phase3-gpr .
docker save swf8-jupyter:phase3-gpr | pigz -1 > out/swf8-jupyter-phase3-gpr.tar.gz
# public publish (needs credentials with push rights):
docker tag swf8-jupyter:phase3-gpr d3vnull0/swf8-jupyter:phase3-gpr
docker push d3vnull0/swf8-jupyter:phase3-gpr
```
