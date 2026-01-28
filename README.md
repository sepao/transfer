# Notion 飞书 Markdown 三方同步工具

这是一个支持 **Notion**、**飞书（Lark）** 和 **本地 Markdown** 三方双向同步的命令行工具。您可以轻松地在这三个平台之间一键同步文档。

## 功能特性

### 核心同步功能

- ✅ **Notion → 飞书**：将 Notion 页面一键同步到飞书文档
- ✅ **Notion → Markdown**：同步 Notion 页面到本地 Markdown 文件
- ✅ **Markdown → 飞书**：将本地 Markdown 文件导入飞书并转为在线文档
- ✅ **飞书 → Markdown**：将飞书文档导出为本地 Markdown 文件
- ✅ **飞书 → Notion**：将飞书文档内容同步回 Notion 页面
- ✅ **Markdown → Notion**：将本地 Markdown 文件内容同步到 Notion 页面

### 高级功能

- 🔐 **OAuth 用户授权**：支持用户授权，文档归属于您而非应用
- 📊 **映射管理**：自动维护 Notion、飞书和 Markdown 之间的对应关系
- 🔄 **增量更新**：支持更新现有文档而不是每次都创建新文档
- 📝 **格式保留**：尽可能保留原始格式（标题、列表、代码块等）
- 🗂️ **文件夹管理**：支持指定飞书文件夹位置
- 📋 **同步状态查询**：查看每个文档的同步状态和历史

## 安装

### 前置要求

- Python 3.7+
- pip（Python 包管理器）

### 安装步骤

1. **克隆或下载项目**

```bash
cd ~/notion-feishu-sync
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

## 配置

### 1. 获取 Notion API 密钥

1. 访问 [Notion Developers](https://developers.notion.com/)
2. 点击 "New Integration"
3. 填写集成名称和选择工作空间
4. 复制 "Internal Integration Token"
5. **重要**：在要同步的 Notion 页面中，点击 "..." → "Connections" → 添加您的集成

### 2. 获取飞书应用凭证

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 登录您的企业账号
3. 创建一个新的"企业自建应用"
4. 在应用详情中获取 **App ID** 和 **App Secret**
5. 在"权限管理"中为应用添加以下权限：
   - `docx:document` - 查看、编辑和管理文档
   - `drive:drive` - 访问云空间

6. **（可选）配置 OAuth 用户授权**：
   - 在"安全设置" → "重定向 URL" 中添加：`http://localhost:8080/callback`
   - 这样创建的文档将归属于您，而非应用

### 3. 创建配置文件

运行初始化命令：

```bash
python3 main.py init
```

系统会提示您输入：
- Notion API Key
- 飞书 App ID
- 飞书 App Secret
- Markdown 文件目录（默认：`./markdown_files`）

配置文件将保存为 `config.json`。

**⚠️ 重要：请妥善保管 `config.json` 文件，不要将其提交到版本控制系统或公开分享。**

### 4. （推荐）OAuth 用户授权

默认情况下，创建的飞书文档归属于应用。如果您希望文档归属于您自己，请进行 OAuth 授权：

```bash
python3 main.py auth
```

这将：
1. 打开浏览器让您登录飞书
2. 授权应用代表您操作
3. 保存用户令牌到 `config.json`

授权后，所有创建的文档将归属于您的账号。

## 使用方法

### 基本命令结构

```bash
python3 main.py [OPTIONS] COMMAND [ARGS]
```

### 查看帮助

```bash
python3 main.py --help
python3 main.py sync --help
```

### 授权命令

#### OAuth 用户授权（推荐）

```bash
python3 main.py auth
```

授权后创建的飞书文档将归属于您，而非应用。

### 同步命令

#### 1. Notion → 飞书

```bash
python3 main.py sync notion-to-feishu <NOTION_PAGE_ID>
```

**选项：**
- `--folder-token`: 指定飞书文件夹 token（可选）
- `--create-md`: 同时创建本地 Markdown 文件

**示例：**
```bash
# 基础同步
python3 main.py sync notion-to-feishu abc123def456

# 同时创建 Markdown 文件
python3 main.py sync notion-to-feishu abc123def456 --create-md

# 同步到特定飞书文件夹
python3 main.py sync notion-to-feishu abc123def456 --folder-token xyz789
```

