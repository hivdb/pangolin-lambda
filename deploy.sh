#! /bin/bash

set -e

LATEST_VERSION=$(cat .latest_version)

aws lambda update-function-code \
    --region us-west-2 \
    --function-name pangolin-runner \
    --image-uri 931437602538.dkr.ecr.us-west-2.amazonaws.com/hivdb/pangolin-lambda:$LATEST_VERSION

mkdir -p local/
docker run -i --rm --volume ~/.aws:/root/.aws:ro --entrypoint python3 931437602538.dkr.ecr.us-west-2.amazonaws.com/hivdb/pangolin-lambda:$LATEST_VERSION > local/latest_version <<EOF
from pangolin import __version__ as pangolin_version
from pangolin_data import __version__ as pangodata_version
version = 'pangolin: {}; pangolin-data: {}'.format(
    pangolin_version, pangodata_version)
print(version)
EOF
aws s3 cp local/latest_version s3://pangolin-assets.hivdb.org/latest_version
