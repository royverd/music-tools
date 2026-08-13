"""
Music Library Tools

Fixes common issues with local music libraries downloaded from Spotify/YouTube:
  - Raw AAC streams with no container → wraps in M4A via ffmpeg
  - MP4 files mislabeled as .mp3 → renames to .m4a
  - Missing genre tags → writes genre from parent folder name

Config (music folder path) persists in music_tools_config.json next to the script.
Requires: mutagen, imageio-ffmpeg (for container fixing only)
"""

import json
import subprocess
from pathlib import Path
from mutagen import File

# lives next to the script so it travels with it
CONFIG_PATH = Path(__file__).parent / "music_tools_config.json"

# .aac included because raw AAC streams often land with this extension
AUDIO_EXTENSIONS = ('.m4a', '.mp3', '.flac', '.ogg', '.opus', '.aac')


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def get_music_root(config):
    root = config.get("music_root")
    if root and Path(root).exists():
        return Path(root)

    # strip quotes because Windows Explorer "copy as path" adds them
    while True:
        raw = input("Music folder path: ").strip().strip('"')
        p = Path(raw)
        if p.is_dir():
            config["music_root"] = str(p)
            save_config(config)
            return p
        print(f"  Not found: {p}")


def fix_containers(root):
    """Wrap raw AAC streams in M4A containers so they can hold metadata."""
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("imageio-ffmpeg not installed. Run: pip install imageio-ffmpeg")
        return

    wrapped, skipped, failed = 0, 0, 0

    for track in root.rglob("*"):
        if not track.is_file() or track.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        try:
            audio = File(track)
            # mutagen.aac.AAC = raw bitstream; anything else already has a container
            if audio is not None and type(audio).__name__ != 'AAC':
                skipped += 1
                continue

            new_path = track.with_suffix('.m4a')
            if new_path.exists():
                new_path = track.with_name(track.stem + '_fixed.m4a')

            # -c copy = remux only, no re-encoding
            result = subprocess.run(
                [ffmpeg_path, '-y', '-i', str(track), '-c', 'copy', str(new_path)],
                capture_output=True
            )

            # don't trust returncode alone — verify output actually exists and has content
            if result.returncode == 0 and new_path.exists() and new_path.stat().st_size > 0:
                track.unlink()
                print(f"  WRAPPED: {track.name} → {new_path.name}")
                wrapped += 1
            else:
                stderr = result.stderr.decode('utf-8', errors='replace')
                print(f"  FAIL:    {track.name} — {stderr[-200:] if result.returncode != 0 else 'output missing or empty'}")
                if new_path.exists() and new_path.stat().st_size == 0:
                    new_path.unlink()  # don't leave empty files behind
                failed += 1
        except Exception as e:
            print(f"  ERROR:   {track.name} — {e}")
            failed += 1

    print(f"\n  Wrapped: {wrapped}, Skipped: {skipped}, Failed: {failed}")


def fix_extensions(root):
    """Rename MP4 files masquerading as .mp3 to .m4a."""
    renamed, skipped, failed = 0, 0, 0

    for track in root.rglob("*.mp3"):
        try:
            audio = File(track)
            # mutagen ignores the extension and reads the actual container format
            if audio and type(audio).__name__ == 'MP4':
                new_path = track.with_suffix('.m4a')
                if new_path.exists():
                    new_path = track.with_name(track.stem + '_renamed.m4a')
                track.rename(new_path)
                print(f"  RENAMED: {track.name} → {new_path.name}")
                renamed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ERROR:   {track.name} — {e}")
            failed += 1

    print(f"\n  Renamed: {renamed}, Skipped: {skipped}, Failed: {failed}")


def tag_genres(root):
    """Write genre tags from parent folder names."""
    tagged, already_ok, failed = 0, 0, 0

    # only iterates top-level dirs — each one becomes the genre name
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        genre = folder.name
        for track in folder.rglob("*"):
            if not track.is_file() or track.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            try:
                # easy=True gives a format-agnostic tag interface (MP3/MP4/FLAC all work the same)
                audio = File(track, easy=True)
                if audio is None:
                    print(f"  FAIL (unreadable): {track.name}")
                    failed += 1
                    continue

                existing = audio.get("genre", [None])[0]
                if existing == genre:
                    print(f"  OK:      {track.name} ({genre})")
                    already_ok += 1
                    continue

                # add_tags() creates the tag header if missing (common with YouTube downloads);
                # throws if tags already exist, which is fine
                try:
                    audio.add_tags()
                except Exception:
                    pass
                audio["genre"] = [genre]
                audio.save()
                print(f"  TAGGED:  {track.name} → {genre}")
                tagged += 1
            except Exception as e:
                print(f"  FAIL:    {track.name} — {e}")
                failed += 1

    print(f"\n  Tagged: {tagged}, Already OK: {already_ok}, Failed: {failed}")


def inspect_file():
    """Show the raw type and tags of a single file."""
    raw = input("  File path: ").strip().strip('"')
    p = Path(raw)
    if not p.is_file():
        print(f"  Not found: {p}")
        return
    # don't use easy=True here — we want the raw tag dump for debugging
    audio = File(p)
    if audio is None:
        print("  Mutagen can't identify this file.")
        return
    print(f"  Type: {type(audio).__name__}")
    print(f"  Tags: {audio.tags}")


def run_all(root):
    """Run fix containers → fix extensions → tag genres in sequence."""
    # order matters: containers must exist before extensions can be checked,
    # and extensions must be correct before the tagger picks them up
    print("\n── Step 1/3: Fix containers ──")
    fix_containers(root)
    print("\n── Step 2/3: Fix extensions ──")
    fix_extensions(root)
    print("\n── Step 3/3: Tag genres ──")
    tag_genres(root)


def main():
    print("Music Library Tools")
    print("Fix containers, extensions, and tags for local music files.")
    print("Config is saved between runs.\n")

    config = load_config()
    root = get_music_root(config)
    print(f"Using: {root}\n")

    menu = {
        '1': ('Fix raw AAC containers',     lambda: fix_containers(root)),
        '2': ('Fix mislabeled extensions',   lambda: fix_extensions(root)),
        '3': ('Tag genres from folders',     lambda: tag_genres(root)),
        '4': ('Run all (1 → 2 → 3)',        lambda: run_all(root)),
        '5': ('Inspect a single file',       lambda: inspect_file()),
        '6': ('Change music folder',         None),
        '0': ('Exit',                        None),
    }

    while True:
        print("\nMusic Library Tools")
        for key, (label, _) in menu.items():
            print(f"  {key}. {label}")

        choice = input("\n> ").strip()

        if choice == '0':
            break
        elif choice == '6':
            config.pop("music_root", None)
            root = get_music_root(config)
            print(f"Using: {root}")
        elif choice in menu:
            print()
            menu[choice][1]()
        else:
            print("Invalid option.")


if __name__ == '__main__':
    main()
