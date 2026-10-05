from pathlib import Path

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
    assert config.client_options == ()


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
    assert config.client_options == (("grpc.max_receive_message_bytes", -1),)


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
