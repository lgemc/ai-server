#!/bin/bash
# Self-signed SSL certificate generator for nginx reverse proxy

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/certs"

# Certificate configuration
DAYS_VALID=365
KEY_SIZE=2048
COMMON_NAME="${COMMON_NAME:-localhost}"
COUNTRY="${COUNTRY:-US}"
STATE="${STATE:-State}"
LOCALITY="${LOCALITY:-City}"
ORGANIZATION="${ORGANIZATION:-AI Services}"
ORG_UNIT="${ORG_UNIT:-Development}"

# Create certs directory if it doesn't exist
mkdir -p "${CERTS_DIR}"

echo "Generating self-signed SSL certificate..."
echo "  Common Name: ${COMMON_NAME}"
echo "  Valid for: ${DAYS_VALID} days"
echo ""

# Generate private key and certificate in one command
openssl req -x509 -nodes -days ${DAYS_VALID} -newkey rsa:${KEY_SIZE} \
    -keyout "${CERTS_DIR}/server.key" \
    -out "${CERTS_DIR}/server.crt" \
    -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCALITY}/O=${ORGANIZATION}/OU=${ORG_UNIT}/CN=${COMMON_NAME}" \
    -addext "subjectAltName=DNS:${COMMON_NAME},DNS:localhost,IP:127.0.0.1"

# Set appropriate permissions
chmod 600 "${CERTS_DIR}/server.key"
chmod 644 "${CERTS_DIR}/server.crt"

echo ""
echo "SSL certificates generated successfully!"
echo "  Private key: ${CERTS_DIR}/server.key"
echo "  Certificate: ${CERTS_DIR}/server.crt"
echo ""
echo "Certificate details:"
openssl x509 -in "${CERTS_DIR}/server.crt" -noout -subject -dates
