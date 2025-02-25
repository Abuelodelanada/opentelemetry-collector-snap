import sh
import requests

from tenacity import retry, stop_after_attempt, wait_fixed

OTEL_DIR = "/etc/otelcol"
OTEL_CONFIG = f"{OTEL_DIR}/config.yaml"
PROEMTHEUS_URL = "https://github.com/prometheus/prometheus/releases/download/v3.2.0/prometheus-3.2.0.linux-amd64.tar.gz"
PROMETHEUS_BINARY = "/tmp/prometheus-3.2.0.linux-amd64/prometheus"
PROMETHEUS_CONFIG = "tests/integration/prometheus_config.yaml"


@retry(stop=stop_after_attempt(20), wait=wait_fixed(10))
def _retry_metrics_api(endpoint: str, params: dict):
    response = requests.get(endpoint, params=params)
    assert len(response.json()["data"]["result"]) > 0


def install_snap_package(package, channel, classic=False):
    print(f"Installing {package}")
    sh.sudo.snap.install(
        package, f"--{channel}", "--classic" if classic is True else None
    )


def pack_opentelemetry_collector_snap():
    sh.snapcraft.pack()


def install_packed_opentelemetry_collector():
    snap_file = sh.grep("opentelemetry-collector_", _in=sh.ls("-1")).strip()
    sh.sudo.snap.install(snap_file, dangerous=True)


def install_promethues():
    # Prometheus snap does not run with --web.enable-remote-write-receiver
    sh.curl("-L", "-O", "--create-dirs", "--output-dir", "/tmp", PROEMTHEUS_URL)
    sh.tar("-zxvf", "/tmp/prometheus-3.2.0.linux-amd64.tar.gz", "-C", "/tmp")


def run_prometheus():
    cmd = sh.Command(PROMETHEUS_BINARY)
    cmd(
        "--web.enable-remote-write-receiver",
        "--config.file",
        PROMETHEUS_CONFIG,
        "--storage.tsdb.path=/tmp",
        _bg=True,
    )


def config_opentelemetry_collector():
    config_file = sh.ls("tests/integration/otel_config.yaml").strip()
    sh.sudo.mkdir("-p", OTEL_DIR)
    sh.sudo.cp(config_file, OTEL_CONFIG)


def setup():
    install_snap_package("node-exporter", "edge")
    install_promethues()
    install_snap_package("snapcraft", "stable", classic=True)
    pack_opentelemetry_collector_snap()
    install_packed_opentelemetry_collector()
    config_opentelemetry_collector()

    run_prometheus()
    sh.sudo.snap.connect("opentelemetry-collector:etc-otelcol-config")
    sh.sudo.snap.restart("opentelemetry-collector")


def test_integration():
    setup()

    # Check that the node exporter metrics reach Prometheus via otelcol.
    prome_sql = "node_cpu_seconds_total"
    endpoint = "http://localhost:9090/api/v1/query"
    _retry_metrics_api(endpoint, params={"query": prome_sql})
