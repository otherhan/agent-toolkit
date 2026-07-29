#!/usr/bin/env bash
set -u
set -o pipefail

usage() {
  cat <<'EOF'
Usage: batch_compress_videos.sh [--output-dir DIR] [--force] [--help]

Batch-compress video files in the current directory into DIR.

Options:
  --output-dir DIR  Output directory. Default: compressed
  --force           Re-encode even when a valid output already exists
  --help            Show this help

The encoding profile is:
  scale=1280:720,fps=30
  libx264 main profile level 3.1, preset slow, tune animation
  3000k video bitrate/maxrate, 6000k bufsize, yuv420p
  AAC audio at 128k, movflags +faststart
EOF
}

output_dir="compressed"
force=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-dir)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --output-dir requires a value" >&2
        exit 2
      fi
      output_dir=$2
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ERROR: ffmpeg not found" >&2
  exit 127
fi

if ! command -v ffprobe >/dev/null 2>&1; then
  echo "ERROR: ffprobe not found" >&2
  exit 127
fi

mkdir -p "$output_dir"

tmp_sources=$(mktemp "${TMPDIR:-/tmp}/compress-videos-sources.XXXXXX")
tmp_outputs=$(mktemp "${TMPDIR:-/tmp}/compress-videos-outputs.XXXXXX")
trap 'rm -f "$tmp_sources" "$tmp_outputs"' EXIT

find . -maxdepth 1 -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '*.m4v' \) -print0 > "$tmp_sources"

source_count=$(tr -cd '\0' < "$tmp_sources" | wc -c | tr -d ' ')
if [ "$source_count" -eq 0 ]; then
  echo "No MP4/MOV/M4V files found in $(pwd)"
  exit 0
fi

is_valid_output() {
  file=$1
  [ -s "$file" ] || return 1

  video=$(ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_name,width,height,pix_fmt,avg_frame_rate \
    -of csv=p=0 "$file" 2>/dev/null) || return 1

  audio=$(ffprobe -v error -select_streams a:0 \
    -show_entries stream=codec_name \
    -of csv=p=0 "$file" 2>/dev/null) || return 1

  [ "$video" = "h264,1280,720,yuv420p,30/1" ] || return 1
  [ "$audio" = "aac" ] || return 1
}

compressed=0
skipped=0
failed=0

while IFS= read -r -d '' input; do
  base=${input#./}
  output="$output_dir/$base"

  if [ "$force" -eq 0 ] && is_valid_output "$output"; then
    echo "SKIP $base"
    skipped=$((skipped + 1))
    printf '%s\0' "$output" >> "$tmp_outputs"
    continue
  fi

  echo "START $base"
  ffmpeg -hide_banner -y -i "$input" \
    -vf "scale=1280:720,fps=30" \
    -c:v libx264 -profile:v main -level:v 3.1 \
    -preset slow -tune animation \
    -b:v 3000k -maxrate 3000k -bufsize 6000k \
    -pix_fmt yuv420p \
    -c:a aac -b:a 128k \
    -movflags +faststart \
    "$output"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "FAILED $base" >&2
    failed=$((failed + 1))
    exit "$rc"
  fi

  if ! is_valid_output "$output"; then
    echo "FAILED validation: $base" >&2
    failed=$((failed + 1))
    exit 1
  fi

  printf '%s\0' "$output" >> "$tmp_outputs"
  compressed=$((compressed + 1))
  echo "DONE $base"
done < "$tmp_sources"

output_count=$(tr -cd '\0' < "$tmp_outputs" | wc -c | tr -d ' ')
source_bytes=$(find . -maxdepth 1 -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '*.m4v' \) -exec stat -f %z {} + 2>/dev/null | awk '{s+=$1} END{print s+0}')
output_bytes=$(while IFS= read -r -d '' output; do stat -f %z "$output"; done < "$tmp_outputs" 2>/dev/null | awk '{s+=$1} END{print s+0}')

echo "SUMMARY source_count=$source_count output_count=$output_count compressed=$compressed skipped=$skipped failed=$failed source_bytes=$source_bytes output_bytes=$output_bytes"
