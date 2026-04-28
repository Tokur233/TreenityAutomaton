# Treenity

自动刷智慧树AI课程脚本

## 项目简介

这是一个基于 Playwright 的自动化脚本，用于在智慧树 AI 课程页面上自动完成“必学”资源的学习过程。脚本会尝试自动登录（如果已有登录状态存储），遍历课程目录，自动处理视频播放、弹窗提示和 PPT 阅读，帮助节省重复操作时间。

> 仅供学习与研究使用，请遵守智慧树平台的使用规则和服务条款。

## 目录结构

- `main.py`：脚本主程序
- `requirements.txt`：Python 依赖列表
- `zhihuishu_state.json`：保存登录状态的 Playwright 存储文件（本地生成，已加入 .gitignore）
- `.env.example`：环境变量配置示例文件

## 依赖

- Python 3.8+
- `playwright>=1.40.0`

## 安装步骤

1. 克隆或下载本项目到本地。
2. 进入项目目录：

```bash
cd \Path\To\Treenity
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 安装 Playwright 浏览器引擎，并下载chromium：

```bash
python -m playwright install
playwright install chromium
```

## 使用方法

### 配置目标课程

在项目根目录创建一个 `.env` 文件，内容示例：

```bash
TARGET_COURSE_URL=https://ai-smart-course-student-pro.zhihuishu.com/learnPage/...
```

也可以直接复制 `.env.example` 并填写真实链接。

### 第一次运行

1. 运行脚本：

```bash
python main.py
```

2. 脚本会打开浏览器并跳转到智慧树首页。
3. 在浏览器中完成扫码或密码登录。
4. 登录并进入课程学习页面（左侧目录、右侧内容均可见）后，回到终端并按 `Enter`。
5. 登录状态会保存到 `zhihuishu_state.json`，下次运行即可直接免密启动。

### 后续运行

再次运行脚本后，如果 `zhihuishu_state.json` 存在且有效，脚本会自动加载登录状态并直接进入目标课程页面。

## 脚本行为说明

脚本会：

- 读取并使用本地登录状态文件 `zhihuishu_state.json`
- 自动跳转到由 `.env` 中 `TARGET_COURSE_URL` 指定的课程页面
- 扫描左侧目录中的“知识模块”“知识单元”“章节”
- 对标记为“必学”的章节进行处理
- 自动播放可见视频并监控播放状态
- 处理“长时间未操作”/答题弹窗等常见防挂机提示
- ~~对 PPT 内容模拟翻页或滚动浏览~~ （刷进度不需要翻页）

## 注意事项

- 目标课程 URL 由项目根目录的 `.env` 文件中的 `TARGET_COURSE_URL` 指定，例如：

```bash
TARGET_COURSE_URL=https://ai-smart-course-student-pro.zhihuishu.com/learnPage/...
```

如果未设置 `.env`，脚本仍会回退检查系统环境变量 `TARGET_COURSE_URL`。

如果本地使用登录状态，`zhihuishu_state.json` 会被 `.gitignore` 忽略，不会提交到仓库。

- 若登录状态过期，请删除 `zhihuishu_state.json` 并重新运行脚本完成登录。
- 脚本仅用于自动化辅助测试，实际使用时请谨慎，避免违反平台规则。

## 免责声明

本项目仅供个人学习与自动化实践参考，不建议用于批量刷课或绕过平台业务规则。使用过程中产生的账号风险或其他后果，作者不承担责任。
