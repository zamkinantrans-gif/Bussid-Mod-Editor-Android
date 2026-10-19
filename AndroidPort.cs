using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

// Ditaruh di ROOT repo (port.py menyalinnya ke project/Assets/Editor).
// Argumen opsional lewat customParameters game-ci:  -portBackend mono   (default: il2cpp)
public static class AndroidPortBuild
{
    static string Arg(string name, string def)
    {
        var a = Environment.GetCommandLineArgs();
        for (int i = 0; i < a.Length - 1; i++) if (a[i] == name) return a[i + 1];
        return def;
    }

    public static void Build()
    {
        try
        {
            PlayerSettings.productName = "BUSSID Mod Editor";
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android, "id.port.bussidmodeditor");
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel24;
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.LandscapeLeft;
            PlayerSettings.SetStackTraceLogType(LogType.Log, StackTraceLogType.None);

            // Kode hasil decompile banyak memakai refleksi; stripping bisa merusaknya.
            PlayerSettings.stripEngineCode = false;
            PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.Android, ManagedStrippingLevel.Disabled);

            bool mono = Arg("-portBackend", "il2cpp").ToLowerInvariant() == "mono";
            if (mono)
            {
                // Untuk memeriksa apakah IL2CPP penyebab crash (assembly obfuscated yang sangat besar).
                PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.Mono2x);
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64;
            }
            else
            {
                PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            }
            Debug.Log("[AndroidPortBuild] backend=" + (mono ? "Mono" : "IL2CPP"));

            var scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
            if (scenes.Length == 0)
            {
                scenes = Directory.GetFiles("Assets", "*.unity", SearchOption.AllDirectories);
                Debug.LogWarning("[AndroidPortBuild] Tidak ada scene aktif di Build Settings; memakai semua scene: " + scenes.Length);
            }
            if (scenes.Length == 0)
            {
                Debug.LogError("[AndroidPortBuild] Tidak ada scene sama sekali.");
                EditorApplication.Exit(1);
                return;
            }

            var dir = Arg("-customBuildPath", "build/Android");
            Directory.CreateDirectory(dir);

            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = Path.Combine(dir, Arg("-customBuildName", "BUSSIDModEditor") + ".apk"),
                target = BuildTarget.Android,
                options = BuildOptions.None
            });

            var sum = report.summary;
            Debug.Log("[AndroidPortBuild] result=" + sum.result + " errors=" + sum.totalErrors + " warnings=" + sum.totalWarnings);
            if (sum.result != BuildResult.Succeeded)
            {
                foreach (var step in report.steps)
                    foreach (var m in step.messages)
                        if (m.type == LogType.Error || m.type == LogType.Exception)
                            Debug.LogError("[AndroidPortBuild] " + m.content);
                EditorApplication.Exit(1);
                return;
            }
            EditorApplication.Exit(0);
        }
        catch (Exception e)
        {
            Debug.LogError("[AndroidPortBuild] GAGAL: " + e);
            EditorApplication.Exit(1);
        }
    }
}
