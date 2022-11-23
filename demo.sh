#!/bin/bash -eux

if ! command -v ubuntu-cloud-image-changelog &> /dev/null
then
    echo "ubuntu-cloud-image-changelog could not be found. 'sudo snap install ubuntu-cloud-image-changelog' or 'python3 -m pip install ubuntu-cloud-image-changelog' to install"
    exit
fi

if ! command -v jq &> /dev/null
then
    echo "jq could not be found. 'sudo apt install jq' to install"
    exit
fi


# Download some package version manifests to compare and generate changelog for
wget http://cloud-images.ubuntu.com/releases/jammy/release-20220420/ubuntu-22.04-server-cloudimg-amd64.manifest -O 20220420-ubuntu-22.04-server-cloudimg-amd64.manifest
wget http://cloud-images.ubuntu.com/releases/jammy/release-20221117/ubuntu-22.04-server-cloudimg-amd64.manifest -O 20221117-ubuntu-22.04-server-cloudimg-amd64.manifest

changelog_txt="20220420-20221117-ubuntu-22.04-server-cloudimg-amd64-changelog-diff.txt"
changelog_json="20220420-20221117-ubuntu-22.04-server-cloudimg-amd64-changelog-diff.json"
changelog_schema="20220420-20221117-ubuntu-22.04-server-cloudimg-amd64-changelog-diff.schema.json"
# generate the changelog for all changes between the two manifests
ubuntu-cloud-image-changelog generate --from-manifest 20220420-ubuntu-22.04-server-cloudimg-amd64.manifest \
                                      --to-manifest 20221117-ubuntu-22.04-server-cloudimg-amd64.manifest \
                                      --from-series jammy \
                                      --to-series jammy \
                                      --image-architecture amd64 \
                                      --highlight-cves \
                                      --notes "Changelog diff for Ubuntu 22.04 jammy base cloud image from serial 20220420 to 20221117" \
                                      --output-json-pretty \
                                      --output-json ${changelog_json} \
                                      | tee ${changelog_txt}

# generate the changelog JSON schema
ubuntu-cloud-image-changelog schema | tee ${changelog_schema}

# list all unique CVEs addressed by moving to this new image
jq --raw-output '.. | .cves? |select(length>0)[] | "\(.cve) \(.cve_priority)"' ${changelog_json} | sort --unique | tee "20220420-20221117-ubuntu-22.04-server-cloudimg-amd64-changelog-diff-unique-CVEs.txt"

# list all unique high priority CVEs addressed by moving to this new image
jq --raw-output '.. | .cves? |select(length>0)[] | select(.cve_priority=="high") | "\(.cve) \(.cve_priority)"' ${changelog_json} | sort --unique | tee "20220420-20221117-ubuntu-22.04-server-cloudimg-amd64-changelog-diff-unique-high-priority-CVEs.txt"

# list all unique launchpad bugs fixed by moving to this new image
jq --raw-output '.. | .launchpad_bugs_fixed? |select(length>0)[]' ${changelog_json} | sort --unique | tee "20220420-20221117-ubuntu-22.04-server-cloudimg-amd64-changelog-diff-unique-launchpad-bugs.txt"

# list all packages that were updated by moving to this new image
jq --raw-output '.summary.deb.diff[]' ${changelog_json} | sort --unique | tee "20220420-20221117-ubuntu-22.04-server-cloudimg-amd64-changelog-diff-updated-deb-packages.txt"