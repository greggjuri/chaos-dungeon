#!/bin/bash
# Deploy frontend to S3 and invalidate CloudFront cache.
#
# Usage: ./scripts/deploy-frontend.sh [stack-name]
#
# Environment variables:
#   STACK_NAME - CloudFormation stack name (default: ChaosHosting-prod)

set -e

# Configuration - get from CloudFormation outputs
STACK_NAME="${1:-${STACK_NAME:-ChaosHosting-prod}}"

echo "Getting deployment configuration from stack: $STACK_NAME"

BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)

DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' \
  --output text)

if [ -z "$BUCKET_NAME" ] || [ "$BUCKET_NAME" == "None" ]; then
  echo "Error: Could not get bucket name from stack outputs"
  echo "Make sure the hosting stack has been deployed."
  exit 1
fi

if [ -z "$DISTRIBUTION_ID" ] || [ "$DISTRIBUTION_ID" == "None" ]; then
  echo "Error: Could not get distribution ID from stack outputs"
  echo "Make sure the hosting stack has been deployed."
  exit 1
fi

echo "Deploying to bucket: $BUCKET_NAME"
echo "CloudFront distribution: $DISTRIBUTION_ID"
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Build frontend
echo "Building frontend..."
cd frontend
npm ci
npm run build
cd ..

# Sync to S3 with appropriate cache headers
echo ""
echo "Uploading to S3..."

# HTML files - no cache (always fetch fresh for SPA routing)
aws s3 sync frontend/dist/ "s3://$BUCKET_NAME/" \
  --exclude "*" \
  --include "*.html" \
  --cache-control "no-cache, no-store, must-revalidate"

# JS/CSS files - long cache (Vite adds content hashes)
aws s3 sync frontend/dist/ "s3://$BUCKET_NAME/" \
  --exclude "*.html" \
  --include "*.js" \
  --include "*.css" \
  --cache-control "public, max-age=31536000, immutable"

# Other assets (images, fonts, etc.)
aws s3 sync frontend/dist/ "s3://$BUCKET_NAME/" \
  --exclude "*.html" \
  --exclude "*.js" \
  --exclude "*.css" \
  --cache-control "public, max-age=86400"

# Invalidate CloudFront cache for HTML and root
echo ""
echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/index.html" "/" \
  --no-cli-pager

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "Site: https://chaos.jurigregg.com"
echo "=========================================="
