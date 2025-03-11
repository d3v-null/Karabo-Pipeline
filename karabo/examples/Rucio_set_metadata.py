# originally found on confluence https://confluence.skatelescope.org/download/attachments/300810226/set_metadata.py?version=1&modificationDate=1732787690635&api=v2
# referenced on this page https://confluence.skatelescope.org/display/SRCSC/CHOC-92%3A+Ingest+image+data+with+rucio-upload+and+add-metadata
# should be run in Rucio container, e.g.
# docker run -it --rm \
#     -e RUCIO_CFG_CLIENT_ACCOUNT=dev_null \
#     -e RUCIO_CFG_RUCIO_HOST='https://rucio.srcnet.skao.int' \
#     -e RUCIO_CFG_AUTH_HOST='https://rucio-auth.srcnet.skao.int' \
#     -e RUCIO_CFG_AUTH_TYPE=oidc \
#     -v $PWD:$PWD \
#     -w $PWD \
#     registry.gitlab.com/ska-telescope/src/src-dm/ska-src-dm-da-rucio-client:release-35.6.0

from os.path import basename
from json import loads
from rucio.client.didclient import DIDClient
from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument(
  "--namespace",
  type=str,
  default="testing",
  help="Namespace for Rucio.",
)
parser.add_argument(
  "visibility_path",
  type=str,
  help="Path to the visibility files.",
)
args = parser.parse_args()
with open(f"{args.visibility_path}.meta") as f:
  metadata = loads(f.read())
did_client = DIDClient()
result = did_client.set_metadata_bulk(
  scope=args.namespace,
  name=basename(args.visibility_path),
  meta=metadata['meta'],
)
if result:
  print("Metadata set successfully.")
else:
  print("Failed to set metadata.")
  exit(1)