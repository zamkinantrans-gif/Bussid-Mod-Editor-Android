using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEditor.Build.Reporting;

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
        PlayerSettings.productName = "BUSSID Mod Editor";
        PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android, "id.port.bussidmodeditor");
        PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
        PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
        PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel24;
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.LandscapeLeft;
        PlayerSettings.SetStackTraceLogType(LogType.Log, StackTraceLogType.None);

        var dir = Arg("-customBuildPath", "build/Android");
        Directory.CreateDirectory(dir);
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray(),
            locationPathName = Path.Combine(dir, Arg("-customBuildName", "BUSSIDModEditor") + ".apk"),
            target = BuildTarget.Android,
            options = BuildOptions.None
        });
        EditorApplication.Exit(report.summary.result == BuildResult.Succeeded ? 0 : 1);
    }
}
