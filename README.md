

resolve-flatpak
===============

This repo allows you to package DaVinci Resolve as a Flatpak for use on Linux Flatpak
based systems, especially e.g. Fedora Silverblue where there aren't easier installation
options. 

Usage
-----

1. If you have appimagelauncherd (the AppImage Launcher daemon) installed and enabled, you NEED to temporarely disable it (either through systemctl or through the AppImage Launcher GUI) as it conflicts with flatpak-builder during the .run file repackaging process.

2. Clone this repo with: `git clone https://github.com/pobthebuilder/resolve-flatpak.git --recursive`
By default, com.blackmagic.Resolve.yaml is configured to package the latest version of Resolve (18.5 Beta 3 at the time of writing).

3. Build your package, and export to a distributable single file installer:

#### Free
```
flatpak-builder --install-deps-from=flathub --force-clean --repo=.repo .build-dir com.blackmagic.Resolve.yaml
```

To simply install the built version:
```
flatpak --user remote-add --no-gpg-verify resolve-repo .repo
flatpak --user install resolve-repo com.blackmagic.Resolve
```

To build a redistruble single file package:
```
flatpak build-bundle .repo resolve.flatpak com.blackmagic.Resolve --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo
```

#### Studio
```
flatpak-builder --install-deps-from=flathub --force-clean --repo=.repo .build-dir com.blackmagic.ResolveStudio.yaml
```

To simply install the built version:
```
flatpak --user remote-add --no-gpg-verify resolve-repo .repo
flatpak --user install resolve-repo com.blackmagic.ResolveStudio
```

To build a redistruble single file package:
```
flatpak build-bundle .repo resolve.flatpak com.blackmagic.ResolveStudio --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo
```

4. Enjoy.

## udev rules (Resolve Studio)
On some distros, you may need to add udev rules to enable Resolve Studio to access your USB licence key, otherwise Resolve will segfault at the "Checking Licences..." splash screen. An example udev rule is below:

```
# Allow Flatpak apps to access USB devices with vendor ID 096e (Feitan Technologies), needed by DaVinci Resolve Studio when using USB licence keys
# Place this file in /etc/udev/rules.d/
# Recommended file name: 99-davinci-usb.rules

SUBSYSTEM=="usb", ATTR{idVendor}=="096e", TAG+="uaccess"
SUBSYSTEM=="usb", ATTR{idVendor}=="096e", MODE="0664", GROUP="plugdev"
```

