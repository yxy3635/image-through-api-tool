---
name: image-api-tool
description: Generate or edit raster images through a configurable OpenAI-compatible image API. Use when Codex needs to call a user-provided image generation tool with configurable baseUrl and apiKey values, including POST v1/images/generations for text-to-image and POST v1/images/edits for image editing.
---

# Image API Tool

Use this skill to generate or edit images through a configurable image API. The bundled script supports OpenAI-compatible endpoints:

- `POST /v1/images/generations`
- `POST /v1/images/edits`

## Configuration

Configure credentials with environment variables or a local JSON file.
`baseUrl` may be either the API root, such as `https://api.example.com`, or a versioned root, such as `https://api.example.com/api/v1`.

Preferred environment variables:

```powershell
$env:IMAGE_API_BASE_URL="https://api.example.com"
$env:IMAGE_API_KEY="sk-..."
```

Optional environment variables:

```powershell
$env:IMAGE_API_MODEL="gpt-image-1"
$env:IMAGE_API_TIMEOUT="120"
```

If environment variables are unavailable, copy `references/config.example.json` to a private file such as `.image-api-config.json`, fill in `baseUrl` and `apiKey`, and pass `--config .image-api-config.json`.

Never commit or share a config file containing a real API key.

## Generate Images

Run the helper script from the skill directory or pass its absolute path:

```powershell
python scripts/image_api.py generate --prompt "A clean product render of a white ceramic mug on a desk" --output out\mug.png
```

Useful options:

- `--model`: model name. Defaults to `IMAGE_API_MODEL` or `gpt-image-1`.
- `--size`: image size, for example `1024x1024`.
- `--quality`: provider-specific quality value.
- `--background`: provider-specific background value.
- `--n`: number of images. Defaults to `1`.
- `--extra-json`: additional JSON fields merged into the request body.

## Edit Images

Use `edit` with an input image and prompt:

```powershell
python scripts/image_api.py edit --image input.png --prompt "Replace the background with a bright studio setting" --output out\edited.png
```

Useful options:

- `--mask`: optional mask file for providers that support masks.
- `--model`, `--size`, `--quality`, `--background`: same as generation.
- `--extra-json`: additional form fields. Values are sent as strings for multipart requests unless they are `null`.

## Output Handling

The script saves the first image to `--output`. If the API returns multiple images, the first image uses the requested file name and later images are saved with a numeric suffix, for example `image-2.png`.

The script supports both common response formats:

- Base64 image data in `data[].b64_json`.
- Remote image URLs in `data[].url`, downloaded by the script.

The script prints a JSON summary containing saved file paths and response metadata.

## Troubleshooting

If the API call fails, inspect the printed HTTP status and response body. Common causes are an invalid `baseUrl`, missing `apiKey`, unsupported model, provider-specific request fields, or network restrictions requiring command escalation.

If a provider requires custom fields, pass them through `--extra-json`, for example:

```powershell
python scripts/image_api.py generate --prompt "..." --extra-json '{"style":"natural"}' --output out\image.png
```
