# DoubanTOOLs - 豆瓣观影记录工具集

一套用于同步豆瓣观影记录到 Trakt.tv 的 Python 工具集。

## 项目概述

这个项目包含四个主要模块：
1. **douban_to_csv** - 从豆瓣抓取用户的观影记录并匹配到 Trakt 条目
2. **csv_to_trakt** - 将处理好的 CSV 文件同步到 Trakt 账户
3. **get_pin_trakt** - 获取 Trakt API 访问令牌的工具
4. **douban_to_trakt_unified** - 统一系统，自动完成整个工作流程

## 功能特性

### douban_to_csv 模块
- 🔍 **自动抓取** - 从豆瓣用户主页抓取所有已看过的影视作品
- 🤖 **智能匹配** - 自动匹配豆瓣条目到 Trakt 数据库
- 🕒 **时间补全** - 支持深度时间补全功能，获取精确的观看时间
- 📊 **CSV 导出** - 导出标准化格式的 CSV 文件，便于人工校对

### csv_to_trakt 模块  
- 🔄 **批量同步** - 支持批量将观影记录同步到 Trakt
- 📺 **类型识别** - 自动识别电影和电视剧类型
- 🎬 **季号处理** - 正确处理电视剧季号信息
- 🧪 **干运行模式** - 支持预览模式，避免误操作
- 🔐 **多认证方式** - 支持命令行参数、环境变量、token.json 多种认证方式

### get_pin_trakt 模块
- 🔑 **令牌获取** - 通过 OAuth 2.0 设备流程获取 Trakt 访问令牌
- 📝 **交互式引导** - 逐步指导用户获取 Trakt 应用凭据
- 🖥️ **用户友好** - 清晰的界面和详细的错误提示
- 💾 **令牌保存** - 自动保存令牌到 JSON 文件供其他工具使用

### douban_to_trakt_unified 模块
- 🔄 **全自动流程** - 一键完成从豆瓣到 Trakt 的整个工作流程
- 🤖 **智能协调** - 自动协调所有子系统的执行顺序
- 🧪 **干运行支持** - 完整的干运行模式支持
- 📋 **进度显示** - 实时显示每个步骤的执行状态
- ⚡ **错误处理** - 完善的错误处理和恢复机制

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `requests` - HTTP 请求库
- `beautifulsoup4` - HTML 解析库
- `certifi` - SSL 证书验证

## 使用方法

### 方法一：使用统一系统（推荐）

```bash
# 使用统一系统一键完成所有步骤
python douban_to_trakt_unified/main.py
```

统一系统会引导您完成：
1. 输入 Trakt 应用凭据
2. 输入豆瓣用户ID和日期范围
3. 配置输出文件
4. 选择是否启用干运行模式
5. 自动执行整个工作流程

### 方法二：分步执行

#### 第零步：获取 Trakt 访问令牌（如尚未获取）

```bash
# 使用交互式工具获取令牌
python get_pin_trakt/get_pin.py
```

按照提示操作，获取并保存访问令牌。

### 第一步：抓取豆瓣数据并生成 CSV

```bash
python douban_to_csv/douban_to_csv.py <豆瓣用户ID> <起始日期> \
  --deep-refine \
  --trakt-client-id <你的Trakt客户端ID> \
  --out movie.csv
```

**参数说明：**
- `豆瓣用户ID` - 豆瓣个人主页的用户ID数字
- `起始日期` - 格式 YYYYMMDD，从此日期开始抓取（默认全部）
- `--deep-refine` - 启用深度时间补全
- `--trakt-client-id` - Trakt API 客户端ID
- `--out` - 输出 CSV 文件路径

### 第二步：人工校对 CSV 文件

生成的 CSV 文件包含以下字段：
- `title` - 影片标题
- `date` - 观看日期
- `datetime` - 观看时间（精确到秒）
- `type` - 类型（movie/show）
- `season` - 季号（电视剧专用）
- `slug` - Trakt 标识符
- `matched_title` - 匹配到的 Trakt 标题
- `matched_year` - 匹配到的年份
- `found` - 是否成功匹配（1/0）
- `douban_link` - 豆瓣链接

