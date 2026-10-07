from pathlib import Path
import json
import tempfile

import pytest

from clang_toolkit.configuration import ConfigurationError, load_network_config


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_default_endpoint_and_application_limits(tmp_path):
    config = load_network_config(cwd=tmp_path, home=tmp_path / "home", system_dir=tmp_path / "etc")
    assert config.target.endswith("/ctk.sock")
    assert config.transport == "unix"
    assert (config.pool_size, config.queue_size) == (3, 100)
    assert (config.max_files, config.max_memory_bytes) == (100, 2_147_483_648)
    assert config.client_options == (("grpc.max_receive_message_length", 67_108_864),)
    assert config.server_options == (("grpc.max_send_message_length", 67_108_864),)


def test_configuration_layers_merge_and_hidden_file_wins(tmp_path):
    system = tmp_path / "etc"
    home = tmp_path / "home"
    cwd = tmp_path / "project"
    write(system / "clang-toolkit.yaml", "network:\n  tcp:\n    host: 127.0.0.1\n    port: 5000\n")
    write(home / "clang-toolkit.yaml", "network:\n  tcp:\n    port: 5001\n")
    write(home / ".clang-toolkit.yaml", "network:\n  tcp:\n    port: 5002\n")
    write(cwd / "clang-toolkit.yaml", "network:\n  transport: tcp\n")
    config = load_network_config(cwd=cwd, home=home, system_dir=system)
    assert config.target == "127.0.0.1:5002"


def test_cli_file_is_highest_layer_and_relative_socket_uses_its_directory(tmp_path):
    cwd = tmp_path / "project"
    selected = write(tmp_path / "selected" / "ctk.yaml", "network:\n  unix:\n    socket_path: run/ctk.sock\n")
    config = load_network_config(selected, cwd=cwd, home=tmp_path / "home", system_dir=tmp_path / "etc")
    assert config.target == f"unix://{selected.parent / 'run/ctk.sock'}"


def test_explicit_tcp_ipv6_and_optional_grpc_values(tmp_path):
    selected = write(
        tmp_path / "network.yaml",
        "network:\n  transport: tcp\n  tcp:\n    host: ::1\n    port: 8123\nclient:\n  grpc:\n    max_receive_message_bytes: -1\n    max_send_message_bytes: null\n",
    )
    config = load_network_config(selected, cwd=tmp_path, home=tmp_path / "home", system_dir=tmp_path / "etc")
    assert config.target == "[::1]:8123"
    assert config.client_options == (("grpc.max_receive_message_length", -1),)


def test_bracketed_ipv4_is_normalized_for_grpc_target(tmp_path):
    selected = write(
        tmp_path / "network.yaml",
        "network:\n  transport: tcp\n  tcp:\n    host: '[127.0.0.1]'\n    port: 8123\n",
    )
    config = load_network_config(selected, cwd=tmp_path, home=tmp_path / "home", system_dir=tmp_path / "etc")
    assert config.target == "127.0.0.1:8123"


def test_optional_timeout_and_shutdown_values_can_be_cleared(tmp_path):
    selected = write(
        tmp_path / "network.yaml",
        "client:\n  rpc_timeout_ms: null\nserver:\n  shutdown_grace_ms: null\n",
    )
    config = load_network_config(selected, cwd=tmp_path, home=tmp_path / "home", system_dir=tmp_path / "etc")
    assert config.rpc_timeout is None
    assert config.shutdown_grace is None


@pytest.mark.parametrize(
    "text, message",
    [
        ("version: 2\n", "version"),
        ("pool:\n  size: true\n", "integer"),
        ("pool:\n  size: 0x10\n", "base-10"),
        ("unknown: true\n", "unknown configuration key"),
        ("pool:\n  size: 1\n  size: 2\n", "duplicate YAML key"),
        ("network:\n  transport: tcp\n", "network.tcp.host is required"),
        ("network:\n  transport: tcp\n  tcp:\n    host: localhost\n    port: 65536\n", "integer"),
        ("network:\n  tcp:\n    host: 192.168.1.10\n", "loopback"),
        ("network:\n  tcp:\n    port: false\n", "integer"),
    ],
)
def test_invalid_configuration_is_rejected(tmp_path, text, message):
    selected = write(tmp_path / "bad.yaml", text)
    with pytest.raises(ConfigurationError, match=message):
        load_network_config(selected, cwd=tmp_path, home=tmp_path / "home", system_dir=tmp_path / "etc")


