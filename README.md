# music-tools

Cleans up common problems in local music libraries downloaded from Spotify/YouTube: raw AAC streams with no container, MP4 files mislabeled as `.mp3`, and missing genre tags.

## Install

```bash
git clone <this-repo-url>
cd music-tools
pip install mutagen imageio-ffmpeg
```

`imageio-ffmpeg` is only needed for the container-fixing step (it bundles a portable ffmpeg binary — no separate ffmpeg install required).

## Usage

```bash
python music_tools.py
```

On first run you'll be prompted for your music library's root folder; the path is saved to `music_tools_config.json` (created next to the script) so you won't be asked again.

```
Music Library Tools
Fix containers, extensions, and tags for local music files.
Config is saved between runs.

Using: E:\Music\SpotifyAAC

Music Library Tools
  1. Fix raw AAC containers
  2. Fix mislabeled extensions
  3. Tag genres from folders
  4. Run all (1 → 2 → 3)
  5. Inspect a single file
  6. Change music folder
  0. Exit

>
```

| Option | What it does |
|---|---|
| 1 | Remuxes raw AAC bitstreams (no container) into `.m4a` via ffmpeg (`-c copy`, no re-encoding). Deletes the original once the output is verified to exist and be non-empty. |
| 2 | Detects `.mp3`-named files that are actually MP4 containers (via mutagen, not the extension) and renames them to `.m4a`. |
| 3 | Writes a `genre` tag on every track, taken from its top-level parent folder name. Skips tracks that already have that genre. |
| 4 | Runs 1 → 2 → 3 in order (order matters: containers must be fixed before extensions are checked, and extensions must be correct before tagging picks files up). |
| 5 | Prints the real container type and raw tag dump for one file — useful for debugging why a track wasn't picked up by 1–3. |
| 6 | Re-prompts for the music root and updates the saved config. |

Each operation prints a per-file line (`WRAPPED`, `RENAMED`, `TAGGED`, `OK`, `FAIL`, `ERROR`) and ends with a tally summary.

## Configuration

`music_tools_config.json`, created next to the script on first run:

```json
{
  "music_root": "E:\\Music\\SpotifyAAC"
}
```

Delete the file, or use menu option 6, to point the tool at a different library.

## Limitations

- Only handles files with these extensions: `.m4a`, `.mp3`, `.flac`, `.ogg`, `.opus`, `.aac`.
- Genre tagging assumes a flat `<music_root>/<genre>/**` layout — it only reads top-level folder names, so nested genre subfolders won't produce the tag you'd expect.
- Container remuxing is a straight `-c copy` — if ffmpeg can't remux a given stream without re-encoding, that file fails and is left untouched.

## License

[MIT](LICENSE)
