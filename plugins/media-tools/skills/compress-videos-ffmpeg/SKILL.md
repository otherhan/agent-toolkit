---
name: compress-videos-ffmpeg
description: Use when batch-compressing local video files with ffmpeg, especially MP4/MOV/M4V files that need 1280x720, 30fps, H.264 libx264 main profile level 3.1, AAC audio, faststart output, safe filename handling, resumable skips, or ffprobe verification.
---

# Compress Videos with FFmpeg

## Overview

Batch-compress videos into a separate directory using a known-good ffmpeg profile. Prefer the bundled script for reliability because video filenames often contain spaces, punctuation, or non-ASCII characters.

## Quick Start

From the directory containing source videos:

```bash
bash "<skill-dir>/scripts/batch_compress_videos.sh" --output-dir compressed
```

Use the user's requested output directory name when specified, for example:

```bash
bash "<skill-dir>/scripts/batch_compress_videos.sh" --output-dir "压缩后"
```

Resolve `<skill-dir>` to the directory containing this `SKILL.md`.

## Workflow

1. Inspect the current directory and confirm `ffmpeg` and `ffprobe` are available.
2. Run the bundled script from the source-video directory.
3. Let the script skip already valid outputs unless the user asks to re-encode with `--force`.
4. After completion, report source count, output count, and total size reduction from the script summary.

## Encoding Profile

The script applies this profile to every source file:

```bash
ffmpeg -y -i input \
  -vf "scale=1280:720,fps=30" \
  -c:v libx264 -profile:v main -level:v 3.1 \
  -preset slow -tune animation \
  -b:v 3000k -maxrate 3000k -bufsize 6000k \
  -pix_fmt yuv420p \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  output
```

## Guardrails

- Run the script with `bash`, not `zsh`; `status` is read-only in zsh and can break ad hoc loops.
- Do not parse `find` output with whitespace splitting. Use the bundled script's null-delimited handling.
- Keep output outside the source scan root or skip the output directory to avoid recursively compressing compressed files.
- Treat ffmpeg warnings like `Unknown cover type` as non-fatal unless ffmpeg exits non-zero.
- Verify outputs with `ffprobe`; file count alone is not enough.

## Script

Use `scripts/batch_compress_videos.sh`. Run `--help` for flags.
