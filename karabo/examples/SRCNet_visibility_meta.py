"""Example script to generate Rucio ObsCore metadata for ingestion of visibilities.

Details: https://jira.skatelescope.org/browse/LAV-402
"""

from __future__ import annotations

import os
from astropy.time import Time

from karabo.data.obscore import ObsCoreMeta
from karabo.data.src import RucioMeta
from karabo.simulation.visibility import Visibility
from karabo.util.helpers import get_rnd_str

from argparse import ArgumentParser, Namespace

def get_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        "--namespace",
        type=str,
        default="testing",
        help="Namespace for Rucio.",
    )
    parser.add_argument(
        "--lifetime",
        type=int,
        default=86400,
        help="Lifetime of the data-product in seconds.",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=None,
        help="ObsCore Collection name.",
    )
    parser.add_argument(
        "visibility_path",
        type=str,
        nargs="+",
        help="Path to the visibility files.",
    )
    return parser.parse_args()

def get_meta(vis: Visibility, args: Namespace) -> RucioMeta:
    vis_ocm = ObsCoreMeta.from_visibility(
        vis=vis,
        calibrated=False,
    )
    vis_rm = RucioMeta(
        namespace=args.namespace,  # needs to be specified by Rucio service
        name=os.path.split(vis.path)[-1],  # remove path-infos for `name`
        lifetime=args.lifetime,  # 1 day
        dataset_name=None,
        meta=vis_ocm,
    )
    # ObsCore mandatory fields
    # -> collection
    if args.collection is not None:
        vis_ocm.obs_collection = args.collection
    elif vis_ocm.instrument_name == "MWA":
        vis_ocm.obs_collection = "MRO/MWA"

    # -> obs_id
    if vis_ocm.instrument_name == "MWA":
        # mwa obs ID is nearest 8 second GPS time
        start_time = Time(vis_ocm.t_min, format="mjd").gps
        vis_ocm.obs_id = int(start_time // 8) * 8
        vis_ocm.obs_publisher_did = ObsCoreMeta.get_ivoid(
            authority='org.mwatelescope',
            path=f'/obs_id/{vis_ocm.obs_id}',
            query=None,
            fragment=None
        )
    else:
        obs_sim_id = 0  # inc/change for new simulation
        user_rnd_str = get_rnd_str(k=7, seed=os.environ.get("USER"))
        vis_ocm.obs_id = f"karabo-{user_rnd_str}-{obs_sim_id}"  # unique ID per user & simulation
        vis_ocm.obs_publisher_did = RucioMeta.get_ivoid(  # rest args are defaults
            namespace=vis_rm.namespace,
            name=vis_rm.name,
        )
    return vis_rm

def main() -> None:
    args = get_args()
    for vis_path in args.visibility_path:
        vis = Visibility(vis_path)
        vis_rm = get_meta(vis=vis, args=args)
        vis_path_meta = RucioMeta.get_meta_fname(fname=vis.path)
        _ = vis_rm.to_dict(fpath=vis_path_meta)
        print(f"Created {vis_path_meta=}")


if __name__ == "__main__":
    main()
