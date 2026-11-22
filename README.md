# keltuxPlugins

Installable plugins for the **keltux** IDE, and the catalog the IDE's "Get plugins" page reads.

This repo is two things:

1. **The plugin sources** — branded forks of the upstream samples, under `samples/`:

   | Plugin | id | What it adds | Toolchain it carries |
   | --- | --- | --- | --- |
   | `hello-plugin` | `dev.keltux.hello` | The smallest complete plugin: a settings page, a palette command, an editor action, a tool window | none (prebuilt stub `.so`) |
   | `dart-plugin` | `dev.keltux.dart` | Dart + Flutter on device, hot reload, live previews | Dart SDK (Termux) + Flutter |
   | `ndk-plugin` | `dev.keltux.ndk` | C / C++ on device | clang + lld (compiled for Android) |
   | `dotnet-plugin` | `dev.keltux.csharp` | C# on device | .NET runtime + Roslyn |

2. **The catalog** — `index.json`, the list the IDE fetches to show what's installable. It's the same
   shape as the host IDE's Supabase `plugin_catalog` table, so the app reads this file exactly as it
   would a Supabase response. The download URLs point at this repo's
   [`plugins` release](https://github.com/keltux/keltuxPlugins/releases/tag/plugins).

## Building

Plugins can't build standalone — they compile against the host IDE's plugin SPI
(`:plugin-api`, `:plugin-ui-api`, `:build-api`, `:interp-api`) and the `build-logic` convention
plugin, which aren't published as jars. So
[`.github/workflows/build-plugins.yml`](.github/workflows/build-plugins.yml) checks out the
**keltux host IDE** ([keltux/keltux](https://github.com/keltux/keltux)), overlays these branded
plugin sources and the toolchain scripts onto it, and builds each plugin inside that tree.

Run it from the **Actions** tab → **Build plugins** → pick a plugin (`hello` / `dart` / `ndk` /
`csharp`, or `all`) and an ABI. `hello` is quick; `ndk` and `csharp` compile a whole toolchain and
take a while. On success the APKs are attached to the `plugins` release and `index.json` is
refreshed.

## Installing

In the keltux IDE: **Get plugins** → pick one → download → install the APK → **restart the IDE**
(plugins are scanned once, at process start). Or download an APK from the `plugins` release and
install it directly.

### For plugin authors

The three things that make a keltux plugin a plugin (unchanged from upstream — see
`docs/writing-plugins.md` in the host IDE):

| Part | Where |
| --- | --- |
| The packaged manifest, as TOML | `src/main/res/raw/codeassist_plugin.toml` |
| The marker the IDE discovers installed plugins by | the `PLUGIN` intent action + `plugin.manifest` meta-data in `AndroidManifest.xml` |
| The entry points it loads | `entryPoints` / `uiEntryPoints` in the manifest |

The manifest action (`dev.ide.codeassist.action.PLUGIN`) and meta-data
(`dev.ide.codeassist.plugin.manifest`) are **fixed protocol strings** the IDE hardcodes — rebrand a
plugin's package, id and display name freely, but leave those two strings and the
`codeassist_plugin.toml` filename alone, or the IDE won't recognize the APK as a plugin.
