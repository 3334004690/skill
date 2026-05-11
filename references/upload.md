# Upload Module

Upload local files to Aimaxhug and return temp URL + metadata for use in image generation.

## When to Use

User provides local file paths and needs them uploaded for image-to-image generation.

## Subcommands

| Subcommand | When to use |
|------------|-------------|
| `run` | **Default.** Upload file(s) and print result |

## Usage

```bash
python {baseDir}/scripts/upload.py run <file_paths...> [options]
```

## Examples

```bash
# Upload single file
python {baseDir}/scripts/upload.py run photo.jpg

# Upload multiple files
python {baseDir}/scripts/upload.py run photo1.jpg photo2.png

# JSON output for scripting
python {baseDir}/scripts/upload.py run photo.jpg --json
```

## Options

| Option | Description |
|--------|-------------|
| `files` | Local file path(s) to upload (required, one or more) |
| `--json` | Output results as JSON |

## Output

The upload returns a data object with 4 fields — all required for `--input-images`:

```json
{
    "tmp_url": "https://static.aimaxhug.com/xxx.jpg",
    "name": "xxx.jpg",
    "type": "image/jpeg",
    "size": 123456
}
```