#### 2. Markdown → 飞书

```bash
python3 main.py sync markdown-to-feishu <MD_FILE>
```

**选项：**
- `--folder-token`: 指定飞书文件夹 token（可选）
- `--notion-page-id`: 关联的 Notion 页面 ID（可选）

**示例：**
```bash
# 基础同步
python3 main.py sync markdown-to-feishu ./my_document.md

# 同时关联 Notion 页面
python3 main.py sync markdown-to-feishu ./my_document.md --notion-page-id abc123def456
```

#### 3. 飞书 → Markdown

```bash
python3 main.py sync feishu-to-markdown <FEISHU_TOKEN>
```

**选项：**
- `--md-file`: 指定输出的 Markdown 文件路径（可选，默认自动生成）
- `--notion-page-id`: 关联的 Notion 页面 ID（可选）

**示例：**
```bash
# 基础同步
python3 main.py sync feishu-to-markdown docx1234567890

# 指定输出文件
python3 main.py sync feishu-to-markdown docx1234567890 --md-file ./output.md
```

#### 4. 飞书 → Notion

```bash
python3 main.py sync feishu-to-notion <FEISHU_TOKEN> <NOTION_PAGE_ID>
```

**示例：**
```bash
python3 main.py sync feishu-to-notion docx1234567890 abc123def456
```

#### 5. Markdown → Notion

```bash
python3 main.py sync markdown-to-notion <MD_FILE> <NOTION_PAGE_ID>
```

**示例：**
```bash
python3 main.py sync markdown-to-notion ./my_document.md abc123def456
```

### 状态查询命令

#### 查看单个文档的同步状态

```bash
python3 main.py status sync-status <NOTION_PAGE_ID>
```

#### 列出所有同步映射

```bash
python3 main.py status list-mappings
```

## 配置文件示例

```json
{
  "notion_api_key": "ntn_xxxxxxxxxxxxx",
  "feishu_app_id": "cli_xxxxxxxxxxxxx",
  "feishu_app_secret": "xxxxxxxxxxxxx",
  "feishu_folder_token": "xxxxxxxxxxxxx",
  "markdown_dir": "./markdown_files",
  "mapping_file": "sync_mapping.json",
  "feishu_user_access_token": "u-xxxxxxxxxxxxx",
  "feishu_refresh_token": "ur-xxxxxxxxxxxxx"
}
```

**字段说明：**
- `notion_api_key`: Notion API 密钥（必需）
- `feishu_app_id`: 飞书应用 ID（必需）
- `feishu_app_secret`: 飞书应用密钥（必需）
- `feishu_folder_token`: 默认飞书文件夹 token（可选）
- `markdown_dir`: Markdown 文件目录（默认：`./markdown_files`）
- `mapping_file`: 映射文件路径（默认：`sync_mapping.json`）
- `feishu_user_access_token`: 用户访问令牌（OAuth 授权后自动生成）
- `feishu_refresh_token`: 刷新令牌（OAuth 授权后自动生成）

## 工作流示例

### 场景 1：从 Notion 开始

1. 在 Notion 中编写文档
2. 一键同步到飞书与同事共享
3. 同时保存本地 Markdown 备份

```bash
python3 main.py sync notion-to-feishu <PAGE_ID> --create-md
```

### 场景 2：从本地 Markdown 开始

1. 在本地编辑 Markdown 文件
2. 导入飞书并转为在线文档
3. 关联到 Notion 页面

```bash
python3 main.py sync markdown-to-feishu ./my_doc.md --notion-page-id <PAGE_ID>
```

### 场景 3：飞书文档更新后同步回源

1. 在飞书中编辑文档
2. 导出为 Markdown
3. 同步回 Notion

```bash
python3 main.py sync feishu-to-markdown <TOKEN> --md-file ./updated.md
python3 main.py sync markdown-to-notion ./updated.md <PAGE_ID>
```

## 获取 ID 和 Token

### 获取 Notion 页面 ID

1. 在 Notion 中打开您的页面
2. 复制页面链接
3. URL 中最后的 32 位字符串就是页面 ID

