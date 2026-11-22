#!/usr/bin/env python3
"""
Generate index.json for the keltux "Get plugins" page.

Scans every samples/*/src/main/res/raw/codeassist_plugin.toml (the plugin's own manifest), pairs each
with the APK built for it in --dist, and writes an index.json whose rows are the same shape as the
host IDE's Supabase `plugin_catalog` table — so GitHubPluginCatalog parses this file exactly as it
would a Supabase response, and the page can't tell the difference.

Per-ABI plugins (Dart / NDK / C#, one APK per device ABI) are written into `abi_downloads`
({"arm64-v8a": {"url": ..., "size": ...}, ...}) so the IDE offers this device's build; universal
plugins (Hello) use the plain `download_url`. The download URLs point at the release assets uploaded
by build-plugins.yml, so they stay valid across runs.
"""

import argparse
import glob
import json
import os
import re
import sys


def parse_toml(path):
    """Pull the fields index.json needs out of a plugin manifest. Hand-rolled: the toml is flat and
    the CI runner has no tomllib dependency guaranteed on the host Python; this reads just the keys."""
    with open(path, encoding="utf-8") as f:
        text = f.read()

    def scalar(key):
        m = re.search(rf'^{key}\s*=\s*"([^"]*)"', text, re.M)
        return m.group(1) if m else ""

    # capabilities is a multi-line array of quoted strings.
    caps = []
    m = re.search(r"^capabilities\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if m:
        caps = re.findall(r'"([^"]*)"', m.group(1))

    return {
        "id": scalar("id"),
        "name": scalar("name"),
        "version": scalar("version"),
        "description": scalar("description"),
        "min_host_version": scalar("minHostVersion") or None,
        "capabilities": caps,
    }


# Which dist APK belongs to which plugin, by a substring of the built filename.
PLUGIN_APK_MATCH = {
    "dev.keltux.hello": "keltux-Hello-",
    "dev.keltux.dart": "keltux-Dart-",
    "dev.keltux.ndk": "keltux-NDK-",
    "dev.keltux.csharp": "keltux-CSharp-",
}

# Short "what it's for" label, shown on the page (the languages column).
PLUGIN_LANGUAGES = {
    "dev.keltux.hello": "Sample",
    "dev.keltux.dart": "Dart · Flutter",
    "dev.keltux.ndk": "C / C++",
    "dev.keltux.csharp": "C# · .NET",
}

# One-line tagline (the page's subtitle). The manifest description is long; this is the short pitch.
PLUGIN_TAGLINE = {
    "dev.keltux.hello": "The smallest complete keltux plugin: a settings page, a command, an editor action, a tool window.",
    "dev.keltux.dart": "Dart and Flutter on your phone, with hot reload and live previews.",
    "dev.keltux.ndk": "C and C++ on your phone, with clang and lld built in.",
    "dev.keltux.csharp": "C# on your phone, with .NET and the Roslyn compiler built in.",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default="host/samples", help="root of the overlaid plugin sources")
    ap.add_argument("--dist", required=True, help="directory of built APKs")
    ap.add_argument("--repo", required=True, help="owner/repo the release lives in")
    ap.add_argument("--tag", default="plugins", help="release tag holding the APKs")
    ap.add_argument("--out", default="index.json", help="output path")
    args = ap.parse_args()

    def asset_url(filename):
        return f"https://github.com/{args.repo}/releases/download/{args.tag}/{filename}"

    rows = []
    for toml_path in sorted(glob.glob(os.path.join(args.samples, "*", "src", "main", "res", "raw", "codeassist_plugin.toml"))):
        meta = parse_toml(toml_path)
        pid = meta["id"]
        if not pid:
            continue
        match = PLUGIN_APK_MATCH.get(pid)
        if not match:
            continue

        # Collect every APK built for this plugin: name -> size.
        apks = {}
        for apk in glob.glob(os.path.join(args.dist, "*.apk")):
            base = os.path.basename(apk)
            if base.startswith(match):
                apks[base] = os.path.getsize(apk)
        if not apks:
            print(f"warning: no APK for {pid} (looked for {match}*)", file=sys.stderr)
            continue

        # ABI-suffixed APKs go into abi_downloads ({"arm64-v8a": {...}}); a universal APK (no ABI in
        # its name) is the plain download_url.
        abi_re = re.compile(r"-(arm64-v8a|armeabi-v7a|x86_64|x86)\.apk$")
        abi_downloads = {}
        universal = None
        for base, size in apks.items():
            m = abi_re.search(base)
            if m:
                abi_downloads[m.group(1)] = {"url": asset_url(base), "size": size}
            else:
                universal = (asset_url(base), size)

        row = {
            "id": pid,
            "name": meta["name"],
            "tagline": PLUGIN_TAGLINE.get(pid, ""),
            "description": meta["description"],
            "publisher": "keltux",
            "version": meta["version"],
            "min_host_version": meta["min_host_version"],
            "languages": PLUGIN_LANGUAGES.get(pid, ""),
            "capabilities": meta["capabilities"],
            "page_url": f"https://github.com/{args.repo}",
        }
        if abi_downloads:
            # size_bytes: the build for the device's preferred ABI, as a fallback for older apps.
            preferred = abi_downloads.get("arm64-v8a") or next(iter(abi_downloads.values()))
            row["size_bytes"] = preferred["size"]
            row["abi_downloads"] = abi_downloads
            row["download_url"] = preferred["url"]
        elif universal:
            row["download_url"] = universal[0]
            row["size_bytes"] = universal[1]
        else:
            continue

        rows.append(row)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {args.out} with {len(rows)} plugin(s)")


if __name__ == "__main__":
    main()
