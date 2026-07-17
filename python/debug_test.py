#!/usr/bin/env python3
"""
Debug test: fresh project, import DNxHR clip, drop to timeline, verify.
Run inside the Resolve sandbox via flatpak enter.
"""
import os
import sys
import time

sys.path.insert(0, "/app/Developer/Scripting/Modules")
os.environ.setdefault("RESOLVE_SCRIPT_LIB", "/app/libs/Fusion/fusionscript.so")

try:
    import DaVinciResolveScript as dvr
except Exception as e:
    print(f"[FAIL] scripting module: {e}")
    sys.exit(2)

print("[...] connecting...")
resolve = None
for _ in range(30):
    try:
        resolve = dvr.scriptapp("Resolve")
        if resolve:
            break
    except Exception:
        pass
    time.sleep(1)

if not resolve:
    print("[FAIL] no connection. EXTERNAL_SCRIPTING_MODE=1 not active?")
    sys.exit(1)

print(f"[OK ] {resolve.GetProductName()} {resolve.GetVersionString()}")

pm = resolve.GetProjectManager()

# Close whatever is open, start completely fresh
current = pm.GetCurrentProject()
if current:
    pm.CloseProject(current)
    time.sleep(1)

proj = pm.CreateProject("_debug_test_")
if not proj:
    print("[FAIL] CreateProject returned None")
    sys.exit(3)

opened = pm.OpenProject("_debug_test_")
if not opened:
    print("[WARN] OpenProject returned None, using CreateProject result")
    opened = proj

print(f"[OK ] project: {opened.GetName()}")

mp = opened.GetMediaPool()
ms = resolve.GetMediaStorage()

TEST_FILE = "/var/home/vaporvee/Downloads/ScreenCoach3_test.mov"
if not os.path.exists(TEST_FILE):
    print(f"[FAIL] test file missing: {TEST_FILE}")
    sys.exit(4)

print(f"[...] importing {os.path.basename(TEST_FILE)}")
items = ms.AddItemListToMediaPool([TEST_FILE])
if not items:
    print("[FAIL] import returned empty")
    sys.exit(5)

clip = items[0]
vcodec = clip.GetClipProperty("Video Codec")
acodec = clip.GetClipProperty("Audio Codec")
res    = clip.GetClipProperty("Resolution")
fps    = clip.GetClipProperty("FPS")
print(f"[OK ] clip: {clip.GetName()}")
print(f"       video={vcodec!r}  audio={acodec!r}  res={res}  fps={fps}")

if not vcodec:
    print("[FAIL] video codec empty. Decoder not working")
    sys.exit(6)

print("[...] creating timeline")
tl = mp.CreateEmptyTimeline("_debug_tl_")
if not tl:
    print("[FAIL] CreateEmptyTimeline returned None")
    sys.exit(7)
print(f"[OK ] timeline: {tl.GetName()}")

print("[...] appending clip to timeline")
result = mp.AppendToTimeline([{"mediaPoolItem": clip, "startFrame": 0, "endFrame": 29}])
if not result:
    # fallback: try simple form
    result = mp.AppendToTimeline([clip])

if not result:
    print("[FAIL] AppendToTimeline returned empty... Timeline drop broken")
    sys.exit(8)

ti = result[0]
dur = ti.GetDuration()
print(f"[OK ] timeline item: {ti.GetName()}  duration={dur}f")

# Verify it actually stayed on the timeline
tl_items = tl.GetItemListInTrack("video", 1)
print(f"[OK ] items on V1: {len(tl_items) if tl_items else 0}")

if tl_items:
    print("\n[PASS] Everything works. Import + timeline are functional.")
else:
    print("\n[FAIL] Clip not on timeline after AppendToTimeline.")
    sys.exit(9)
