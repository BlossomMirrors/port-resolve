#!/bin/bash
####
# Make every file with the given extension in the current directory
# importable into DaVinci Resolve (free version supports neither H.264/H.265
# video decode nor AAC audio decode). Probes each stream and only re-encodes
# what's actually incompatible:
#   - video already in a supported codec (DNxHD/DNxHR, ProRes, etc.) -> copied
#     as-is; otherwise re-encoded to ProRes (prores_ks).
#   - audio already PCM -> copied as-is; otherwise re-encoded to PCM.
# Output goes to ./converted/<name>.mov.
#
# See: https://wiki.nobaraproject.org/general-usage/additional-software/davinci-resolve
#
# Usage: ./convert_for_resolve.sh [extension]
#   extension defaults to .mp4. Pass e.g. ".mkv" for other containers.
####
EXT="${1:-.mp4}"
SUPPORTED_VIDEO_RE='^(dnxhd|prores|mjpeg|rawvideo|ffv1|cfhd)$'

mkdir -p converted
for f in *"$EXT"; do
    [ -e "$f" ] || continue
    NAME="${f%"$EXT"}"

    vcodec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$f")
    acodec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$f")

    if [[ "$vcodec" =~ $SUPPORTED_VIDEO_RE ]]; then
        vopts=(-c:v copy)
    else
        # The freedesktop.org runtime's ffmpeg build excludes ProRes encoders
        # (patent-encumbered), so re-encode to DNxHR instead, which ffmpeg
        # does ship and which Resolve treats as natively supported.
        echo "${f}: re-encoding video (${vcodec} -> dnxhr)"
        vopts=(-c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p)
    fi

    if [[ "$acodec" == pcm_* ]]; then
        aopts=(-c:a copy)
    else
        echo "${f}: re-encoding audio (${acodec} -> pcm)"
        aopts=(-c:a pcm_s24le)
    fi

    ffmpeg -i "$f" "${vopts[@]}" "${aopts[@]}" -f mov "converted/${NAME}.mov"
done