**请仔细检查匹配结果**，特别是：
- 确认所有 `found=1` 的条目匹配正确
- 检查电视剧的季号是否正确
- 验证观看时间是否准确

### 第三步：同步到 Trakt

```bash
python csv_to_trakt/csv_to_trakt.py --csv movie.csv --type watched \
  --trakt-client-id <客户端ID> \
  --trakt-token <访问令牌>
```

或者使用环境变量：
```bash
export TRAKT_CLIENT_ID="你的客户端ID"
export TRAKT_ACCESS_TOKEN="你的访问令牌"
python csv_to_trakt/csv_to_trakt.py --csv movie.csv --type watched
```

**同步模式：**
- `--type watched` - 同步到已观看记录
- `--type watchlist` - 同步到想看列表
- `--dry-run` - 干运行模式，只预览不实际同步

## Trakt API 配置

### 第一步：获取 Trakt 访问令牌

推荐使用 `get_pin_trakt` 工具自动获取访问令牌：

```bash
# 使用模块化版本
python get_pin_trakt/get_pin.py
```

工具会逐步引导您：
1. 获取 Trakt 应用凭据（Client ID 和 Client Secret）
2. 生成 PIN 码并在浏览器中授权
3. 自动获取并保存访问令牌

### 手动获取凭据

如果您想手动获取：

1. **获取客户端 ID 和 Secret**
   - 访问 [Trakt TV API](https://trakt.tv/oauth/applications)
   - 创建新的应用程序
   - 获取 Client ID 和 Client Secret

2. **获取访问令牌**
   推荐使用 token.json 方式：
   ```json
   {
     "access_token": "你的访问令牌",
     "refresh_token": "你的刷新令牌",
     "expires_in": 7776000
   }
   ```

将 token.json 放在项目根目录或相应工具目录下。

## 项目结构

```
doubanTOOLs/
├── douban_to_csv/          # 豆瓣数据抓取模块
│   ├── douban.py          # 豆瓣相关功能
│   ├── session_utils.py   # 会话管理
│   ├── trakt.py           # Trakt 匹配功能
│   ├── exporter.py        # CSV 导出
│   ├── config.py          # 配置
│   └── douban_to_csv.py   # 主入口
├── csv_to_trakt/          # Trakt 同步模块
│   ├── config.py          # 配置管理
│   ├── io_csv.py          # CSV 读写
│   ├── time_utils.py      # 时间处理
│   ├── trakt.py           # Trakt API 操作
│   ├── importer.py        # 导入逻辑
│   └── csv_to_trakt.py    # 主入口
├── get_pin_trakt/              # Trakt 令牌获取模块
│   ├── config.py               # 配置和用户引导
│   ├── auth.py                 # 认证逻辑
│   ├── get_pin.py              # 主入口
│   └── __init__.py             # 包初始化
├── douban_to_trakt_unified/    # 统一系统模块
│   ├── config.py               # 统一配置管理
│   ├── orchestrator.py         # 工作流程协调器
│   ├── main.py                 # 统一系统主入口
│   └── __init__.py             # 包初始化
├── getpin.py                   # 简化版令牌获取工具
├── requirements.txt            # 依赖列表
└── README.md                   # 说明文档
```

## 注意事项

1. **遵守豆瓣 Robots协议** - 适当设置请求间隔，避免频繁请求
2. **数据准确性** - 自动匹配可能存在误差，务必人工校对
3. **API 限制** - 遵守 Trakt API 的请求频率限制
4. **隐私保护** - 妥善保管 API 密钥和访问令牌

## 许可证

MIT License

## 致谢

部分逻辑代码参考了 [f-is-h/douban-to-imdb](https://github.com/f-is-h/douban-to-imdb) 项目，特此感谢。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。