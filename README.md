# Image API Tool 使用教程

这个 skill 让 Codex agent 通过你配置的图片 API 调用生图和改图接口。

支持接口：

- `POST /v1/images/generations`
- `POST /v1/images/edits`

## 1. 安装

把整个 `image-api-tool` 文件夹放到 Codex skills 目录。

Windows:

```powershell
Copy-Item -Recurse -Force .\image-api-tool $env:USERPROFILE\.codex\skills\
```

安装后的结构应该类似：

```text
C:\Users\你的用户名\.codex\skills\image-api-tool\SKILL.md
C:\Users\你的用户名\.codex\skills\image-api-tool\scripts\image_api.py
```

然后重启 Codex，或者开一个新的 Codex 对话。

## 2. 配置 API

推荐使用环境变量配置，不要把真实 `apiKey` 写进要分享的文件里。

PowerShell:

```powershell
$env:IMAGE_API_BASE_URL="https://image.qzcy3.top/api/v1"
$env:IMAGE_API_KEY="你的真实 api key"
$env:IMAGE_API_MODEL="gpt-image-2"
$env:IMAGE_API_TIMEOUT="360"
```

`baseUrl` 可以是：

```text
https://api.example.com
```

也可以是已经带 `/v1` 的地址：

```text
https://api.example.com/api/v1
```

脚本会自动拼接成正确的接口路径。

## 3. 使用本地配置文件

如果不想每次设置环境变量，可以复制配置样例：

```powershell
Copy-Item .\references\config.example.json .\.image-api-config.local.json
```

然后编辑 `.image-api-config.local.json`：

```json
{
  "baseUrl": "https://image.qzcy3.top/api/v1",
  "apiKey": "你的真实 api key",
  "model": "gpt-image-2",
  "timeout": 360
}
```

注意：`.image-api-config.local.json` 是私有文件，不要提交，不要分享。

## 4. 在 Codex 里调用

安装并配置后，可以这样对 Codex 说：

```text
使用 $image-api-tool 生成一张图：一个红苹果放在白色桌面上，摄影棚灯光
```

编辑图片：

```text
使用 $image-api-tool 编辑 F:\path\input.png，把背景换成明亮摄影棚
```

## 5. 手动测试生图

进入 skill 目录：

```powershell
cd C:\Users\你的用户名\.codex\skills\image-api-tool
```

使用环境变量测试：

```powershell
python .\scripts\image_api.py generate --prompt "a simple red apple on a clean white table, studio lighting" --size 1024x1024 --output .\test-generation.png
```

使用本地配置文件测试：

```powershell
python .\scripts\image_api.py generate --config .\.image-api-config.local.json --prompt "a simple red apple on a clean white table, studio lighting" --size 1024x1024 --output .\test-generation.png
```

成功后会输出类似：

```json
{
  "operation": "generate",
  "saved": [
    "C:\\Users\\你的用户名\\.codex\\skills\\image-api-tool\\test-generation.png"
  ],
  "created": 1782281095
}
```

## 6. 手动测试改图

```powershell
python .\scripts\image_api.py edit --config .\.image-api-config.local.json --image .\input.png --prompt "replace the background with a bright studio setting" --output .\edited.png
```

如果 API 支持 mask：

```powershell
python .\scripts\image_api.py edit --config .\.image-api-config.local.json --image .\input.png --mask .\mask.png --prompt "change only the masked area" --output .\edited.png
```

## 7. 常见问题

`HTTP 401` 或 `HTTP 403`：
检查 `apiKey` 是否正确，是否有生图权限。

`HTTP 404`：
检查 `baseUrl`。如果你的地址已经包含 `/v1`，可以直接填完整的 `/v1` 地址。

`HTTP 429`：
上游限流或额度不足，稍后重试，或换 key/模型/渠道。

长时间无响应：
调大 `IMAGE_API_TIMEOUT` 或配置文件里的 `timeout`，例如 `360`。

返回成功但没有图片：
检查 API 响应是否包含 `data[].b64_json` 或 `data[].url`。