**示例：**
- URL: `https://www.notion.so/My-Page-abc123def456abc123def456abc123de`
- 页面 ID: `abc123def456abc123def456abc123de`

### 获取飞书文档 Token

1. 在飞书中打开您的文档
2. 复制文档链接
3. URL 中 `/docx/` 后面的部分就是文档 token

**示例：**
- URL: `https://feishu.cn/docx/ABC123XYZ456`
- Token: `ABC123XYZ456`

### 获取飞书文件夹 Token

1. 在飞书云空间中打开文件夹
2. 复制文件夹链接
3. URL 中 `/folder/` 后面的部分就是文件夹 token

**示例：**
- URL: `https://feishu.cn/drive/folder/ABC123XYZ456`
- Token: `ABC123XYZ456`

## 格式支持

### 支持的 Notion 块类型

- ✅ 段落
- ✅ 标题（H1, H2, H3）
- ✅ 列表（有序、无序）
- ✅ 待办项
- ✅ 代码块（支持语言高亮）
- ✅ 引用
- ✅ 分割线
- ✅ 图片和视频
- ✅ 链接
- ⚠️ 表格（需要手动转换）
- ⚠️ 数据库（部分支持）

### 支持的 Markdown 元素

- ✅ 标题（H1-H6）
- ✅ 列表（有序、无序）
- ✅ 代码块（支持语言标注）
- ✅ 粗体、斜体、删除线
- ✅ 链接
- ✅ 引用
- ✅ 分割线

## 故障排除

### 问题 1：API 认证失败

**症状：** `Error: Failed to get access token`

**解决方案：**
1. 检查 `config.json` 中的 App ID 和 App Secret 是否正确
2. 确保飞书应用已启用
3. 重新生成 App Secret 并更新配置

### 问题 2：权限不足

**症状：** `Error: 403 Forbidden`

**解决方案：**
1. 确保飞书应用有以下权限：
   - `docx:document`
   - `drive:drive`
2. 确保 Notion Integration 已被添加到目标页面
3. 如果使用 OAuth，重新运行 `python3 main.py auth`

### 问题 3：页面未找到

**症状：** `Error: 404 Not Found`

**解决方案：**
1. 检查页面 ID 或 token 是否正确
2. 确保您有访问该页面的权限
3. 对于 Notion，确保 Integration 已被添加到页面（点击 "..." → "Connections"）

### 问题 4：文档归属于应用而非用户

**症状：** 创建的飞书文档显示为应用所有

**解决方案：**
1. 在飞书开放平台配置重定向 URL：`http://localhost:8080/callback`
2. 运行 `python3 main.py auth` 进行 OAuth 授权
3. 授权后创建的文档将归属于您

### 问题 5：OAuth 授权失败

**症状：** 浏览器显示错误或回调失败

**解决方案：**
1. 确保已在飞书开放平台添加重定向 URL：`http://localhost:8080/callback`
2. 确保端口 8080 未被占用
3. 检查飞书应用权限是否包含 `docx:document` 和 `drive:drive`

## 限制和注意事项

1. **API 限流**：飞书 API 每次最多添加 50 个块，大文档会自动分批处理
2. **表格支持**：复杂表格可能无法完美转换
3. **数据库**：Notion 数据库的同步支持有限
4. **实时同步**：当前版本不支持实时同步，需要手动触发
5. **冲突处理**：如果多个地方同时编辑，最后一次同步会覆盖之前的更改
6. **令牌过期**：用户访问令牌有效期约 2 小时，过期后需重新授权

## 常见问题 (FAQ)

**Q: 同步会覆盖现有内容吗？**
A: 对于 Notion，内容会追加到页面。对于飞书，会创建新文档或更新现有文档。

**Q: 支持实时同步吗？**
A: 当前版本不支持实时同步。您需要手动运行命令来同步文档。

**Q: 可以同步私密文档吗？**
A: 可以，只要您有访问权限并且已添加相应的 Integration/授权。

**Q: 支持批量同步吗？**
A: 当前版本需要逐个同步。您可以编写脚本来批量处理。

**Q: OAuth 授权和普通模式有什么区别？**
A: OAuth 授权后，创建的飞书文档归属于您的账号；普通模式下，文档归属于应用。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue。

---

**最后更新：2026 年 1 月**
