// GeorgianInstaller is an OFFLINE launcher. It performs no network requests.
// It runs the bundled, locally stored CPython interpreter and source installer.
// Build: GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags="-s -w -buildid=" -o GeorgianInstaller.exe GeorgianInstaller.go
package main

import (
    "fmt"
    "os"
    "os/exec"
    "path/filepath"
    "strings"
)

func main() {
    self, err := os.Executable()
    if err != nil { fatal("Cannot locate installer executable: %v", err) }
    root := filepath.Dir(self)
    action := "install"
    if len(os.Args) > 1 { action = strings.ToLower(os.Args[1]) }
    switch action {
    case "--about", "--version":
        fmt.Println("007 First Light Georgian localization - OFFLINE launcher, beta")
        fmt.Println("No downloads, no network access, and no system Python installation.")
        return
    case "install", "uninstall":
    default:
        fatal("Unknown command %q. Usage: GeorgianInstaller.exe [install|uninstall|--about]", action)
    }
    python := filepath.Join(root, "runtime", "python.exe")
    script := filepath.Join(root, "scripts", "installer.py")
    if _, err := os.Stat(python); err != nil {
        fatal("Offline Python runtime not found at: %s\nThis appears to be a BUILD KIT, not a complete release ZIP.\nBuild the offline release before publishing.", python)
    }
    if _, err := os.Stat(script); err != nil { fatal("Mod installer source missing at: %s", script) }
    cmd := exec.Command(python, "-u", script, action)
    cmd.Dir = root
    cmd.Env = append(os.Environ(), "PYTHONIOENCODING=utf-8", "PYTHONUTF8=1", "PYTHONDONTWRITEBYTECODE=1")
    cmd.Stdin, cmd.Stdout, cmd.Stderr = os.Stdin, os.Stdout, os.Stderr
    fmt.Printf("007 First Light - Georgian localization (%s)\n", action)
    fmt.Println("Running entirely offline using bundled open-source components.")
    if err := cmd.Run(); err != nil {
        if ex, ok := err.(*exec.ExitError); ok { os.Exit(ex.ExitCode()) }
        fatal("Could not start bundled Python: %v", err)
    }
}

func fatal(format string, args ...any) {
    fmt.Fprintf(os.Stderr, "ERROR: "+format+"\n", args...)
    os.Exit(1)
}
