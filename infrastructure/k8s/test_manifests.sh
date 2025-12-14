#!/bin/bash

# Test Kubernetes manifests
kubectl apply --dry-run=client -f deployments.yaml