## Codec support & known limitations
See also: [Nobara Project wiki: DaVinci Resolve](https://wiki.nobaraproject.org/general-usage/additional-software/davinci-resolve), which documents these same limitations for a native (non-Flatpak) install.

- **H.264/H.265 decode**: the free version of Resolve cannot decode H.264/H.265 at all (you'll see `Codec (avc1) not Found in Repository` in the logs). Hardware-accelerated decode of these formats is a Studio-only feature, and on AMD it additionally requires the `rocm-meta` package (`rocm-opencl` + `opencl-filesystem`) installed on the **host** — this is outside what the Flatpak can provide. Note that AMD dropped ROCm support for older (pre-RDNA) GPUs such as the Polaris-based RX 400/500 series some years ago, so `rocm-opencl` will report 0 usable devices on those cards regardless of how it's installed.
- **H.264/H.265 encode**: hardware encode is Nvidia-only via CUDA, and requires the `cuda-devel` host package (or the equivalent entry in the Nobara Driver Manager). There is no built-in software (CPU) H.264/H.265/ProRes encoder in either version of Resolve, see Plugins below for a free community workaround.
- **AAC audio**: not supported for import in either version. A typical screen-recording `.mp4` (H.264 video + AAC audio) needs *both* re-encoded, not just the audio — [`shell/convert_for_resolve.sh`](shell/convert_for_resolve.sh) probes each file and only re-encodes what's actually incompatible (video to ProRes if it isn't already DNxHD/ProRes/etc., audio to PCM if it isn't already PCM): `./convert_for_resolve.sh .mp4`.
- **Laptops with iGPU + dGPU**: Resolve renders in OpenGL and needs to be pointed at the discrete GPU explicitly. See the Nobara wiki's [Nvidia](https://wiki.nobaraproject.org/graphics/nvidia/gpu-selection-in-igpu-plus-dgpu-setup) and [AMD](https://wiki.nobaraproject.org/graphics/amd/gpu-selection-in-igpu-plus-dgpu-setup) pages for the relevant environment variables; these aren't currently wired into this Flatpak's manifests.

Resolve doesn't surface these codec errors in its UI. An incompatible import just silently vanishes from the timeline with no preview, with the actual reason only visible in its debug log. Run [`shell/notify_codec_errors.sh`](shell/notify_codec_errors.sh) (named "Arc Compat") alongside Resolve to get a KDE dialog the moment Resolve logs one of these errors, showing the exact `convert_for_resolve.sh` command to fix that file plus an "Open Docs" button that opens this README instead of having to dig through `~/.var/app/com.blackmagic.Resolve/data/logs/ResolveDebug.txt` yourself:

```
./shell/notify_codec_errors.sh                       # free
./shell/notify_codec_errors.sh com.blackmagic.ResolveStudio
```

## Plugins
Davinci Resolve Flatpak now supports bundling IOPlugins as Flatpak Extensions so they can be trivially installed.

For an example; the publically available ffmpeg IOPlugin is available packaged as a Flatpak extension here:
https://github.com/pobthebuilder/resolve-ffmpeg-plugin-flatpak

### Free x264/x265/ProRes + VAAPI encode plugins
The free version of Resolve has no software H.264/H.265/ProRes encoder. The manifests in [`ioplugins/`](ioplugins/) package the free community plugins documented on the Nobara wiki as installable Flatpak extensions, one per `.dvcp.bundle`, since Flatpak extension IDs can't contain dots, so each is built as `..._dvcp_bundle` and renamed back to `....dvcp.bundle` in the exported metadata (the same approach used by [resolve-ffmpeg-plugin-flatpak](https://github.com/pobthebuilder/resolve-ffmpeg-plugin-flatpak)).

Build, export and install all of them for an app that's already built and installed (requires that app's manifest to declare the matching `add-extensions: <app-id>.ioplugin` block, which both manifests in this repo do):

```
./shell/build_ioplugins.sh com.blackmagic.Resolve        # free
./shell/build_ioplugins.sh com.blackmagic.ResolveStudio  # Studio
```

This installs CPU x264/x265/ProRes encode plus AMD/Intel VAAPI H.264/H.265/AV1 GPU encode into `/app/IOPlugins`.

## Finding explicit Download IDs (for download_resolve.sh)
#### Studio:

```
curl -o- https://www.blackmagicdesign.com/api/support/nz/downloads.json |
    jq -r '.downloads[]
            | select(.urls["Linux"] != null)
            | select(.urls["Linux"][0]["product"] == "davinci-resolve-studio")
            | [.urls["Linux"][0].downloadTitle, .urls["Linux"][0].downloadId]
            | @tsv'
```

#### Free:

```
curl -o- https://www.blackmagicdesign.com/api/support/nz/downloads.json |
    jq -r '.downloads[]
            | select(.urls["Linux"] != null)
            | select(.urls["Linux"][0]["product"] == "davinci-resolve")
            | [.urls["Linux"][0].downloadTitle, .urls["Linux"][0].downloadId]
            | @tsv'
```

## Licensing
The icon in logo.png is licensed under the Creative [Commons Attribution-Share Alike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/deed.en) and fetched from [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:DaVinci_Resolve_Studio.png). It was only cropped afterwards.

## Related

- [Flathub forum : DaVinci Resolve Feature Requests](https://discourse.flathub.org/t/davinci-resolve-flatpak-request/842)
- [blackmagicdesign forum : DaVinci Resolve Flatpak request](https://forum.blackmagicdesign.com/viewtopic.php?f=33&t=186259)
