import re
import os
import time
import random
from playwright.sync_api import sync_playwright


def run_study():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--mute-audio"])

        STATE_FILE = "zhihuishu_state.json"

        TARGET_COURSE_URL = "https://ai-smart-course-student-pro.zhihuishu.com/learnPage/2028067952205553664/1978646709568786432/156520"

        if os.path.exists(STATE_FILE):
            print("🍪 发现本地登录记忆 (Cookie)！尝试自动免密空降...")

            context = browser.new_context(storage_state=STATE_FILE)
            page = context.new_page()

            page.goto(TARGET_COURSE_URL)
            print("⏳ 正在等待页面加载...")
            time.sleep(5)  # 给一点加载时间

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
            print("⚠️ 未发现登录记忆 (首次运行或已清除)。")
            context = browser.new_context()
            page = context.new_page()

            page.goto("https://www.zhihuishu.com/")
            print("--------------------------------------------------")
            print("🚨 【首次运行授权】请在弹出的浏览器中：")
            print("1. 手动完成扫码或密码登录")
            print(
                "2. 一步步点击，直到进入你的【课程学习页面】(能看到左侧目录和右侧内容的地方)"
            )
            print("3. 准备好后，切回这个黑框终端，按下【Enter】键！")
            print("--------------------------------------------------")
            input()

            context.storage_state(path=STATE_FILE)
            print(f"💾 登录状态已永久保存到 {STATE_FILE} ！下次运行将全自动免密！")

        def handle_video():
            print("▶ 发现可见视频，开始处理...")
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
                        print("✅ 视频已到底！停留 5 秒等待平台向服务器发送进度数据...")
                        time.sleep(5)
                        break

                    inactivity_msg = page.get_by_text("长时间未操作")
                    if inactivity_msg.count() > 0 and inactivity_msg.first.is_visible():
                        print("⚠️ 检测到【长时间未操作】防挂机弹窗，正在自动关闭...")

                        btns = page.locator('text="确定"')
                        for i in range(btns.count()):
                            if btns.nth(i).is_visible():
                                btns.nth(i).click()
                                time.sleep(1.5)
                                break

                        video_locator.evaluate("v => v.play()")
                        time.sleep(2)
                        continue

                    dialogs = page.locator('.el-dialog, [role="dialog"]')
                    for i in range(dialogs.count()):
                        d = dialogs.nth(i)
                        if d.is_visible():
                            options = d.locator(".el-radio, .option-item")
                            submit_btn = d.locator(
                                'button:has-text("确定"), button:has-text("提交")'
                            )

                            if options.count() > 0 or submit_btn.count() > 0:
                                print("⚠️ 发现中途答题弹窗，正在随机盲猜...")
                                if options.count() > 0:
                                    options.nth(0).click()
                                    time.sleep(1)
                                if submit_btn.count() > 0:
                                    submit_btn.nth(0).click()
                                    time.sleep(1)

                                video_locator.evaluate("v => v.play()")
                                break

                    is_paused = video_locator.evaluate("v => v.paused")
                    if is_paused and not is_ended:
                        print("⏸️ 发现视频意外暂停，尝试唤醒...")
                        video_locator.evaluate("v => v.play()")

                    time.sleep(5)

        def handle_ppt():
            print("📄 发现 PPT，开始模拟阅读...")

            ppt_catalog = page.locator(
                ".ppt-preview-container .catalogue-container .div-img-container"
            )
            count = ppt_catalog.count()

            if count > 0:
                for i in range(count):
                    ppt_catalog.nth(i).click()

                    time.sleep(random.uniform(2.0, 4.0))
                print("✅ PPT 浏览完毕")
            else:
                for _ in range(6):
                    page.mouse.wheel(0, 800)
                    time.sleep(2)
                print("✅ PPT 滚动完毕")

        def traverse_course():
            print("🔍 开始扫描左侧课程目录...")

            try:
                page.wait_for_selector(".el-collapse-item", timeout=10000)
            except Exception:
                print(
                    "❌ 错误：等待 10 秒后，依然没有在页面上找到课程目录组件。请确认是否真的进入了学习页面！"
                )
                return

            modules = page.locator('.el-collapse-item:has(span:has-text("知识模块"))')
            module_count = modules.count()
            print(f"📦 识别到 {module_count} 个知识模块")

            for m_idx in range(module_count):
                module = modules.nth(m_idx)

                header = module.locator(".el-collapse-item__header").first
                if header.get_attribute("aria-expanded") == "false":
                    header.click()
                    time.sleep(1.5)

                units = module.locator(
                    '.collapse-item-sub:has(span:has-text("知识单元："))'
                )
                unit_count = units.count()

                for u_idx in range(unit_count):
                    unit = units.nth(u_idx)

                    u_header = unit.locator(".el-collapse-item__header").first
                    if u_header.get_attribute("aria-expanded") == "false":
                        u_header.click()
                        time.sleep(1.5)

                    chapters = unit.locator(".section-item-collapse-info")
                    chapter_count = chapters.count()

                    for c_idx in range(chapter_count):
                        chapter = chapters.nth(c_idx)

                        title_loc = chapter.locator(".title-text")
                        title = (
                            title_loc.inner_text()
                            if title_loc.count() > 0
                            else "未知章节名"
                        )

                        full_text = chapter.inner_text().replace("\n", " ")

                        print(f"🔎 扫描到章节: [{title}] | 页面提取文本: {full_text}")

                        if "必学" in full_text:
                            is_finished = False

                            if "100%" in full_text or "已完成" in full_text:
                                is_finished = True

                            nums = re.findall(r"(\d+)\s*/\s*(\d+)", full_text)
                            if nums:
                                current_p, total_p = int(nums[0][0]), int(nums[0][1])
                                if current_p >= total_p:
                                    is_finished = True
                                else:
                                    is_finished = False  # 显式标记未完成

                            if not re.search(r"\d+", full_text):
                                is_finished = False

                            if not is_finished:
                                print(f"👉 准备学习章节: {title}")
                                chapter.click()

                                time.sleep(2)

                                resources_section = page.locator(
                                    '.resources-section:has(div.resources-detail-title:has-text("必学资源"))'
                                )
                                wait_loop = 0
                                while resources_section.count() == 0 and wait_loop < 12:
                                    time.sleep(1)
                                    wait_loop += 1

                                if resources_section.count() > 0:
                                    print(
                                        "📑 发现资源卡片列表，开始逐个处理必学资源..."
                                    )

                                    cards_locator = resources_section.locator(
                                        ".basic-info-video-card-container"
                                    )
                                    card_count = cards_locator.count()

                                    for i in range(card_count):
                                        current_card = (
                                            page.locator(
                                                '.resources-section:has(div.resources-detail-title:has-text("必学资源"))'
                                            )
                                            .locator(".basic-info-video-card-container")
                                            .nth(i)
                                        )

                                        card_title_loc = current_card.locator(
                                            ".video-title"
                                        )
                                        card_title = (
                                            card_title_loc.inner_text()
                                            if card_title_loc.count() > 0
                                            else f"资源{i + 1}"
                                        )

                                        finished_icon = current_card.locator(
                                            ".finished-icon"
                                        )
                                        if finished_icon.count() > 0 and (
                                            "已完成" in finished_icon.inner_text()
                                            or "100%" in finished_icon.inner_text()
                                        ):
                                            print(f"  ⏭️ 卡片已完成，跳过: {card_title}")
                                            continue

                                        print(
                                            f"  👉 正在精准点击卡片标题: {card_title}"
                                        )

                                        if card_title_loc.count() > 0:
                                            card_title_loc.click()
                                        else:
                                            current_card.click()

                                        time.sleep(4)  # 给播放器或右侧组件留出加载时间

                                        if page.locator("video:visible").count() > 0:
                                            handle_video()

                                            time.sleep(3)
                                        else:
                                            print(
                                                f"  📄 非视频资料 [{card_title}]，正在等待平台确认打卡..."
                                            )

                                            wait_success = False
                                            for _ in range(8):
                                                time.sleep(2)

                                                fresh_card = (
                                                    page.locator(
                                                        '.resources-section:has(div.resources-detail-title:has-text("必学资源"))'
                                                    )
                                                    .locator(
                                                        ".basic-info-video-card-container"
                                                    )
                                                    .nth(i)
                                                )
                                                current_status = (
                                                    fresh_card.locator(
                                                        ".finished-icon"
                                                    ).inner_text()
                                                    if fresh_card.locator(
                                                        ".finished-icon"
                                                    ).count()
                                                    > 0
                                                    else ""
                                                )

                                                if (
                                                    "已完成" in current_status
                                                    or "100%" in current_status
                                                ):
                                                    print(
                                                        f"  ✅ 平台已成功记录 [{card_title}]！"
                                                    )
                                                    wait_success = True
                                                    break

                                            if not wait_success:
                                                print(
                                                    f"  ⚠️ 等待打卡超时，平台接口可能响应缓慢，继续往下执行..."
                                                )
                                else:
                                    if page.locator("video:visible").count() > 0:
                                        handle_video()
                                    else:
                                        print(
                                            "❓ 没有资源列表也没有视频，停留 10 秒后跳过..."
                                        )
                                        time.sleep(10)
                            else:
                                print(f"⏭️ 已完成，跳过: {title}")
                        else:
                            print(f"⏭️ 非必学内容(选学)，跳过: {title}")

        traverse_course()
        print("🎉 全部必学内容处理完成！")
        time.sleep(3600)  # 防止浏览器过快关闭


if __name__ == "__main__":
    run_study()
