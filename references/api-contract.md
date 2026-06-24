# Image API Contract

The helper script expects an OpenAI-compatible image API.

## Authentication

Requests include:

```http
Authorization: Bearer <apiKey>
```

## Generation

`POST {baseUrl}/v1/images/generations`

JSON body includes:

- `model`
- `prompt`
- `n`
- `size`, when provided
- `quality`, when provided
- `background`, when provided
- fields from `--extra-json`

## Edit

`POST {baseUrl}/v1/images/edits`

Multipart body includes:

- `image`
- `prompt`
- `model`
- `n`
- `mask`, when provided
- `size`, `quality`, and `background`, when provided
- fields from `--extra-json`

## Response

At least one of these response shapes should be returned:

```json
{
  "data": [
    { "b64_json": "..." }
  ]
}
```

```json
{
  "data": [
    { "url": "https://..." }
  ]
}
```
