"""No runtime dependencies; .hdop operations share the host's manifest validator."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from openhdo_plugin import PluginError, pack, unpack, validate_manifest


def scaffold(directory, id, runtime):
    manifest = dict(schemaVersion=1, apiVersion=1, id=id, name=id, version="1.0.0", permissions=[], entrypoints={}, contributes={})
    if runtime in {"python", "hybrid"}:
        manifest["entrypoints"]["python"] = "backend/plugin.py"
        manifest["permissions"] = ["api", "storage"]
    if runtime in {"ts", "hybrid"}:
        manifest["entrypoints"]["web"] = "web/plugin.js"
        manifest["contributes"]["modules"] = [{"id": "main", "name": id}]
    validate_manifest(manifest)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "hdo.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    if "python" in manifest["entrypoints"]:
        (directory / "backend").mkdir()
        (directory / "backend/plugin.py").write_text('''async def activate(ctx):
    async def state(request, context):
        if request.method == "PUT":
            context.store.set("settings", await request.json())
        return context.store.get("settings", {})
    ctx.route("settings", state, methods=("GET", "PUT"))
''', "utf-8")
    if "web" in manifest["entrypoints"]:
        (directory / "src").mkdir()
        (directory / "src/plugin.ts").write_text('''// Import SDK types only: host.React supplies the panel's React instance.
import type { PluginHost } from "@openhdo/plugin-sdk";
export function activate(host: PluginHost) {
  host.module({ id: "main", label: host.id, component: () => host.React.createElement("h1", null, host.id) });
}
''', "utf-8")
        (directory / "package.json").write_text(json.dumps({"name": id, "private": True, "type": "module", "scripts": {"build": "esbuild src/plugin.ts --bundle --format=esm --outfile=web/plugin.js"}, "devDependencies": {"esbuild": "^0.25.0", "typescript": "^5.7.0"}}, indent=2), "utf-8")
    (directory / ".gitignore").write_text("node_modules/\n__pycache__/\n*.hdop\n", "utf-8")
    return directory


def request(args, method, path, body=None):
    from urllib.parse import urlparse
    parsed = urlparse(args.server)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise PluginError("Use an HTTP(S) HDO server URL")
    token = os.environ.get("HDO_TOKEN")
    if not token:
        raise PluginError("Set HDO_TOKEN to the server API token (it is never written into the plugin)")
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/octet-stream"}
    req = urllib.request.Request(args.server.rstrip("/") + "/api/v1/plugins" + path, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as response:
        data = response.read()
        return json.loads(data) if data else None


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hdop", description="Build and manage HDO plugins")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("directory"); init.add_argument("--id", required=True); init.add_argument("--runtime", choices=["python", "ts", "hybrid"], default="hybrid")
    build = commands.add_parser("build"); build.add_argument("directory", nargs="?", default=".")
    package = commands.add_parser("pack"); package.add_argument("directory", nargs="?", default="."); package.add_argument("--out", required=True)
    validate = commands.add_parser("validate"); validate.add_argument("path")
    for name in ["install", "list", "enable", "disable", "remove", "scan"]:
        command = commands.add_parser(name); command.add_argument("--server", default="http://localhost:8000")
        if name not in {"list", "scan"}: command.add_argument("target")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            print(scaffold(args.directory, args.id, args.runtime))
        elif args.command == "build":
            directory = Path(args.directory).resolve()
            validate_manifest(json.loads((directory / "hdo.json").read_text("utf-8")))
            if (directory / "package.json").exists():
                npm = "npm.cmd" if os.name == "nt" else "npm"
                subprocess.run([npm, "run", "build"], cwd=directory, check=True)
            print("Build complete")
        elif args.command == "pack":
            print(pack(args.directory, args.out))
        elif args.command == "validate":
            path = Path(args.path)
            if path.is_dir():
                with tempfile.TemporaryDirectory() as staging:
                    package = pack(path, Path(staging) / "plugin.hdop")
                    manifest = unpack(package, Path(staging) / "expanded")
            else:
                with tempfile.TemporaryDirectory() as staging:
                    manifest = unpack(path, staging)
            print(f"Valid: {manifest['id']} {manifest['version']}")
        elif args.command == "install":
            # Validate locally before transmitting or executing any plugin code.
            with tempfile.TemporaryDirectory() as staging:
                unpack(args.target, staging)
            print(json.dumps(request(args, "POST", "/install", Path(args.target).read_bytes())))
        elif args.command == "scan":
            print(json.dumps(request(args, "POST", "/reload", b""), indent=2))
        elif args.command == "list":
            print(json.dumps(request(args, "GET", ""), indent=2))
        else:
            from urllib.parse import quote
            path = "/" + quote(args.target, safe="")
            print(json.dumps(request(args, "DELETE" if args.command == "remove" else "POST", path + ("" if args.command == "remove" else "/" + args.command), b"")))
    except (PluginError, OSError, ValueError, subprocess.CalledProcessError, urllib.error.URLError) as error:
        parser.exit(1, f"hdop: {error}\n")


if __name__ == "__main__":
    main()
