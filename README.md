# Leader Election with a K8s Lease

## Quickstart

Build docker image:
```
podman build -t leader-election .
podman run -it --rm -p 8000:8000 leader-election
```

Apply the deployment to your Kubernetes cluster:
```
kubectl apply -k k8s/
```

Verify the Lease: You can verify that the lease is created and check which pod holds the lease:
```
kubectl get lease leader-lease -o yaml
```
