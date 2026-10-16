# 007 First Light Georgian — installer source and reproducible build

This project is an unofficial Georgian translation for 007 First Light.
The native executable in this package is an **offline launcher only**. It does not access the network; it calls the bundled official Windows CPython interpreter with `scripts/installer.py install` or `uninstall`. The installer modifies the player's locally owned `Runtime/chunk0.rpkg` and `Runtime/chunk1.rpkg` through an MIT-licensed third-party toolkit.

## Native launcher source

`GeorgianInstaller.go` is the complete source of `GeorgianInstaller.exe`. It has **no third-party Go dependencies**. To rebuild with Go 1.23+:

```shell
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags='-s -w -buildid=' -o GeorgianInstaller.exe GeorgianInstaller.go
```

On Windows PowerShell:

```powershell
$env:GOOS='windows'; $env:GOARCH='amd64'; $env:CGO_ENABLED='0'
go build -trimpath -ldflags='-s -w -buildid=' -o GeorgianInstaller.exe GeorgianInstaller.go
```

Rebuilding with a different Go version could produce different binary bytes.

## Python installer source

`scripts/installer.py` is the full patch and recovery logic. It performs **no downloading or network calls**. It reads player game archives after confirmation, checks resource IDs, appends translated data and commits resource tables, saving original table and length snapshots for restoration.

## One-time publisher-side release assembly

`build_offline_release.py` is the source of the release assembler. Run `BUILD_RELEASE.bat` in the Build Kit on Windows with Python already installed, with internet connectivity **on the publisher's computer only**. It obtains:

- Official CPython **3.11.9** embeddable Windows x64 distribution from python.org.
- Two Windows wheels from PyPI: **lz4 4.4.5**, **fonttools 4.63.0**, checking their SHA-256 hashes against the PyPI metadata.
- MIT-licensed toolkit code from the publisher's existing `Documents/007-firstlight-toolkit` checkout when available, or from the upstream GitHub main branch otherwise; always include its `LICENSE` file.
- Noto Sans Georgian Regular/Bold fonts are already shipped in the Build Kit under SIL OFL 1.1.

The builder creates `dist/007_First_Light_Georgian_OFFLINE_BETA.zip`. **The result is offline for end users**; no runtime downloader, pip, Git, or system-wide installation. A `BUILD_MANIFEST.json` records source URLs and dependency hashes.

**Reproducibility limitation:** the toolkit may be retrieved from the GitHub `main` branch when a local checkout is unavailable, which can change. The produced manifest pins the exact fetched ZIP SHA-256 but a subsequent build may fetch a newer revision. Before publishing a stable v1.0, pin a reviewed immutable toolkit commit or its archive digest.

## Licensing and trust

- Translation data: localization authors' rights.
- Toolkit: MIT, maintained by @7akeem0; upstream LICENSE is bundled.
- Python: PSF licensing, official runtime ZIP includes its license.
- Fonts: Noto Sans Georgian, SIL OFL 1.1; copyright documentation is in `LICENSES/`.
- lz4 and fonttools: upstream licenses in the package metadata where supplied.
- **No original proprietary RPKG assets, game executables, or game code are bundled.**

Nexus Mods may quarantine executable-containing ZIP files even if they are harmless or offline. Source availability does not guarantee approval; request manual review and provide this document, the repository link, build instructions, and antivirus scan results. Do not encourage users to disable antivirus or bypass SmartScreen warnings.

## Validation

The launcher is cross-compiled to PE32+ x64 and Python sources pass syntax checks. Packaging logic was tested with mock ZIP archives; **the actual Windows CPython runtime and real-game install/uninstall require testing on Windows**. The Build Kit alone is NOT a finished offline release.
