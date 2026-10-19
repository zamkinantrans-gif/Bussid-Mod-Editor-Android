// Lapisan kompatibilitas Android untuk BUSSID Mod Editor (belum dikompilasi/diuji).
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using UnityEngine;

// Pengganti kelas <PrivateImplementationDetails> milik compiler (dipakai untuk switch string).
// Hash FNV-1a 32-bit, sama dengan ComputeStringHash bawaan Roslyn.
internal static class _003CPrivateImplementationDetails_003E
{
    internal static uint ComputeStringHash(string s)
    {
        uint h = 2166136261u;
        if (s != null) for (int i = 0; i < s.Length; i++) h = (s[i] ^ h) * 16777619u;
        return h;
    }
}

public static class AndroidPaths
{
    // Android/data/<package>/files/BUSSID (taruh .bussidmod dan model di sini)
    public static string Root { get { return Ensure(Path.Combine(Application.persistentDataPath, "BUSSID")); } }
    public static string Mods { get { return Ensure(Path.Combine(Root, "Mods")); } }
    static string Ensure(string p) { try { if (!Directory.Exists(p)) Directory.CreateDirectory(p); } catch { } return p; }
}

// Pengganti Process.Start (explorer.exe dll.) - tidak melakukan apa pun di Android.
public static class AndroidShim
{
    public static System.Diagnostics.Process Start(string file, string args)
    { Debug.Log("[AndroidPort] Process.Start diabaikan: " + file); return null; }

    public static System.Diagnostics.Process Start(string file)
    { return Start(file, null); }

    public static System.Diagnostics.Process Start(System.Diagnostics.ProcessStartInfo info)
    { return Start(info != null ? info.FileName : null, info != null ? info.Arguments : null); }
}

// Pengganti etctool.exe: encoder Etc2Comp (libetcwrap.so).
public static class EtcNative
{
    [DllImport("etcwrap")] static extern int etc_encode(byte[] rgba, uint w, uint h, int fmt, float effort, out IntPtr bits, out uint nbytes);
    [DllImport("etcwrap")] static extern void etc_free(IntPtr p);

    // fmt: 0=ETC1, 1=RGB8 (ETC2), 2=RGBA8 (ETC2 EAC). rgba = w*h*4 byte.
    public static byte[] Encode(byte[] rgba, int w, int h, int fmt = 0, float effort = 50f)
    {
        IntPtr bits; uint n;
        etc_encode(rgba, (uint)w, (uint)h, fmt, effort, out bits, out n);
        var res = new byte[n]; Marshal.Copy(bits, res, 0, (int)n); etc_free(bits);
        return res;
    }
}

// Pengganti hotkey keyboard (tombol di layar) dan mouse (1 jari = klik kiri,
// 2 jari = klik kanan, cubit = scroll).
public static class VirtualKeys
{
    public static readonly HashSet<KeyCode> Sticky = new HashSet<KeyCode>();
    static readonly Dictionary<KeyCode, int> pressFrame = new Dictionary<KeyCode, int>();
    public static void Tap(KeyCode k) { pressFrame[k] = Time.frameCount + 1; }
    public static bool Down(KeyCode k) { int f; return pressFrame.TryGetValue(k, out f) && f == Time.frameCount; }
    public static bool Up(KeyCode k) { int f; return pressFrame.TryGetValue(k, out f) && f + 1 == Time.frameCount; }
    public static bool Held(KeyCode k) { return Sticky.Contains(k) || Down(k); }
}

