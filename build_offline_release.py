#!/usr/bin/env python3
"""PUBLISHER-ONLY offline distribution builder for 007 First Light Georgian.

One-time ONLINE build on Windows (using publisher's existing Python):
    py build_offline_release.py

The resulting dist/*.zip is an OFFLINE player-facing package.
Its installer.exe never downloads components. Do NOT upload this builder kit
as though it were the finished offline release.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
PY_VER = "3.11.9"
PY_URL = f"https://www.python.org/ftp/python/{PY_VER}/python-{PY_VER}-embed-amd64.zip"
TOOLKIT_URL = "https://codeload.github.com/7akeem0/007-firstlight-toolkit/zip/refs/heads/main"
PACKAGES = {"lz4": "4.4.5", "fonttools": "4.63.0"}
USER_AGENT = "GeorgianLocalizationOfflineReleaseBuilder/1.0"


def read_url(url: str) -> bytes:
    print("  Fetching:", url, flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_extract_zip(source: bytes, dest: Path) -> None:
    dest = dest.resolve()
    with zipfile.ZipFile(io.BytesIO(source)) as z:
        for entry in z.infolist():
            path = Path(entry.filename.replace('\\', '/'))
            if path.is_absolute() or '..' in path.parts:
                raise ValueError("Unsafe ZIP entry: " + entry.filename)
            # Do not extract symlinks or weird device nodes.
            mode = (entry.external_attr >> 16) & 0o170000
            if mode not in (0, 0o100000, 0o040000):
                raise ValueError("Unsupported ZIP entry type: " + entry.filename)
            target = (dest / path).resolve()
            if target != dest and dest not in target.parents:
                raise ValueError("ZIP path escapes destination: " + entry.filename)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(entry) as src, target.open('wb') as out:
                    shutil.copyfileobj(src, out)


def cached_or_download(url: str, cache: Path, name: str) -> bytes:
    path = cache / name
    if path.is_file():
        print("  Using local cache:", name)
        return path.read_bytes()
    data = read_url(url)
    cache.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def wheel_for(name: str, version: str, cache: Path) -> tuple[str, bytes]:
    # PyPI's JSON API supplies both the wheel URL and SHA-256 hash.
    metadata = json.loads(cached_or_download(
        f'https://pypi.org/pypi/{name}/{version}/json', cache,
        f'pypi-{name}-{version}.json'))
    wheels = [entry for entry in metadata['urls'] if entry['filename'].endswith('.whl')]
    def score(entry):
        f = entry['filename'].lower()
        if 'cp311-cp311-win_amd64' in f:
            return 3
        if 'cp311-abi3-win_amd64' in f or 'cp39-abi3-win_amd64' in f:
            return 2
        if 'py3-none-any' in f:
            return 1
        return 0
    wheels.sort(key=score, reverse=True)
    if not wheels or score(wheels[0]) == 0:
        raise RuntimeError(f'No compatible Windows x64 / Python 3.11 wheel for {name} {version}')
    w = wheels[0]
    data = cached_or_download(w['url'], cache, w['filename'])
    actual = sha256(data)
    expected = w['digests']['sha256']
    if actual != expected:
        raise RuntimeError(f"Wheel hash mismatch for {w['filename']}: {actual} != {expected}")
    return w['filename'], data


def zip_wheel_into_site(data: bytes, site: Path) -> None:
    # Handles ordinary root wheel entries and purelib/platlib wheel data directories.
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for item in z.infolist():
            if item.is_dir():
                continue
            path = Path(item.filename.replace('\\', '/'))
            if path.is_absolute() or '..' in path.parts:
                raise RuntimeError('Unsafe wheel entry: ' + item.filename)
            parts = path.parts
            if len(parts) >= 3 and parts[0].endswith('.data'):
                if parts[1] not in ('purelib', 'platlib'):
                    continue
                parts = parts[2:]
            if not parts:
                continue
            dest = site.joinpath(*parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item) as r, dest.open('wb') as w:
                shutil.copyfileobj(r, w)


def make_release(cache: Path, out: Path, local_toolkit: Path | None = None) -> None:
    for relative in (
        'GeorgianInstaller.exe', 'INSTALL_GEORGIAN.bat',
        'UNINSTALL_GEORGIAN.bat', 'scripts/installer.py',
        'translations/ui.json', 'translations/dialogue.json',
        'translations/speakers.json', 'font_config.json',
        'fonts/NotoSansGeorgian-Regular.ttf', 'fonts/NotoSansGeorgian-Bold.ttf',
        'README_PLAYERS.txt',
    ):
        if not (ROOT / relative).is_file():
            raise RuntimeError('Build kit missing required file: ' + relative)

    with tempfile.TemporaryDirectory(prefix='georgian_offline_build_') as tmp:
        staging = Path(tmp) / '007_First_Light_Georgian_OFFLINE'
        staging.mkdir(parents=True)
        manifest = { 'format': 1, 'build': 'Offline beta', 'dependencies': {} }
        for relative in (
            'GeorgianInstaller.exe','INSTALL_GEORGIAN.bat','UNINSTALL_GEORGIAN.bat',
            'scripts/installer.py','translations/ui.json','translations/dialogue.json',
            'translations/speakers.json','font_config.json',
            'fonts/NotoSansGeorgian-Regular.ttf','fonts/NotoSansGeorgian-Bold.ttf',
            'README_PLAYERS.txt', 'LICENSES/Noto-Fonts-COPYRIGHT.txt',
            'SOURCE_AND_BUILD.md', 'GeorgianInstaller.go',
        ):
            src = ROOT / relative
            if src.is_file():
                dst = staging / relative
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        print('[1/4] Bundling official Windows Python runtime...', flush=True)
        pyzip = cached_or_download(PY_URL, cache, 'python-'+PY_VER+'-embed-amd64.zip')
        # External download may have a 404 HTML body; ZIP parsing rejects it.
        safe_extract_zip(pyzip, staging / 'runtime')
        manifest['dependencies']['python'] = {'url': PY_URL, 'sha256': sha256(pyzip)}
        pyhome = staging/'runtime'
        if not (pyhome/'python.exe').is_file() or not (pyhome/'python311.dll').is_file():
            raise RuntimeError('Invalid CPython embeddable package. Check source URL.')
        (pyhome/'python311._pth').write_text('python311.zip\n.\nLib\\site-packages\nimport site\n', encoding='ascii')
        site = pyhome/'Lib'/'site-packages'
        site.mkdir(parents=True, exist_ok=True)

        print('[2/4] Bundling Windows wheels (no pip on players PCs)...', flush=True)
        for name, ver in PACKAGES.items():
            filename, data = wheel_for(name, ver, cache)
            zip_wheel_into_site(data, site)
            manifest['dependencies'][name]={'version':ver,'filename':filename,'sha256':sha256(data)}

        print('[3/4] Bundling MIT toolkit source...', flush=True)
        toolkit = staging/'_toolkit'/'007-firstlight-toolkit-main'
        if local_toolkit is not None and (local_toolkit/'glacier'/'rpkg.py').is_file():
            print('  Using YOUR existing working toolkit checkout (no toolkit download).')
            toolkit.mkdir(parents=True, exist_ok=True)
            shutil.copytree(local_toolkit/'glacier', toolkit/'glacier',
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
            for extra in ('LICENSE', 'README.md'):
                src=local_toolkit/extra
                if src.is_file(): shutil.copy2(src,toolkit/extra)
            manifest['dependencies']['toolkit']={'source':'Existing local toolkit checkout',
                'glacier_sources_sha256':sha256(b''.join(
                  p.read_bytes() for p in sorted((toolkit/'glacier').rglob('*.py'))))}
        else:
            source = cached_or_download(TOOLKIT_URL,cache,'007-firstlight-toolkit-main.zip')
            safe_extract_zip(source, staging/'_toolkit')
            if not (toolkit/'glacier'/'rpkg.py').is_file():
                raise RuntimeError('Toolkit source ZIP layout changed. Refusing to publish.')
            for unnecessary in ('examples', '.github', 'docs', 'tools'):
                p=toolkit/unnecessary
                if p.is_dir(): shutil.rmtree(p)
            manifest['dependencies']['toolkit']={'url':TOOLKIT_URL,'sha256':sha256(source)}
        if not (toolkit/'LICENSE').is_file():
            raise RuntimeError('Toolkit MIT LICENSE missing. Refusing to redistribute.')

        print('[4/4] Writing manifest and offline ZIP...', flush=True)
        manifest['files']={str(p.relative_to(staging)).replace('\\','/'):sha256(p.read_bytes())
                           for p in staging.rglob('*') if p.is_file()}
        (staging/'BUILD_MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        out.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for f in sorted(staging.rglob('*')):
                if f.is_file():z.write(f,arcname=str(f.relative_to(staging.parent)).replace('\\','/'))
        print('\nBUILT:',out)
        print('Size:', f'{out.stat().st_size/1048576:.1f} MiB')
        print('SHA256:', sha256(out.read_bytes()))
        print('This is the file to test and, after independent review, upload to Nexus.')


def main():
    parser = argparse.ArgumentParser(description='Build complete OFFLINE Windows mod ZIP, for publisher only.')
    parser.add_argument('--cache',type=Path,default=ROOT/'_download_cache')
    parser.add_argument('--output',type=Path,default=ROOT/'dist'/'007_First_Light_Georgian_OFFLINE_BETA.zip')
    parser.add_argument('--toolkit-dir',type=Path,default=Path.home()/'Documents'/'007-firstlight-toolkit',
                        help='Your existing toolkit clone; falls back to fresh GitHub source if unavailable')
    args=parser.parse_args()
    try:
        make_release(args.cache,args.output,args.toolkit_dir)
    except Exception as exc:
        print('\nBUILD ERROR:',exc,flush=True)
        print('Nothing was installed into your game. The builder only creates a ZIP.')
        raise SystemExit(1)

if __name__=='__main__':main()
