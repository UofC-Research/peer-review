#!/bin/bash
#SBATCH --job-name=peer-elt
#SBATCH --output=results/peer_elt_%j.out
#SBATCH --error=results/peer_elt_%j.err
#SBATCH --time=02:00:00
#SBATCH --mem=8G

set -euo pipefail

CONFIG_PATH="${1:-configs/prod.yml}"

python -m peer_elt.cli --config "${CONFIG_PATH}" run