def test_missing_explicit_config_is_an_error(tmp_path):
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_network_config(tmp_path / "missing.yaml", cwd=tmp_path, home=tmp_path / "home", system_dir=tmp_path / "etc")


def test_invalid_value_is_rejected_even_when_a_higher_layer_overrides_it(tmp_path):
    system = write(tmp_path / "etc" / "clang-toolkit.yaml", "pool:\n  size: -1\n")
    selected = write(tmp_path / "selected.yaml", "pool:\n  size: 2\n")
    with pytest.raises(ConfigurationError, match="pool.size"):
        load_network_config(selected, cwd=tmp_path, home=tmp_path / "home", system_dir=system.parent)


_CONFORMANCE = json.loads((Path(__file__).parents[1] / "fixtures" / "network_configuration.json").read_text())


@pytest.mark.parametrize("case", _CONFORMANCE["cases"], ids=lambda case: case["name"])
def test_shared_network_configuration_conformance(tmp_path, case):
    assert _CONFORMANCE["format"] == 1
    paths = {layer: tmp_path / relative for layer, relative in _CONFORMANCE["layers"].items()}
    for layer, text in case["files"].items():
        write(paths[layer], text)
    selected = paths["explicit"] if "explicit" in case["files"] else None
    options = {"cwd": tmp_path / "project", "home": tmp_path / "home", "system_dir": tmp_path / "etc"}
    if case.get("error") or "error_key" in case:
        with pytest.raises(ConfigurationError) as failure:
            load_network_config(selected, **options)
        assert str(tmp_path) in str(failure.value)
        if "error_key" in case:
            assert case["error_key"] in str(failure.value)
        return
    config = load_network_config(selected, **options)
    expected = case["expected"]

    def expand(value):
        return value.replace("${ROOT}", str(tmp_path)).replace("${TEMP}", tempfile.gettempdir())

    assert config.target == expand(expected["target"])
    for key, value in expected.get("values", {}).items():
        assert config.effective_values[key] == value
        assert type(config.effective_values[key]) is type(value)
    for key, value in expected.get("origins", {}).items():
        assert config.provenance[key] == expand(value)


def test_provenance_effective_values_are_read_only_and_defaults_are_explicit(tmp_path):
    config = load_network_config(cwd=tmp_path, home=tmp_path / "home", system_dir=tmp_path / "etc")
    assert len(config.effective_values) == len(config.provenance) == 11
    assert set(config.provenance.values()) == {"<defaults>"}
    assert "network.tcp.host" not in config.effective_values
    assert "client.grpc.max_send_message_bytes" not in config.effective_values
    with pytest.raises(TypeError):
        config.effective_values["pool.size"] = 8
    with pytest.raises(TypeError):
        config.provenance["pool.size"] = "new.yaml"


def test_duplicate_and_base_notation_errors_report_file_and_dotted_key(tmp_path):
    for text in ("pool:\n  size: 1\n  size: 2\n", "pool:\n  size: 0x10\n"):
        path = write(tmp_path / "bad.yaml", text)
        with pytest.raises(ConfigurationError) as failure:
            load_network_config(path, cwd=tmp_path, home=tmp_path / "home", system_dir=tmp_path / "etc")
        assert str(path) in str(failure.value)
        assert "pool.size" in str(failure.value)


def test_client_and_server_grpc_options_use_native_channel_argument_names(tmp_path):
    selected = write(tmp_path / "network.yaml", '''client:
  grpc:
    max_receive_message_bytes: 128
    max_send_message_bytes: -1
server:
  grpc:
    max_receive_message_bytes: 256
    max_send_message_bytes: 512
''')
    config = load_network_config(selected, cwd=tmp_path, home=tmp_path / "home", system_dir=tmp_path / "etc")
    assert dict(config.client_options) == {"grpc.max_receive_message_length": 128, "grpc.max_send_message_length": -1}
    assert dict(config.server_options) == {"grpc.max_receive_message_length": 256, "grpc.max_send_message_length": 512}
    assert config.effective_values["client.grpc.max_receive_message_bytes"] == 128
