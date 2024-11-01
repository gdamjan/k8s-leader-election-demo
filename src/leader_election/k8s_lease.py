from kubernetes.client.rest import ApiException
import kubernetes

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Thread, Event
from typing import Optional
import time, uuid, os

@dataclass
class State:
    # FIXME: copy of config.lease_holder_id - decide where it needs to be
    self_id: str
    current_leader_id: Optional[str] = None


@dataclass(frozen=True)
class Config:
    namespace: str
    lease_name: str
    lease_holder_id: str
    lease_duration_seconds: int
    renew_interval_seconds: float
    retry_interval_seconds: float


def load_config(lease_holder_id: Optional[str] = None, auto_configure_k8s: bool = True):
    if lease_holder_id is None:
        lease_holder_id = str(uuid.uuid4())

    namespace = os.environ["NAMESPACE"]
    lease_name = os.environ["LEASE_NAME"]
    lease_duration_seconds = int(os.environ["LEASE_DURATION_SECONDS"])
    renew_interval_seconds = float(os.environ["RENEW_INTERVAL_SECONDS"])
    retry_interval_seconds = float(os.environ["RETRY_INTERVAL_SECONDS"])

    if auto_configure_k8s:
        kubernetes.config.load_incluster_config()

    return Config(namespace, lease_name, lease_holder_id, lease_duration_seconds, renew_interval_seconds, retry_interval_seconds)


def create_or_update_lease(config: Config, state: State):
    """Creates or updates a Lease object to acquire leadership."""
    now = datetime.now(timezone.utc)
    coordination_api = kubernetes.client.CoordinationV1Api()
    lease_spec = kubernetes.client.V1LeaseSpec(
        holder_identity=config.lease_holder_id,
        lease_duration_seconds=config.lease_duration_seconds,
        acquire_time=now,
        renew_time=now,
    )
    lease_body = kubernetes.client.V1Lease(
        metadata=kubernetes.client.V1ObjectMeta(name=config.lease_name, namespace=config.namespace),
        spec=lease_spec,
    )
    try:
        # Try to create the lease
        coordination_api.create_namespaced_lease(config.namespace, lease_body)
        print(f"{config.lease_holder_id}: acquired leadership", flush=True)
        state.current_leader_id = config.lease_holder_id
        return True
    except ApiException as e:
        if e.status == 409:
            # Lease already exists, so try to update it
            return update_lease(config, state, now)
        else:
            print(f"Failed to create lease: {e}", flush=True)
            return False


def update_lease(config: Config, state: State, now: datetime):
    """Updates the Lease object to renew leadership if current holder."""
    coordination_api = kubernetes.client.CoordinationV1Api()
    try:
        lease = coordination_api.read_namespaced_lease(name=config.lease_name, namespace=config.namespace)
        we_are_leader = lease.spec.holder_identity == config.lease_holder_id
        lease_expired = lease.spec.renew_time + timedelta(seconds=config.lease_duration_seconds) < now
        if we_are_leader or lease_expired:
            # Update lease if we are the holder or the lease has expired
            lease.spec.holder_identity = config.lease_holder_id
            lease.spec.renew_time = now
            coordination_api.replace_namespaced_lease(name=config.lease_name, namespace=config.namespace, body=lease)
            print(f"{config.lease_holder_id} renewed leadership", flush=True)
            state.current_leader_id = config.lease_holder_id
            return True
        else:
            print(f"{config.lease_holder_id} is not the current leader", flush=True)
            state.current_leader_id = lease.spec.holder_identity
            return False
    except ApiException as e:
        print(f"Failed to update lease: {e}", flush=True)
        return False


def loop(config: Config, state: State) -> None:
    """Runs the leader election loop."""
    while True:
        if create_or_update_lease(config, state):
            # We are the leader, renew leadership on regular intervals
            time.sleep(config.renew_interval_seconds)
        else:
            # We are not the leader, retry to acquire leadership
            time.sleep(config.retry_interval_seconds)


def run_leader_election(config: Config) -> State:
    # FIXME: we need some kind of a signal/event here to notify for changes
    state_ev = Event()
    state = State(self_id=config.lease_holder_id)
    Thread(target=loop, args=(config, state), daemon=True).start()
    return state
