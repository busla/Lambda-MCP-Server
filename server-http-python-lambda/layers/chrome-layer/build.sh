#!/bin/bash
set -e

echo "Building Chrome AWS Lambda Layer..."

mkdir -p python/lib/python3.12/site-packages
mkdir -p chrome

echo "Installing chrome-aws-lambda..."
npm install chrome-aws-lambda

echo "Copying Chrome binary..."
cp -r node_modules/chrome-aws-lambda/bin/* chrome/

echo "Installing Python dependencies..."
pip install playwright==1.41.1 -t python/lib/python3.12/site-packages/

echo "Creating layer zip..."
zip -r ../chrome-aws-lambda-layer.zip python/ chrome/

echo "Chrome AWS Lambda Layer built successfully!"
echo "Layer zip: chrome-aws-lambda-layer.zip"
