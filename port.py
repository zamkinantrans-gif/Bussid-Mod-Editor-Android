#!/usr/bin/env python3
"""Pembantu port BUSSID Mod Editor -> Android.
  reconstruct <game_dir> <assetripper_dir> <out_project>
  patch       <project> <native_out>
"""
import os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8765

def _post(path, fields):
    data = urllib.parse.urlencode(fields).encode()
    return urllib.request.urlopen(urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}", data=data), timeout=7200).read()

def reconstruct(game, ar, out):
    exe = next(os.path.join(r, f) for r, _, fs in os.walk(ar) for f in fs
               if f == "AssetRipper.GUI.Free")
    os.chmod(exe, 0o755)
    export = os.path.abspath("ripped"); shutil.rmtree(export, ignore_errors=True)
    proc = subprocess.Popen([exe, "--port", str(PORT), "--launch-browser", "false"])
    try:
        for _ in range(90):  # tunggu server siap
            try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=2); break
            except Exception: time.sleep(1)
        # Endpoint/nama field AssetRipper 1.x; belum diverifikasi, coba dua kapitalisasi.
        for key in ("path", "Path"):
            try: _post("/LoadFolder", {key: os.path.abspath(game)}); break
            except urllib.error.HTTPError as e: print("LoadFolder", key, e)
        for key in ("path", "Path"):
            try: _post("/Export/UnityProject", {key: export}); break
            except urllib.error.HTTPError as e: print("Export", key, e)
    finally:
        proc.terminate()
    root = next((r for r, ds, _ in os.walk(export) if "ProjectSettings" in ds and "Assets" in ds), None)
    if not root: sys.exit("Project hasil AssetRipper tidak ditemukan")
    shutil.rmtree(out, ignore_errors=True); shutil.move(root, out)
    print("Project:", out, open(os.path.join(out, "ProjectSettings/ProjectVersion.txt")).read())

RULES = [  # (regex, pengganti) - idempoten
    (r'(?<![A-Za-z_])(?:UnityEngine\.)?Application\.dataPath\s*\+\s*"/\.\./', 'AndroidPaths.Root + "/'),
    (r'(?<![A-Za-z_])(?:UnityEngine\.)?Input\.GetKeyDown\(', 'AndroidInput.GetKeyDown('),
    (r'(?<![A-Za-z_])(?:UnityEngine\.)?Input\.GetKeyUp\(', 'AndroidInput.GetKeyUp('),
    (r'(?<![A-Za-z_])(?:UnityEngine\.)?Input\.GetKey\(', 'AndroidInput.GetKey('),
    (r'(?<![A-Za-z_])(?:UnityEngine\.)?Input\.GetMouseButtonDown\(', 'AndroidInput.GetMouseButtonDown('),
    (r'(?<![A-Za-z_])(?:UnityEngine\.)?Input\.GetMouseButtonUp\(', 'AndroidInput.GetMouseButtonUp('),
    (r'(?<![A-Za-z_])(?:UnityEngine\.)?Input\.GetMouseButton\(', 'AndroidInput.GetMouseButton('),
    (r'(?<![A-Za-z_])(?:UnityEngine\.)?Input\.mouseScrollDelta', 'AndroidInput.mouseScrollDelta'),
    (r'(?<![A-Za-z_])(?:UnityEngine\.)?Input\.GetAxis\("Mouse ScrollWheel"\)', 'AndroidInput.ScrollWheel'),
]
SUSPECT = re.compile(r'DllImport|Process\b|ProcessStartInfo|explorer\.exe|etctool|Devil|assimp|'
                     r'System\.Windows|Microsoft\.Win32|OpenFileName|\.exe\b|FileBrowser|'
                     r'Directory\.GetLogicalDrives|DriveInfo|\\\\')

def patch(project, native):
    assets = os.path.join(project, "Assets")
    rep = open("port-report.txt", "w", encoding="utf-8")
    changed = 0
    for r, _, fs in os.walk(assets):
        if "AndroidPort" in r or os.sep + "Editor" in r: continue
        for f in fs:
            if not f.endswith(".cs"): continue
            p = os.path.join(r, f)
            s = open(p, encoding="utf-8-sig", errors="replace").read(); o = s
            for rx, rp in RULES: s = re.sub(rx, rp, s)
            if s != o: open(p, "w", encoding="utf-8").write(s); changed += 1
            for i, line in enumerate(s.splitlines(), 1):
                if SUSPECT.search(line): rep.write(f"{os.path.relpath(p, assets)}:{i}: {line.strip()[:200]}\n")
    rep.close()
    print("File C# diubah:", changed)
    # buang plugin Windows (x86 dll / exe) agar tidak ikut build Android
    for r, _, fs in os.walk(assets):
        for f in fs:
            if f.lower().endswith((".dll", ".exe")) and ("x86" in r or "Plugins" in r) and "Managed" not in r:
                if f.lower() in ("assimp.dll", "devil.dll", "etctool.exe"):
                    os.remove(os.path.join(r, f))
                    m = os.path.join(r, f + ".meta")
                    if os.path.exists(m): os.remove(m)
    # overlay
    dst = os.path.join(assets, "AndroidPort"); os.makedirs(dst, exist_ok=True)
    shutil.copy(os.path.join(HERE, "AndroidPort.cs"), dst)
    ed = os.path.join(assets, "Editor"); os.makedirs(ed, exist_ok=True)
    shutil.copy(os.path.join(HERE, "AndroidPortBuild.cs"), ed)
    libs = os.path.join(assets, "Plugins", "Android", "libs", "arm64-v8a"); os.makedirs(libs, exist_ok=True)
    for so in os.listdir(native): shutil.copy(os.path.join(native, so), libs)

if __name__ == "__main__":
    c = sys.argv[1]
    if c == "reconstruct": reconstruct(*sys.argv[2:5])
    elif c == "patch": patch(*sys.argv[2:4])
