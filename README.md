# 007 First Light — Georgian Localization 🇬🇪

Source code and translation files for the community-made Georgian localization of **007 First Light**.

**This repository contains the source, not a ready-to-run game installer.** The tested player ZIP is distributed separately on the mod page. The source is published for transparency, review, and rebuilding the installer.

## Contents

- `GeorgianInstaller.go` — native offline launcher source (compiled into `GeorgianInstaller.exe`).
- `scripts/installer.py` — installation, RPKG patching and restoration logic. No downloading at install time.
- `build_offline_release.py` / `BUILD_RELEASE.bat` — publisher-side release assembly script, which fetches official runtime and dependencies on the publisher PC.
- `translations/` — Georgian UI, subtitles, and speaker names.
- `fonts/`, `font_config.json` — Noto Sans Georgian font assets and configuration.
- `third_party/007-firstlight-toolkit/` — relevant MIT-licensed Glacier toolkit source included in the tested release, with its license.
- `BUILD_MANIFEST.json` — checksums and dependency provenance from the tested offline beta build.
- `SOURCE_AND_BUILD.md` — full source and building notes.

## Build instructions

To build the native Windows x64 launcher with **Go 1.23+** from the repository root:

```powershell
$env:GOOS='windows'; $env:GOARCH='amd64'; $env:CGO_ENABLED='0'
go build -trimpath -ldflags='-s -w -buildid=' -o GeorgianInstaller.exe GeorgianInstaller.go
```

Then, on a Windows publisher computer with **Python installed** and internet access, double-click `BUILD_RELEASE.bat`. It produces `dist/007_First_Light_Georgian_OFFLINE_BETA.zip`. **Players do not need Python or the internet to install that finished ZIP.**

See [SOURCE_AND_BUILD.md](SOURCE_AND_BUILD.md) for dependency versions, licensing, and detailed behavior. The release assembler currently prefers the publisher's local toolkit checkout if available, otherwise the upstream GitHub main branch. This means rebuilding at a later date may produce different bytes; refer to `BUILD_MANIFEST.json` for the exact dependencies included in the tested build.

## Third-party code and licensing

This project uses the [007 First Light Toolkit](https://github.com/7akeem0/007-firstlight-toolkit) (MIT license), Noto Sans Georgian fonts (SIL Open Font License), and official CPython plus selected Python packages. Relevant license texts and provenance are included. Translation copyrights remain with the localization authors; no blanket license for original translations is granted by this source upload.

## Safety and distribution

- The **offline player installer does not download or run remote code** during installation.
- It modifies the player's local game archives; back up files before installation and keep recovery data until uninstalling.
- This repository **does not contain game RPKG archives or game executables**.
- Release executables may be quarantined by Nexus Mods or warned about by SmartScreen; use publisher review rather than bypassing security warnings.
- The tester reported the finished release functioning in-game; independent testing on clean installations and a full security review are still recommended.

Unofficial community project. Not endorsed by IO Interactive or the James Bond rights holders.
