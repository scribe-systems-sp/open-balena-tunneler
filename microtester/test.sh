export IMAGENAME=razikus/open-balena-tunneler:tunneler-latest
export BIND=0.0.0.0
export PUBLIC=127.0.0.1
export SSLRESOLVER=letsencrypt
source ./confidential.sh
pytest -v