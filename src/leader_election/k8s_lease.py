from kubernetes import client, config
from kubernetes.client.rest import ApiException

from datetime import datetime, timedelta, timezone
import time, uuid, os

# Load the kubeconfig file and initialize the client
# config.load_kube_config()
config.load_incluster_config()

# Configuration
# /var/run/secrets/kubernetes.io/serviceaccount/namespace
NAMESPACE = os.environ["NAMESPACE"]
LEASE_NAME = os.environ["LEASE_NAME"]
LEASE_DURATION_SECONDS = os.environ["LEASE_DURATION_SECONDS"]
RENEW_INTERVAL_SECONDS = os.environ["RENEW_INTERVAL_SECONDS"]
RETRY_INTERVAL_SECONDS = os.environ["RETRY_INTERVAL_SECONDS"]

# Create a unique identifier for this instance
LEASE_HOLDER_ID = str(uuid.uuid4())

# Initialize the coordination API client
coordination_api = client.CoordinationV1Api()


def create_or_update_lease():
    """Creates or updates a Lease object to acquire leadership."""
    now = datetime.now(timezone.utc)
    lease_spec = client.V1LeaseSpec(
        holder_identity=LEASE_HOLDER_ID,
        lease_duration_seconds=LEASE_DURATION_SECONDS,
        acquire_time=now,
        renew_time=now,
    )
    lease_body = client.V1Lease(
        metadata=client.V1ObjectMeta(name=LEASE_NAME, namespace=NAMESPACE),
        spec=lease_spec,
    )
    try:
        # Try to create the lease
        coordination_api.create_namespaced_lease(NAMESPACE, lease_body)
        print(f"{LEASE_HOLDER_ID} acquired leadership")
        return True
    except ApiException as e:
        if e.status == 409:
            # Lease already exists, so try to update it
            return update_lease(now)
        else:
            print(f"Failed to create lease: {e}")
            return False


def update_lease(now):
    """Updates the Lease object to renew leadership if current holder."""
    try:
        lease = coordination_api.read_namespaced_lease(LEASE_NAME, NAMESPACE)
        if (
            lease.spec.holder_identity == LEASE_HOLDER_ID
            or lease.spec.renew_time + timedelta(seconds=LEASE_DURATION_SECONDS) < now
        ):
            # Update lease if we are the holder or the lease has expired
            lease.spec.holder_identity = LEASE_HOLDER_ID
            lease.spec.renew_time = now
            coordination_api.replace_namespaced_lease(LEASE_NAME, NAMESPACE, lease)
            print(f"{LEASE_HOLDER_ID} renewed leadership")
            return True
        else:
            print(f"{LEASE_HOLDER_ID} is not the current leader")
            return False
    except ApiException as e:
        print(f"Failed to update lease: {e}")
        return False


def run_leader_election():
    """Runs the leader election loop."""
    while True:
        if create_or_update_lease():
            time.sleep(RENEW_INTERVAL_SECONDS)
        else:
            print("Retrying to acquire leadership...")
            time.sleep(RETRY_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_leader_election()
