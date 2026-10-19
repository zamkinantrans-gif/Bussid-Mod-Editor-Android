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
               if f.startswith("AssetRipper") and "." not in f.replace("AssetRipper.GUI.Free", "")
               and not f.endswith((".dll", ".pdb", ".json", ".xml")))
    os.chmod(exe, 0o755)
    print("Executable:", exe)
    try: print(subprocess.run([exe, "--help"], capture_output=True, text=True, timeout=30).stdout[:2000])
    except Exception as e: print("--help gagal:", e)
    export = os.path.abspath("ripped"); shutil.rmtree(export, ignore_errors=True)
    proc = subprocess.Popen([exe, "--headless", "--port", str(PORT)])
    try:
        import re as _re
        for _ in range(90):  # tunggu server siap
            if proc.poll() is not None: sys.exit(f"AssetRipper berhenti dengan kode {proc.returncode}")
            try:
                html = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=2).read().decode("utf-8", "replace")
                print("Server siap. action/href di halaman utama:",
                      sorted(set(_re.findall(r'(?:action|href|hx-post|hx-get)="([^"]+)"', html)))[:60])
                break
            except Exception: time.sleep(1)
        else: sys.exit("Server AssetRipper tidak naik dalam 90 detik")
        # Endpoint/nama field AssetRipper 1.x; belum diverifikasi, coba dua kapitalisasi.
        for key in ("path", "Path"):
            try: _post("/LoadFolder", {key: os.path.abspath(game)}); break
            except urllib.error.HTTPError as e: print("LoadFolder", key, e, e.read()[:500])
        for key in ("path", "Path"):
            try: _post("/Export/UnityProject", {key: export}); break
            except urllib.error.HTTPError as e: print("Export", key, e, e.read()[:500])
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
    (r'(?<![A-Za-z_])(?:System\.Diagnostics\.)?Process\.Start\(', 'AndroidShim.Start('),
    # enum usang yang menjadi error CS0619 di Unity 2021
    (r'RuntimePlatform\.WindowsWebPlayer\b', '((RuntimePlatform)(-9001))'),
    (r'RuntimePlatform\.OSXDashboardPlayer\b', '((RuntimePlatform)(-9002))'),
    # array berukuran negatif literal (umpan obfuscator) -> CS0248
    (r'new\s+([A-Za-z_][\w\.<>,]*)\[\s*-\s*\d+\s*\]', r'new \1[0]'),
]
SUSPECT = re.compile(r'DllImport|Process\b|ProcessStartInfo|explorer\.exe|etctool|Devil|assimp|'
                     r'System\.Windows|Microsoft\.Win32|OpenFileName|\.exe\b|FileBrowser|'
                     r'Directory\.GetLogicalDrives|DriveInfo')

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
    snippets(project)

def snippets(project):
    """Tulis port-snippets.txt: potongan kode yang dibutuhkan untuk menulis pengganti native."""
    assets = os.path.join(project, "Assets"); out = open("port-snippets.txt", "w", encoding="utf-8")
    files = []
    for r, _, fs in os.walk(assets):
        if "AndroidPort" in r or os.sep + "Editor" in r: continue
        for f in fs:
            if f.endswith(".cs"):
                p = os.path.join(r, f); files.append((p, open(p, encoding="utf-8-sig", errors="replace").read().splitlines()))
    def rel(p): return os.path.relpath(p, assets)
    out.write("##### A. Process / etctool (konteks)\n")
    for p, L in files:
        if not any("new Process()" in l or "etctool" in l for l in L): continue
        last = -99
        for i, l in enumerate(L):
            if ("new Process()" in l or "etctool" in l) and i > last + 30:
                out.write(f"--- {rel(p)}:{i+1}\n" + "\n".join(L[max(0, i-6):i+30]) + "\n"); last = i
    for lib, tag in (("assimp", "B"), ("Devil", "C")):
        out.write(f"\n##### {tag}. Deklarasi DllImport {lib}\n")
        for p, L in files:
            for i, l in enumerate(L):
                if f'DllImport("{lib}"' in l:
                    ent = re.search(r'EntryPoint = "([^"]+)"', l)
                    sig = " ".join(x.strip() for x in L[i+1:i+4]); sig = sig.split(";")[0]
                    out.write(f"{ent.group(1) if ent else '?'} :: {sig}\n")
    # pemanggil Devil
    out.write("\n##### E. Konteks error kompilasi Unity\n")
    ERR = [("BSITCar.cs",5292),("BSITCar.cs",10351),("MeshSplit.cs",108),("MeshSplit.cs",4611),("FrictionPreset.cs",68),
           ("AssetLoaderWindow.cs",163),("VehicleCustomAnimations.cs",757),("VehicleCustomAnimations.cs",768),
           ("EditableMaterials.cs",808),("Model.cs",720),("UIInspector.cs",491),("MapObjectDataPart.cs",323)]
    for name, ln in ERR:
        for p, L in files:
            if os.path.basename(p) == name:
                out.write(f"--- {name}:{ln}\n" + "\n".join(f"{i+1}: {L[i][:260]}" for i in range(max(0, ln-6), min(len(L), ln+5))) + "\n")
    out.write("\n##### D. Pemanggil Devil (nama kelas DllImport)\n")
    for p, L in files:
        if any('DllImport("Devil"' in l for l in L):
            m = next((re.search(r'class\s+(\S+)', l) for l in L if re.search(r'\bclass\s+\S+', l)), None)
            if not m: continue
            cname = m.group(1)
            for q, M in files:
                if q == p: continue
                for i, l in enumerate(M):
                    if re.search(re.escape(cname) + r'\.il[A-Z]', l): out.write(f"{rel(q)}:{i+1}: {l.strip()[:220]}\n")
    out.close()

if __name__ == "__main__":
    c = sys.argv[1]
    if c == "reconstruct": reconstruct(*sys.argv[2:5])
    elif c == "patch": patch(*sys.argv[2:4])
