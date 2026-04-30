import os
import re
import time
import random
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()


def run_study():
    with sync_playwright() as p:
        # 使用最大化窗口启动，防止响应式布局遮挡元素
        browser = p.chromium.launch(
            headless=False, args=["--mute-audio", "--start-maximized"]
        )

        state_file = "zhihuishu_state.json"
        TARGET_COURSE_URL = os.getenv("TARGET_COURSE_URL")

        if not TARGET_COURSE_URL:
            print("⚠️ 请先在 .env 文件中设置 TARGET_COURSE_URL")
            return

        if os.path.exists(state_file):
            print("🍪 发现本地登录记忆！免密空降中...")
            context = browser.new_context(no_viewport=True, storage_state=state_file)
            page = context.new_page()
            page.goto(TARGET_COURSE_URL)
            print("⏳ 正在等待页面加载...")
            time.sleep(6)

            if (
                page.locator('text="登录"').count() > 0
                and page.locator(".login-box").is_visible()
            ):
                print(
                    "⚠️ 登录记忆似乎已过期，请删除 zhihuishu_state.json 后重新运行脚本。"
                )
                return
            print("🎉 免密登录成功！直接开始干活！")
        else:
            print("⚠️ 未发现登录记忆。")
            context = browser.new_context(no_viewport=True)
            page = context.new_page()
            page.goto("https://www.zhihuishu.com/")
            print("--------------------------------------------------")
            print(
                "🚨 【首次运行授权】请在弹出的浏览器中手动登录，进入课程学习页面后按【Enter】键！"
            )
            print("--------------------------------------------------")
            input()
            context.storage_state(path=state_file)
            print("💾 登录状态已保存！")

        def handle_video():
            print("  ▶ 发现视频，开始自动处理...")
            video_locator = page.locator("video:visible").first

            if video_locator.count() > 0:
                try:
                    video_locator.evaluate("v => { v.muted = true; v.play(); }")
                except Exception:
                    pass

                while True:
                    is_ended = video_locator.evaluate(
                        "v => v.ended || (v.duration > 0 && v.currentTime >= v.duration - 1)"
                    )
                    if is_ended:
                        print("  ✅ 视频已播放到底！停留 2 秒等待平台记录进度...")
                        time.sleep(2)
                        break

                    # 处理防挂机弹窗
                    inactivity_msg = page.get_by_text("长时间未操作")
                    if inactivity_msg.count() > 0 and inactivity_msg.first.is_visible():
                        print("  ⚠️ 检测到防挂机弹窗，自动关闭...")
                        page.locator('button:has-text("确定")').first.click(force=True)
                        time.sleep(1.5)
                        video_locator.evaluate("v => v.play()")
                        continue

                    # 处理答题弹窗
                    dialogs = page.locator(
                        '.el-dialog:visible, [role="dialog"]:visible'
                    )
                    if dialogs.count() > 0:
                        options = dialogs.first.locator(
                            ".el-radio, .option-item, .el-checkbox"
                        )
                        submit_btn = dialogs.first.locator(
                            'button:has-text("确定"), button:has-text("提交")'
                        )
                        if options.count() > 0 or submit_btn.count() > 0:
                            print("  ⚠️ 发现视频内弹题，随机盲猜消除...")
                            if options.count() > 0:
                                options.first.click(force=True)
                                time.sleep(1)
                            if submit_btn.count() > 0:
                                submit_btn.first.click(force=True)
                                time.sleep(1)
                            video_locator.evaluate("v => v.play()")

                    # 意外暂停唤醒
                    is_paused = video_locator.evaluate("v => v.paused")
                    if is_paused and not is_ended:
                        video_locator.evaluate("v => v.play()")

                    time.sleep(2)

        def handle_ppt():
            # 【极致精简版】PPT处理逻辑：不再翻页，挂机 2 秒发送确认包后直接退出
            print("  📄 发现文档资料(PPT/PDF)，点开即完成，停留 2 秒等待系统记录...")
            time.sleep(2)
            print("  ✅ 资料阅读任务完成！")

        def traverse_flat_course():
            print("🔍 检测到平铺界面，开始按标签页扫描...")
            try:
                page.wait_for_selector(".ant-tabs-tab", timeout=15000)
            except Exception:
                print("❌ 未加载出顶部标签页，请确认是否处于正确的课程页面。")
                return

            tab_count = page.locator(".ant-tabs-tab").count()
            skip_items = set()  # 记录已经处理过或无任务的知识点ID

            for t_idx in range(tab_count):
                print(f"\n📂 准备扫描第 {t_idx + 1} 个标签页...")

                while True:
                    # 获取最新 DOM 防止失效
                    tabs = page.locator(".ant-tabs-tab")
                    if tabs.count() <= t_idx:
                        break

                    tab_element = tabs.nth(t_idx)
                    tab_title = tab_element.inner_text().strip()

                    # 解析对应的内容容器 ID
                    tab_btn = tab_element.locator(".ant-tabs-tab-btn")
                    tab_id_attr = tab_btn.get_attribute("id") or ""
                    if "tab-" not in tab_id_attr:
                        break
                    content_id = tab_id_attr.split("tab-")[1]

                    tab_element.click(force=True)
                    time.sleep(2)

                    content_container = page.locator(f"#{content_id}")
                    items = content_container.locator(".item-content")
                    item_count = items.count()

                    clicked_any = False

                    for i_idx in range(item_count):
                        item = content_container.locator(".item-content").nth(i_idx)

                        title_loc = item.locator(".item-title")
                        title = (
                            title_loc.inner_text()
                            if title_loc.count() > 0
                            else "未知知识点"
                        )
                        knowledge_id = item.get_attribute("knowledgeid") or title

                        if knowledge_id in skip_items:
                            continue

                        # 检查卡片上的学习进度
                        progress_loc = item.locator(".bottom-text .progress-num")
                        progress_text = (
                            progress_loc.inner_text().strip()
                            if progress_loc.count() > 0
                            else "0"
                        )

                        if "100" not in progress_text:
                            print(
                                f"👉 发现未完成知识页 [{title}] (进度: {progress_text})，进入学习..."
                            )
                            item.scroll_into_view_if_needed()
                            item.click(force=True)

                            # 给出足够的时间让页面或 Vue 渲染内页资源
                            time.sleep(4)

                            old_section = page.locator(
                                '.resources-section:has(div.resources-detail-title:has-text("必学资源"))'
                            )
                            new_items = page.locator(".line2-list-item")

                            wait_loop = 0
                            while (
                                old_section.count() == 0
                                and new_items.count() == 0
                                and wait_loop < 10
                            ):
                                time.sleep(1)
                                wait_loop += 1

                            # 采用老版逻辑处理
                            if old_section.count() > 0:
                                print(
                                    "  📑 发现老版资源布局，开始精准处理必学区卡片..."
                                )
                                cards = old_section.locator(
                                    ".basic-info-video-card-container"
                                )
                                for r_idx in range(cards.count()):
                                    card = old_section.locator(
                                        ".basic-info-video-card-container"
                                    ).nth(r_idx)
                                    res_title_loc = card.locator(".video-title")
                                    res_name = (
                                        res_title_loc.inner_text()
                                        if res_title_loc.count() > 0
                                        else f"资源{r_idx + 1}"
                                    )

                                    finished_icon = card.locator(".finished-icon")
                                    if finished_icon.count() > 0 and (
                                        "已完成" in finished_icon.inner_text()
                                        or "100%" in finished_icon.inner_text()
                                    ):
                                        print(
                                            f"    ⏭️ 资源 [{res_name}] 已完成，跳过..."
                                        )
                                        continue

                                    print(f"    ▶ 点击进入: {res_name}")
                                    if res_title_loc.count() > 0:
                                        res_title_loc.click(force=True)
                                    else:
                                        card.click(force=True)
                                    time.sleep(4)

                                    if page.locator("video:visible").count() > 0:
                                        handle_video()
                                        time.sleep(3)
                                    elif (
                                        page.locator(
                                            ".ppt-preview-container, .pdf-container"
                                        ).count()
                                        > 0
                                    ):
                                        handle_ppt()
                                    else:
                                        print(
                                            f"    ❓ 非标准视听资料 [{res_name}]，按文档类处理..."
                                        )
                                        handle_ppt()

                            # 采用新版逻辑处理
                            elif new_items.count() > 0:
                                print(
                                    f"  📑 发现新版资源布局，共 {new_items.count()} 项，开始甄别必学标签..."
                                )
                                for r_idx in range(new_items.count()):
                                    card = page.locator(".line2-list-item").nth(r_idx)
                                    res_title_loc = card.locator(".item-name")
                                    res_name = (
                                        res_title_loc.inner_text()
                                        if res_title_loc.count() > 0
                                        else f"资源{r_idx + 1}"
                                    )

                                    # 精准判断是否有必学标签
                                    sugges_loc = card.locator(".item-pic-sugges")
                                    is_required = False
                                    for s_idx in range(sugges_loc.count()):
                                        if "必学" in sugges_loc.nth(s_idx).inner_text():
                                            is_required = True
                                            break

                                    if not is_required:
                                        print(
                                            f"    ⏭️ 资源 [{res_name}] 带有选学标签，跳过..."
                                        )
                                        continue

                                    res_text = card.inner_text()
                                    if "已完成" in res_text or "100%" in res_text:
                                        print(
                                            f"    ⏭️ 资源 [{res_name}] 已完成，跳过..."
                                        )
                                        continue

                                    print(f"    ▶ 点击进入: {res_name}")
                                    res_title_loc.click(force=True)
                                    time.sleep(4)

                                    if page.locator("video:visible").count() > 0:
                                        handle_video()
                                        time.sleep(3)
                                    elif (
                                        page.locator(
                                            ".ppt-preview-container, .pdf-container"
                                        ).count()
                                        > 0
                                    ):
                                        handle_ppt()
                                    else:
                                        print(
                                            f"    ❓ 非标准视听资料 [{res_name}]，按文档类处理..."
                                        )
                                        handle_ppt()
                            else:
                                print(
                                    f"  ❌ 等待超时，知识页 [{title}] 内部未找到任何资料。可能为建设中。"
                                )

                            print(
                                f"✅ 知识页 [{title}] 探查完毕，加入已处理名单，准备重载页面..."
                            )
                            skip_items.add(knowledge_id)

                            # ==========================================
                            # 【核心修复】：增加重载兜底机制，化解发包冲突
                            # ==========================================
                            for attempt in range(3):
                                try:
                                    # wait_until="domcontentloaded" 表示只要核心骨架出来了就行，不傻等所有的追踪脚本
                                    page.goto(
                                        TARGET_COURSE_URL,
                                        timeout=20000,
                                        wait_until="domcontentloaded",
                                    )
                                    break  # 成功加载就跳出重试循环
                                except Exception as e:
                                    print(
                                        f"  ⚠️ 页面重载遇到网络中断，正在进行第 {attempt + 1} 次重试..."
                                    )
                                    time.sleep(3)  # 喘口气再刷
                            time.sleep(5)  # 给页面重新渲染留出时间

                            clicked_any = True
                            break  # 中断 for，重走 while 获取最新 DOM

                    if not clicked_any:
                        print(
                            f"✨ 标签页 【{tab_title}】 的所有知识点均已达成 100% 学习进度！"
                        )
                        break

        traverse_flat_course()
        print("🎉 恭喜！全书所有必学视频/PPT刷课完毕！")
        time.sleep(3600)


if __name__ == "__main__":
    run_study()