// Dinamai PortInput (bukan AndroidInput) karena UnityEngine.AndroidInput sudah ada di Unity.
public static class PortInput
{
    static int frame = -1; static bool two, prevTwo; static float prevDist, scroll;
    public static void Tick()
    {
        if (frame == Time.frameCount) return; frame = Time.frameCount;
        prevTwo = two; two = Input.touchCount >= 2; scroll = 0f;
        if (two)
        {
            float d = Vector2.Distance(Input.GetTouch(0).position, Input.GetTouch(1).position);
            if (prevTwo) scroll = (d - prevDist) * 0.02f;
            prevDist = d;
        }
    }
    public static bool GetKey(KeyCode k) { return Input.GetKey(k) || VirtualKeys.Held(k); }
    public static bool GetKeyDown(KeyCode k) { return Input.GetKeyDown(k) || VirtualKeys.Down(k); }
    public static bool GetKeyUp(KeyCode k) { return Input.GetKeyUp(k) || VirtualKeys.Up(k); }
    public static bool GetMouseButton(int b) { Tick(); return b == 0 ? (!two && Input.GetMouseButton(0)) : b == 1 ? (two || Input.GetMouseButton(1)) : Input.GetMouseButton(b); }
    public static bool GetMouseButtonDown(int b) { Tick(); return b == 0 ? (!two && Input.GetMouseButtonDown(0)) : b == 1 ? ((two && !prevTwo) || Input.GetMouseButtonDown(1)) : Input.GetMouseButtonDown(b); }
    public static bool GetMouseButtonUp(int b) { Tick(); return b == 1 ? ((!two && prevTwo) || Input.GetMouseButtonUp(1)) : Input.GetMouseButtonUp(b); }
    public static Vector2 mouseScrollDelta { get { Tick(); return new Vector2(0f, scroll + Input.mouseScrollDelta.y); } }
    public static float ScrollWheel { get { return mouseScrollDelta.y; } }
}

public class VirtualKeyBar : MonoBehaviour
{
    static readonly KeyCode[] keys = { KeyCode.B, KeyCode.C, KeyCode.F, KeyCode.G, KeyCode.W, KeyCode.A,
        KeyCode.X, KeyCode.Y, KeyCode.Z, KeyCode.Delete, KeyCode.Escape, KeyCode.Return, KeyCode.Tab };
    static readonly KeyCode[] sticky = { KeyCode.LeftShift, KeyCode.LeftControl };
    bool open = true;

    void Update() { PortInput.Tick(); }

    void OnGUI()
    {
        float s = Mathf.Clamp(Screen.dpi / 160f, 1f, 3f);
        GUI.matrix = Matrix4x4.Scale(new Vector3(s, s, 1));
        float W = Screen.width / s, H = Screen.height / s, bw = 52, bh = 38, x = 0, y = H - bh;
        if (GUI.Button(new Rect(W - 60, H - bh - 40, 56, 36), open ? "KEYS-" : "KEYS+")) open = !open;
        if (!open) return;
        foreach (var k in keys)
        {
            if (x + bw > W - 64) { x = 0; y -= bh; }
            if (GUI.Button(new Rect(x, y, bw, bh), Label(k))) VirtualKeys.Tap(k);
            x += bw;
        }
        foreach (var k in sticky)
        {
            if (x + bw > W - 64) { x = 0; y -= bh; }
            bool on = VirtualKeys.Sticky.Contains(k);
            if (GUI.Toggle(new Rect(x, y, bw, bh), on, k == KeyCode.LeftShift ? "Shift" : "Ctrl", "Button") != on)
            { if (on) VirtualKeys.Sticky.Remove(k); else VirtualKeys.Sticky.Add(k); }
            x += bw;
        }
    }
    static string Label(KeyCode k) { return k == KeyCode.Delete ? "Del" : k == KeyCode.Escape ? "Esc" : k == KeyCode.Return ? "Enter" : k.ToString(); }
}

static class AndroidBootstrap
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Init()
    {
        Application.targetFrameRate = 60;
        Screen.sleepTimeout = SleepTimeout.NeverSleep;
        Input.simulateMouseWithTouches = true;
        var _ = AndroidPaths.Mods;
        var go = new GameObject("AndroidPort"); UnityEngine.Object.DontDestroyOnLoad(go);
        go.AddComponent<VirtualKeyBar>();
    }
}
