# Treenity

智慧树 AI 课程自动化辅助脚本集合。

## 项目简介

本项目包含两个 Python 自动化脚本：

- `auto_course.py`：自动完成智慧树 AI 课程中“必学资源”的刷课流程。
- `auto_exam.py`：自动答题与答案抓取辅助脚本，可在考试页面中尝试智能作答并保存题库。

脚本基于 Playwright 执行浏览器自动化，支持自动加载登录状态、处理视频播放、应对防挂机弹窗、快速跳转课程资源等功能。

> 仅供学习与研究使用，请遵守智慧树平台的使用规则和服务条款。

## 目录结构

- `auto_course.py`：课程自动化主程序。
- `auto_exam.py`：考试答题与答案抓取脚本。
- `requirements.txt`：Python 依赖列表。
- `answers_db.json`：自动答题脚本的本地题库缓存（本地生成）。
- `zhihuishu_state.json`：Playwright 登录状态储存文件（本地生成）。
- `.env`：环境变量配置文件（需要自行配置相应URL）。
- `.gitignore`：忽略本地 JSON 文件与 `.env`。

## 依赖

- Python 3.8+
- `playwright>=1.40.0`
- `python-dotenv`

## 安装步骤

1. 克隆或下载本项目到本地。
2. 进入项目目录：

```bash
cd D:\Files\Projects\Treenity
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 安装 Playwright 浏览器引擎(个人使用Chromium)

```bash
python -m playwright install chromium
```

## 配置环境

在项目根目录创建一个 `.env` 文件，示例内容：

```bash
TARGET_COURSE_URL=https://ai-smart-course-student-pro.zhihuishu.com/knowledgeStudy/...
```

如果未设置 `.env`，脚本会尝试读取系统环境变量 `TARGET_COURSE_URL`。

## 使用方法

### 刷课脚本：`auto_course.py`

1. 运行脚本：

```bash
python auto_course.py
```

2. 如果首次运行，脚本会打开浏览器并跳转至智慧树首页。
3. 在浏览器中完成扫码或密码登录，并手动进入课程学习页面。
4. 返回终端后按 `Enter` 继续。
5. 登录状态将保存到 `zhihuishu_state.json`，日后运行可免密启动。

### 答题脚本：`auto_exam.py`

1. 运行脚本：

```bash
python auto_exam.py
```

2. 脚本会尝试识别考试页面，自动作答并在解析页提取答案保存到 `answers_db.json`。
3. `answers_db.json` 会作为本地题库用于后续自动答题。

## 脚本行为说明

`auto_course.py` 会：

- 自动加载本地登录状态 `zhihuishu_state.json`
- 访问 `.env` 中配置的 `TARGET_COURSE_URL`
- 检测课程资源布局并按“必学”资源逐项处理
- 自动播放视频并监测播放结束状态
- 应对“长时间未操作”防挂机弹窗与视频内弹题
- 对 PPT/PDF 类资料进行简化处理，等待系统记录进度

`auto_exam.py` 会：

- 从 `answers_db.json` 加载本地题库
- 在考试页面中尝试匹配题目并填充答案
- 未命中题库时盲答以继续流程
- 在解析页提取正确答案并更新题库

## 注意事项

- `.gitignore` 已忽略所有 `.json` 文件和 `.env`，本地登录状态与题库不会提交到仓库。
- 如果登录状态过期，请删除 `zhihuishu_state.json` 并重新运行 `auto_course.py` 进行登录。
- 请谨慎使用自动化脚本，避免违反平台规则或服务条款。

## 免责声明

本项目仅供个人学习与自动化实践参考，不建议用于批量刷课或绕过平台业务规则。使用过程中产生的账号风险或其他后果，作者不承担责任。
