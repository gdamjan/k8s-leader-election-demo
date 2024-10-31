# Leader Election with a K8s Lease

## Quickstart

Build docker image:
```
podman build -t leader-election .
podman run -it --rm -p 8000:8000 leader-election

# push to local k3s registry
podman push --tls-verify=false leader-election registry.localhost/leader-election
```

## Testing on a local k3s

Apply the deployment to your Kubernetes cluster:
```
k3s kubectl apply -k k8s/
```

Verify the Lease: You can verify that the lease is created and check which pod holds the lease:
```
k3s kubectl get lease leader-lease -o yaml
```

Follow logs of all pods:
```
k3s kubectl logs -l app=leader-election --all-containers=true -f --max-log-requests 10
```

Run a pod with curl to access the web page:
```
k3s kubectl run curl -it --rm --image=quay.io/curl/curl-base:latest --command -- /bin/sh
# curl -v http://leader-election

# curl -v http://leader-election/crash -d 'crash random pod'
```
