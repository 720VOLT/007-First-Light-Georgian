"""Georgian localization installer for 007 First Light.

Requires the MIT-licensed 7akeem0 toolkit downloaded into _toolkit by prepare.ps1.
Does not contain or distribute RPKG archives. Append-only changes are backed up
using tables and original file length; it does not copy multi-gigabyte archives.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / '_toolkit' / '007-firstlight-toolkit-main'
BACKUP_NAME = '_georgian_localization_backup'
STATE_NAME = 'install_state.json'
PATCHED_THRESHOLD = .95  # Abort/rollback if IDs don't match supported game build.


def load_json(file):
    with open(file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_atomic(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)


def is_game(path):
    path = Path(path).expanduser()
    return (path / 'Runtime' / 'chunk0.rpkg').is_file() and (path / 'Runtime' / 'chunk1.rpkg').is_file()


def resolve_game(steam=None):
    # Most players extract the package directly beside the game's Runtime folder.
    if is_game(ROOT):
        print(f'Game found beside installer: {ROOT}', flush=True)
        if input('Use this game folder? [Y/n]: ').strip().lower() in ('', 'y', 'yes'):
            return ROOT.resolve()
    last = ROOT / '.last_game_path.txt'
    if last.is_file():
        candidate = Path(last.read_text('utf-8').strip())
        if is_game(candidate):
            print(f'Previous game folder: {candidate}', flush=True)
            response = input('Use this folder? [Y/n]: ').strip().lower()
            if response in ('','y','yes'):
                return candidate.resolve()
    # Check common Steam/store directories without an expensive whole-drive scan.
    if steam is not None:
        try:
            for candidate in steam._store_paths('007 First Light') + steam._xbox_paths():
                if is_game(candidate):
                    print(f'Game found: {candidate}', flush=True)
                    if input('Use this folder? [Y/n]: ').strip().lower() in ('','y','yes'):
                        return Path(candidate).resolve()
        except Exception as exc:
            print(f'Automatic detection unavailable: {exc}', flush=True)
    while True:
        raw = input('Paste the full GAME FOLDER path (or press Enter to cancel): ').strip().strip('"').strip("'")
        if not raw:
            raise RuntimeError('Cancelled.')
        candidate=Path(raw)
        # Accept Runtime folder too if user pasted it instead of its parent.
        if candidate.name.lower() == 'runtime':
            candidate = candidate.parent
        if is_game(candidate):
            return candidate.resolve()
        print('Not found: expected Runtime\\chunk0.rpkg and Runtime\\chunk1.rpkg in that folder.', flush=True)


def load_toolkit():
    if not (ENGINE / 'glacier' / 'rpkg.py').is_file():
        raise RuntimeError('Toolkit not downloaded. Double-click INSTALL_GEORGIAN.bat first.')
    sys.path.insert(0, str(ENGINE))
    from glacier import rpkg, locr, dlge, gfxf, steam
    return rpkg, locr, dlge, gfxf, steam


def preflight(root, game, rpkg):
    runtime = game / 'Runtime'
    chunks = [runtime / 'chunk0.rpkg', runtime / 'chunk1.rpkg']
    for chunk in chunks:
        h = rpkg.read_header(str(chunk))  # Validate RPKG v2 early.
        if not h['hashCount'] or not h['table1Size'] or not h['table2Size']:
            raise RuntimeError(f'Invalid RPKG tables: {chunk}')
    free_bytes = shutil.disk_usage(str(runtime)).free
    if free_bytes < 1_073_741_824:
        raise RuntimeError('At least 1 GB of free space on the game drive is required for safety.')
    # Detect at least one line of the previous Georgian patch. It is unsafe to
    # create a "clean" backup from an already-localized game.
    for chunk in chunks:
        h,t1,t2 = rpkg.read_tables(str(chunk))
        match = rpkg.find_resource(t1, h['hashCount'], '01F73A398FDC61E6')
        if match:
            idx = match[0]
            roff = rpkg.build_record_offsets(t2, h['hashCount'])
            raw,_ = rpkg.read_resource(str(chunk),t1,t2,idx,roff)
            if raw:
                from glacier import dlge
                s = dlge.get_base_text(raw)
                if s:
                    if any('\u10a0' <= c <= '\u10ff' for c in s):
                        raise RuntimeError('Georgian dialogue already installed! Restore original game archives before using this release installer.')
                    try:
                        fixed = s.encode('latin-1').decode('utf-8')
                    except UnicodeError:
                        fixed = ''
                    if any('\u10a0' <= c <= '\u10ff' for c in fixed):
                        raise RuntimeError('An older Georgian patch is already installed. Restore original game archives first; do NOT overwrite its backup.')
    return chunks


def patch_archive(chunk, rpkg, locr, dlge, gfxf, ui_data, dlg_data, speakers, font_cfg):
    name = chunk.name
    header, t1, t2 = rpkg.read_tables(str(chunk))
    roff = rpkg.build_record_offsets(t2, header['hashCount'])
    n_ui = n_dialogue = n_speakers = 0
    writes=0
    print(f'\n--- Patching {name} ---', flush=True)
    for idx,h,off,sf in rpkg.t1_iter(t1,header['hashCount']):
        if t2[roff[idx]:roff[idx]+4] != rpkg.TYPE_LOCR:
            continue
        key = '%016X' % h
        if key not in ui_data:
            continue
        raw, _ = rpkg.read_resource(str(chunk),t1,t2,idx,roff)
        if raw is None:
            continue
        try:
            new_raw, count = locr.rebuild(raw,{k.upper():v for k,v in ui_data[key].items()},lang_index=1)
        except Exception:
            continue
        if count:
            rpkg.write_resource_eof(str(chunk),t1,t2,idx,new_raw,roff)
            writes+=1
            n_ui+=count

    for idx,h,off,sf in rpkg.t1_iter(t1,header['hashCount']):
        if t2[roff[idx]:roff[idx]+4] != rpkg.TYPE_DLGE:
            continue
        key = '%016X' % h
        if key not in dlg_data and not speakers:
            continue
        raw, _ = rpkg.read_resource(str(chunk),t1,t2,idx,roff)
        if raw is None:
            continue
        changed=False
        if key in dlg_data:
            segs = dlg_data[key].get('segments')
            if segs:
                modified = dlge.inject_spoken(raw,segs,shape_fn=lambda v:v)
                if modified is not None:
                    raw=modified; changed=True; n_dialogue+=1
        if speakers:
            modified = dlge.inject_speaker(raw,speakers,shape_fn=lambda v:v)
            if modified is not None:
                raw=modified;changed=True;n_speakers+=1
        if changed:
            rpkg.write_resource_eof(str(chunk),t1,t2,idx,raw,roff)
            writes+=1
            if writes % 500 == 0:
                print(f'  {name}: written {writes:,} resources...',flush=True)

    if font_cfg is not None and name == 'chunk0.rpkg':
        match = rpkg.find_resource(t1,header['hashCount'],'01DD9580958CDC9B')
        if match is None:
            raise RuntimeError('Font resource not found in chunk0. Unsupported game build.')
        raw_font,_=rpkg.read_resource(str(chunk),t1,t2,match[0],roff)
        if raw_font is None:
            raise RuntimeError('Cannot read original font resource.')
        new_font=gfxf.build(raw_font,font_cfg,verbose=False)
        rpkg.write_resource_eof(str(chunk),t1,t2,match[0],new_font,roff)
        writes+=1
        print(f'  Georgian font: {len(new_font):,} bytes',flush=True)

    # Commit this archive's index after all appends; backups were made first.
    rpkg.commit_tables(str(chunk),t1,t2)
    print(f'  UI strings: {n_ui:,} | dialogue resources: {n_dialogue:,} | speaker resources: {n_speakers:,}',flush=True)
    return n_ui, n_dialogue, n_speakers, writes


def install():
    rpkg, locr, dlge, gfxf, steam = load_toolkit()
    ui_data=load_json(ROOT/'translations'/'ui.json')
    dlg_data=load_json(ROOT/'translations'/'dialogue.json')
    speakers={k:v for k,v in load_json(ROOT/'translations'/'speakers.json').items() if v}
    font_cfg=load_json(ROOT/'font_config.json')
    for relative in set(font_cfg['weights'].values()):
        if not (ROOT/relative).is_file():
            raise RuntimeError(f'Font not found: {relative}. Re-run INSTALL_GEORGIAN.bat.')
    game=resolve_game(steam)
    runtime=game/'Runtime'
    backup_root=runtime/BACKUP_NAME
    if backup_root.exists():
        raise RuntimeError(f'Backup folder already exists: {backup_root}\nThis installer will not overwrite it. Use UNINSTALL_GEORGIAN.bat to restore, or ask for help.')
    print(f'\nGame: {game}\nChecking archives and available disk space...',flush=True)
    chunks=preflight(ROOT,game,rpkg)
    print('\nIMPORTANT: Close the game before continuing.',flush=True)
    print('This will change chunk0.rpkg and chunk1.rpkg in place, and create small table/size backups.',flush=True)
    if input('Type INSTALL to continue: ').strip() != 'INSTALL':
        raise RuntimeError('Cancelled without changes.')
    state={'status':'pending','game_dir':str(game),'chunks':{}}
    try:
        backup_root.mkdir(parents=False,exist_ok=False)
        for chunk in chunks:
            folder=backup_root/chunk.name
            rpkg.backup_chunk(str(chunk),str(folder))
            state['chunks'][chunk.name]={'original_size':chunk.stat().st_size}
        save_json_atomic(backup_root/STATE_NAME,state)
        totals=[0,0,0,0]
        os.chdir(ROOT)  # gfxf.build() resolves font weight paths against working directory.
        for chunk in chunks:
            n=patch_archive(chunk,rpkg,locr,dlge,gfxf,ui_data,dlg_data,speakers,font_cfg)
            totals=[a+b for a,b in zip(totals,n)]
        if totals[0] < PATCHED_THRESHOLD * sum(map(len,ui_data.values())):
            raise RuntimeError('Not enough UI translations found. Unsupported game build; rolling back.')
        if totals[1] < PATCHED_THRESHOLD * len(dlg_data):
            raise RuntimeError('Not enough dialogue translations found. Unsupported game build; rolling back.')
        if totals[2] == 0:
            raise RuntimeError('No speaker names were patched. Rolling back.')
        for chunk in chunks:
            state['chunks'][chunk.name]['installed_size']=chunk.stat().st_size
        state['status']='installed'
        save_json_atomic(backup_root/STATE_NAME,state)
        (ROOT/'.last_game_path.txt').write_text(str(game),encoding='utf-8')
        print('\nSUCCESS! Georgian UI, dialogue, speakers and font installed.',flush=True)
        print(f'  {totals[0]:,} UI strings, {totals[1]:,} dialogue resources, {totals[2]:,} speaker resources',flush=True)
        print(f'  Recovery data: {backup_root}',flush=True)
        print('  Select English text language in-game and enable subtitles.',flush=True)
    except BaseException:
        if backup_root.exists():
            print('\nAn error/interruption occurred. Attempting to restore original archives...',flush=True)
            failed=[]
            for chunk in chunks:
                folder=backup_root/chunk.name
                if (folder/'meta.json').is_file():
                    try:
                        rpkg.restore_chunk(str(chunk),str(folder))
                        print(f'  Restored {chunk.name}',flush=True)
                    except Exception as exc:
                        failed.append(f'{chunk.name}: {exc}')
            if not failed:
                shutil.rmtree(backup_root)
                print('Rollback complete.',flush=True)
            else:
                print('CRITICAL: Could not fully restore archives. KEEP recovery data at:', backup_root,flush=True)
                for s in failed: print('  '+s,flush=True)
        raise


def uninstall():
    # Only stdlib needed; works even when toolkit or internet is unavailable.
    game=resolve_game(None)
    backup_root=game/'Runtime'/BACKUP_NAME
    manifest=backup_root/STATE_NAME
    if not manifest.is_file():
        raise RuntimeError(f'No Georgian mod backup found in {backup_root}.\nIf the game was modified with another toolkit, use THAT toolkit backup or verify game files.')
    state=load_json(manifest)
    if Path(state.get('game_dir','')).resolve()!=game.resolve():
        raise RuntimeError('The backup belongs to a different game folder. Refusing to restore.')
    for name,info in state['chunks'].items():
        chunk=game/'Runtime'/name
        if not chunk.is_file():
            raise RuntimeError(f'Missing archive: {chunk}')
        current_size=chunk.stat().st_size
        if state['status']=='installed' and current_size!=info.get('installed_size'):
            raise RuntimeError(f'{name} size changed since install. A game update or other mod may have modified it.\nDo NOT restore this snapshot over changed archives. Use the game launcher to verify files if needed.')
        if current_size < info['original_size']:
            raise RuntimeError(f'{name} is smaller than its original size. Refusing unsafe restore.')
    # Validate ALL backup snapshots before asking to restore.

    prepared = []
    for name,info in state['chunks'].items():
        chunk=game/'Runtime'/name
        folder=backup_root/name
        meta=load_json(folder/'meta.json')
        t1=(folder/'table1.bin').read_bytes()
        t2=(folder/'table2.bin').read_bytes()
        if len(t1)!=meta['table1Size'] or len(t2)!=meta['table2Size']:
            raise RuntimeError(f'Backup tables are incomplete for {name}. No archive was modified.')
        if meta['chunk_size'] != info['original_size']:
            raise RuntimeError(f'Backup size disagreement for {name}. No archive was modified.')
        prepared.append((name, chunk, meta, t1, t2))
    print(f'\nRestore original archives for: {game}',flush=True)
    if input('Type RESTORE to continue: ').strip()!='RESTORE':
        raise RuntimeError('Cancelled without changes.')
    for name,chunk,meta,t1,t2 in prepared:
        with chunk.open('r+b') as f:
            f.truncate(meta['chunk_size'])
            f.seek(0x19)
            f.write(t1)
            f.seek(0x19+meta['table1Size'])
            f.write(t2)
            f.flush()
            os.fsync(f.fileno())
        stamp=time.mktime((2020,1,1,0,0,0,0,0,-1))
        os.utime(chunk,(stamp,stamp))
        print(f'Restored {name}',flush=True)
    shutil.rmtree(backup_root)
    print('\nSUCCESS! Original game archives restored.',flush=True)


def main():
    action=sys.argv[1] if len(sys.argv)>1 else 'install'
    try:
        if action=='install': install()
        elif action=='uninstall': uninstall()
        else: raise RuntimeError(f'Unknown action: {action}')
        return 0
    except KeyboardInterrupt:
        print('\nCancelled.',flush=True)
        return 1
    except Exception as exc:
        print(f'\nERROR: {exc}',flush=True)
        return 1

if __name__=='__main__':
    sys.exit(main())
