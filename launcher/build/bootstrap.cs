using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("Project Meridian Bootstrap")]
[assembly: AssemblyProduct("Project Meridian Launcher")]
[assembly: AssemblyVersion("2.0.0.0")]
[assembly: AssemblyFileVersion("2.0.0.0")]

internal static class Bootstrap
{
    private static string Child(string root, string name)
    {
        string path = Path.GetFullPath(Path.Combine(root, name));
        if (!path.StartsWith(root.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new IOException("Некорректный путь программы.");
        return path;
    }

    private static void Recover(string root)
    {
        string app = Child(root, "app");
        string backup = Child(root, "app.previous");
        string pending = Child(root, "app.update-pending");
        if (!File.Exists(pending)) return;
        foreach (string path in new string[] { app, backup })
            if (Directory.Exists(path) && (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("Связанные каталоги программы не поддерживаются.");
        if (Directory.Exists(backup))
        {
            if (Directory.Exists(app)) Directory.Move(app, Child(root, "app.failed-" + Guid.NewGuid().ToString("N")));
            Directory.Move(backup, app);
        }
        if (!File.Exists(Path.Combine(app, "Project-Meridian-Launcher.exe")))
            throw new IOException("Не удалось восстановить лаунчер. Запустите установщик повторно.");
        File.Delete(pending);
    }

    private static string Quote(string argument)
    {
        StringBuilder result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char character in argument)
        {
            if (character == '\\') { slashes++; continue; }
            if (character == '"')
            {
                result.Append('\\', slashes * 2 + 1);
                result.Append('"');
            }
            else
            {
                result.Append('\\', slashes);
                result.Append(character);
            }
            slashes = 0;
        }
        result.Append('\\', slashes * 2);
        result.Append('"');
        return result.ToString();
    }

    [STAThread]
    private static int Main(string[] arguments)
    {
        using (Mutex gate = new Mutex(false, @"Local\ProjectMeridianLauncherUpdate"))
        {
            bool acquired = false;
            try
            {
                try { acquired = gate.WaitOne(0); }
                catch (AbandonedMutexException) { acquired = true; }
                if (!acquired) throw new IOException("Обновление лаунчера ещё выполняется. Повторите запуск после его завершения.");
                string root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                Recover(root);
                StringBuilder command = new StringBuilder();
                foreach (string argument in arguments) command.Append(Quote(argument)).Append(' ');
                ProcessStartInfo settings = new ProcessStartInfo(Child(root, @"app\Project-Meridian-Launcher.exe"), command.ToString());
                settings.UseShellExecute = false;
                settings.CreateNoWindow = true;
                settings.WorkingDirectory = root;
                using (Process child = Process.Start(settings))
                {
                    gate.ReleaseMutex();
                    acquired = false;
                    if (arguments.Length > 0)
                    {
                        child.WaitForExit();
                        return child.ExitCode;
                    }
                }
                return 0;
            }
            catch (Exception error)
            {
                MessageBox.Show(error.Message, "Project Meridian Launcher", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
            finally { if (acquired) gate.ReleaseMutex(); }
        }
    }
}
