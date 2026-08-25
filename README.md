# XPA Game Tracker

一个面向 Xbox 玩家社区的 Xbox Play Anywhere（XPA）游戏目录。网站支持游戏搜索、排序、新游戏标记和响应式浏览，数据来自 Xbox 官方公开接口。

## 本地运行

项目是纯静态网站。请通过 HTTP 服务打开，避免浏览器对本地 `fetch` 的限制：

```bash
python -m http.server 8000
```

然后访问 <http://127.0.0.1:8000/>。

## 更新游戏数据

安装依赖并运行完整更新流程：

```bash
python -m pip install -r requirements.txt
python update_xpa_data.py
```

更新流程会：

1. 将当前数据保存为 `data/games.previous.json`；
2. 从 Xbox API 获取完整目录并更新 `data/games.json`；
3. 对比前后版本并生成 `data/games_with_new_markers.json`；
4. 检查数据结构、重复产品 ID 和必要的发布文件。

GitHub Actions 每天 UTC 03:17 自动执行同一流程，也可以在 Actions 页面手动触发。只有数据发生变化时才会提交。

## 项目检查

```bash
node --check app.js
python -m compileall -q *.py
python validate_project.py
```

## 发布

生产环境使用 Cloudflare Pages：

- 生产分支：`main`
- 构建命令：留空
- 构建输出目录：仓库根目录

每个 PR 会运行项目检查并生成 Pages 预览部署；合并到 `main` 后自动发布生产版本。

## 协作流程

- 开发分支使用 `codex/<feature-name>` 命名；
- 所有基线后的修改通过 Pull Request；
- PR 通过自动检查和 review 后，由仓库所有者确认合并；
- 游戏及 Xbox 商标归其各自权利人所有，本项目与 Microsoft 或 Xbox 没有关联。
