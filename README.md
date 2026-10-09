# HDO plugin CLI

`hdop` scaffolds Python/TypeScript plugins, validates them, builds TypeScript, creates deterministic `.hdop` packages and installs them through an HDO server's Plugins API. Python 3.11+; no runtime dependencies.

```sh
python -m pip install .
hdop init my-plugin --id example.my-plugin --runtime hybrid
cd my-plugin
npm install                 # TypeScript scaffolds need Node.js and esbuild
hdop build .
hdop validate .
hdop pack . --out my-plugin.hdop
```

`--runtime python`, `ts` or `hybrid` selects the scaffold. The Python SDK is provided by HDO at runtime. For TypeScript type checking, install `@openhdo/plugin-sdk` from the [SDK repository](https://github.com/OpenHDO/sdk/tree/master/typescript) after building that package; imports of its types are erased by esbuild. `build` executes the author's npm build script; validation/packaging never executes plugin entrypoints.

Install via the panel's **Plugins → Install .hdop**, or set the server's API token in `HDO_TOKEN` and use:

```sh
hdop install my-plugin.hdop --server http://localhost:8000
hdop list --server http://localhost:8000
hdop enable example.my-plugin --server http://localhost:8000
hdop disable example.my-plugin --server http://localhost:8000
hdop remove example.my-plugin --server http://localhost:8000
hdop scan --server http://localhost:8000
```

PowerShell: `$env:HDO_TOKEN = "your-server-api-token"`; POSIX shell: `export HDO_TOKEN=...`. CLI does not store the token. Prefer HTTPS for a remote server. `install` validates before upload and leaves new plugins disabled. `enable` explicitly executes trusted plugin code. `scan` reloads plugins copied into `/data/plugins`; state remains in `/data/plugin-data/<id>`. Server packages must implement Plugin API v1.

The archive is a ZIP with manifest and per-file SHA-256 checksums, not a publisher signature. Shared SDK validation rejects traversal, symlinks, duplicate/case-colliding names, invalid manifests, corrupt payloads and oversized archives. Only trusted plugins should be enabled.

See the complete [manifest and SDK guide](https://github.com/OpenHDO/server/blob/master/docs/plugins.md). Run tests with `python -m unittest discover -s tests -v`.
