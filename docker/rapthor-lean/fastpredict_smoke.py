#!/usr/bin/env python3
"""DP3 FastPredict smoke test — extracted verbatim from rapthor-jupyter.Dockerfile.

Builds a 3-antenna measurement set with a 1 Jy point source and asserts that
DP3 actually takes the FastPredict path and writes non-zero visibilities.
Skipped on ARM, where DP3 is built ~fastpredict.
"""
import platform, subprocess, sys, tempfile
if platform.machine() in ("aarch64", "arm64"):
    print("skip FastPredict smoke on ARM")
    sys.exit(0)
import numpy as np
from casacore.tables import default_ms, table, makearrcoldesc

td = tempfile.mkdtemp()
ms, sky, out = f"{td}/s.ms", f"{td}/s.txt", f"{td}/s.out.ms"
t0, nchan, freq0, width = 5010000000.0, 4, 150e6, 1e6
default_ms(ms)
ant = table(ms + "/ANTENNA", readonly=False)
ant.addrows(3)
ant.putcol("NAME", ["A0", "A1", "A2"])
ant.putcol("POSITION", np.array(
    [[3826577.0, 461022.0, 5064892.0],
     [3826677.0, 461022.0, 5064892.0],
     [3826577.0, 461122.0, 5064892.0]]))
ant.putcol("DISH_DIAMETER", np.full(3, 25.0))
ant.putcol("MOUNT", ["ALT-AZ"] * 3)
ant.putcol("STATION", ["X"] * 3)
ant.putcol("TYPE", ["GROUND-BASED"] * 3)
ant.close()
pol = table(ms + "/POLARIZATION", readonly=False)
pol.addrows(1)
pol.putcol("NUM_CORR", np.array([4], np.int32))
pol.putcol("CORR_TYPE", np.array([[9, 10, 11, 12]], np.int32))
pol.putcol("CORR_PRODUCT", np.array([[[0, 0], [0, 1], [1, 0], [1, 1]]], np.int32))
pol.close()
spw = table(ms + "/SPECTRAL_WINDOW", readonly=False)
spw.addrows(1)
freqs = freq0 + np.arange(nchan) * width
spw.putcol("NUM_CHAN", np.array([nchan], np.int32))
spw.putcol("NAME", ["band"])
spw.putcol("CHAN_FREQ", np.array([freqs]))
spw.putcol("CHAN_WIDTH", np.array([np.full(nchan, width)]))
spw.putcol("EFFECTIVE_BW", np.array([np.full(nchan, width)]))
spw.putcol("RESOLUTION", np.array([np.full(nchan, width)]))
spw.putcol("REF_FREQUENCY", np.array([freq0]))
spw.putcol("MEAS_FREQ_REF", np.array([5], np.int32))
spw.putcol("TOTAL_BANDWIDTH", np.array([nchan * width]))
spw.putcol("NET_SIDEBAND", np.array([1], np.int32))
spw.close()
dd = table(ms + "/DATA_DESCRIPTION", readonly=False)
dd.addrows(1)
dd.putcol("SPECTRAL_WINDOW_ID", np.array([0], np.int32))
dd.putcol("POLARIZATION_ID", np.array([0], np.int32))
dd.close()
fld = table(ms + "/FIELD", readonly=False)
fld.addrows(1)
d0 = np.array([[[0.0, 0.0]]])
fld.putcol("NAME", ["field0"])
fld.putcol("PHASE_DIR", d0)
fld.putcol("DELAY_DIR", d0)
fld.putcol("REFERENCE_DIR", d0)
fld.putcol("NUM_POLY", np.array([0], np.int32))
fld.close()
obs = table(ms + "/OBSERVATION", readonly=False)
obs.addrows(1)
obs.putcol("TELESCOPE_NAME", ["OSKAR"])
obs.putcol("OBSERVER", ["smoke"])
obs.putcol("PROJECT", ["smoke"])
obs.putcol("TIME_RANGE", np.array([[t0, t0 + 1.0]]))
obs.close()
main = table(ms, readonly=False)
main.addcols(makearrcoldesc("DATA", 0 + 0j, valuetype="complex", shape=(nchan, 4)))
nbl = 3
main.addrows(nbl)
main.putcol("TIME", np.full(nbl, t0))
main.putcol("TIME_CENTROID", np.full(nbl, t0))
main.putcol("INTERVAL", np.full(nbl, 1.0))
main.putcol("EXPOSURE", np.full(nbl, 1.0))
main.putcol("ANTENNA1", np.array([0, 0, 1], np.int32))
main.putcol("ANTENNA2", np.array([1, 2, 2], np.int32))
# FastPredict checks per-antenna UVW consistency (bl 1-2 = ant2 - ant1).
main.putcol("UVW", np.array([[100.0, 0.0, 0.0], [0.0, 100.0, 0.0], [-100.0, 100.0, 0.0]]))
main.putcol("DATA", np.zeros((nbl, nchan, 4), np.complex64))
main.putcol("FLAG", np.zeros((nbl, nchan, 4), bool))
main.putcol("WEIGHT", np.ones((nbl, 4), np.float32))
main.putcol("SIGMA", np.ones((nbl, 4), np.float32))
main.close()
open(sky, "w").write(
    "FORMAT = Name, Type, Ra, Dec, I, SpectralIndex, LogarithmicSI, "
    "ReferenceFrequency, MajorAxis, MinorAxis, Orientation\n"
    "s0, POINT, 00:00:00, +00.00.00, 1.0, [0.0], false, 150e6, , ,\n"
)
log = subprocess.check_output(
    ["DP3", f"msin={ms}", f"msout={out}", "steps=[predict]",
     f"predict.sourcedb={sky}", "predict.usefastpredict=true",
     "predict.usebeammodel=false", "checkparset=1"],
    text=True,
    stderr=subprocess.STDOUT,
)
assert "FastPredict" in log, log
amp = np.abs(table(out).getcol("DATA")).max()
assert amp > 0, amp
print("DP3 FastPredict smoke OK", "max|V|", float(amp))
