"""Update only CTK's deployment settings in a VS Code user settings file."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

# Keep source offsets so JSONC comments, formatting and unrelated values survive.
TOKEN = re.compile(
    r'\s+|//[^\r\n]*|/\*.*?\*/|"(?:[^"\\\x00-\x1f]|\\.)*"'
    r"|[{}\[\]:,]|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?"
    r"|true|false|null",
    re.DOTALL,
)


def update_jsonc(source: str, settings: dict[str, str]) -> str:
    """Validate JSONC, replace top-level CTK values and append missing keys."""
    if not source.strip():
        source = "{}\n"
    tokens: list[re.Match[str]] = []
    position = 0
    for token in TOKEN.finditer(source):
        if token.start() != position:
            raise ValueError("Invalid JSONC in user settings")
        position = token.end()
        text = token[0]
        if not text.isspace() and not text.startswith(("//", "/*")):
            tokens.append(token)
    if position != len(source):
        raise ValueError("Invalid JSONC in user settings")
    if not tokens:
        return update_jsonc(source + "\n{}", settings)
    normalized = [
        token[0]
        for index, token in enumerate(tokens)
        if not (
            token[0] == ","
            and index + 1 < len(tokens)
            and tokens[index + 1][0] in ("}", "]")
        )
    ]
    if not isinstance(json.loads(" ".join(normalized)), dict):
        raise ValueError("User settings must be a JSON object")
    edits: list[tuple[int, int, str]] = []
    missing = dict(settings)
    index = 1
    while index < len(tokens) - 1:
        key = json.loads(tokens[index][0])
        start = index + 2
        end = start
        depth = 0
        while end < len(tokens):
            text = tokens[end][0]
            if depth == 0 and text in (",", "}"):
                break
            depth += int(text in ("{", "[")) - int(text in ("}", "]"))
            end += 1
        if key in settings:
            edits.append(
                (
                    tokens[start].start(),
                    tokens[end - 1].end(),
                    json.dumps(settings[key]),
                )
            )
            missing.pop(key, None)
        index = end + 1
    newline = "\r\n" if "\r\n" in source else "\n"
    if missing:
        # Insert at the beginning; a trailing // comment cannot swallow a comma.
        properties = ("," + newline).join(
            f"  {json.dumps(key)}: {json.dumps(value)}"
            for key, value in missing.items()
        )
        suffix = "," if len(tokens) > 2 else ""
        edits.append(
            (tokens[0].end(), tokens[0].end(), newline + properties + suffix + newline)
        )
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


def settings_path(code: str, profile: str) -> Path:
    """Resolve desktop/profile or host-wide Remote-SSH user settings."""
    executable = Path(code).resolve()
    agent = os.environ.get("VSCODE_AGENT_FOLDER")
    if not agent and (
        "remote-cli" in executable.parts or executable.name == "code-server"
    ):
        for parent in executable.parents:
            if parent.name in (".vscode-server", ".vscode-server-insiders"):
                agent = str(parent)
                break
        if not agent:
            raise ValueError("Custom remote server location: use --settings-file")
    if agent:
        # Remote settings are shared by this user's workspaces and local profiles.
        return Path(agent) / "data/Machine/settings.json"
    portable = os.environ.get("VSCODE_PORTABLE")
    if portable:
        user = Path(portable) / "user-data/User"
    else:
        config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        product = "Code - Insiders" if "insiders" in str(executable).lower() else "Code"
        user = config / product / "User"
    if profile and profile != "Default":
        storage = user / "globalStorage/storage.json"
        profiles = (
            json.loads(storage.read_text()).get("userDataProfiles", [])
            if storage.exists()
            else []
        )
        matches = [item for item in profiles if item.get("name") == profile]
        if len(matches) != 1:
            raise ValueError(
                "Cannot locate VS Code profile settings; use --settings-file"
            )
        if not matches[0].get("useDefaultFlags", {}).get("settings"):
            location = matches[0].get("location", "")
            if (
                not isinstance(location, str)
                or not location
                or Path(location).name != location
                or location in (".", "..")
            ):
                raise ValueError("Invalid profile location; use --settings-file")
            user = user / "profiles" / location
    return user / "settings.json"


def write_settings(path: Path, settings: dict[str, str]) -> None:
    # Follow a user's settings symlink without replacing the symlink itself.
    path = path.resolve()
    original = path.read_bytes() if path.exists() else None
    updated = update_jsonc(
        original.decode("utf-8-sig") if original else "", settings
    ).encode()
    if updated == original:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".ctk-settings-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(updated)
        if original is not None:
            os.chmod(temporary, path.stat().st_mode & 0o777)
        if (path.read_bytes() if path.exists() else None) != original:
            raise ValueError(
                "User settings changed during deployment; rerun the installer"
            )
        if original is not None:
            shutil.copy2(path, path.with_name(path.name + ".ctk-backup"))
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", required=True)
    parser.add_argument("--profile", default="")
    parser.add_argument("--settings-file", default="")
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--library-directory", required=True)
    args = parser.parse_args()
    root = Path(args.deployment)
    path = (
        Path(args.settings_file)
        if args.settings_file
        else settings_path(args.code, args.profile)
    )
    write_settings(
        path,
        {
            "ctk.server": args.server,
            "ctk.configPath": str(root / "server.yaml"),
            "ctk.pythonPath": str(root / "runtime/bin/python"),
            "ctk.libraryDirectory": args.library_directory,
        },
    )
    print(f"User settings: {path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f"Cannot configure CTK user settings: {error}") from error
