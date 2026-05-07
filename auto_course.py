import time
from playwright.sync_api import sync_playwright
from config import TARGET_COURSE_URL
from core_auth import login_and_get_page, check_cookie_expired
from core_utils import load_manual_blacklist
from actions import handle_video, handle_ppt


def run_study():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, args=["--mute-audio", "--start-maximized"]
        )
        context, page = login_and_get_page(browser)
        if not page:
            return

        try:
            page.wait_for_selector(".ant-tabs-tab", timeout=15000)
        except Exception:
            if check_cookie_expired(page):
                return
            print("❌ 未加载出顶部标签页，请确认是否处于正确的课程页面。")
            return

        manual_blacklist = load_manual_blacklist()
        if manual_blacklist:
            print(f"🛡️ 已加载本地手动黑名单，共 {len(manual_blacklist)} 项策略。")

        tab_count = page.locator(".ant-tabs-tab").count()
        skip_items = set()

        for t_idx in range(tab_count):
            print(f"\n📂 准备扫描第 {t_idx + 1} 个标签页...")

            while True:
                tabs = page.locator(".ant-tabs-tab")
                if tabs.count() <= t_idx:
                    break

                tab_element = tabs.nth(t_idx)
                tab_title = tab_element.inner_text().strip()

                if tab_title in manual_blacklist:
                    print(f"🛑 整个标签页 【{tab_title}】 命中手动黑名单，整体跳过！")
                    break

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

                    if title in manual_blacklist:
                        print(f"  🛑 知识页 [{title}] 命中手动黑名单，直接无视...")
                        continue

                    if knowledge_id in skip_items:
                        continue

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

                        if old_section.count() > 0:
                            print("  📑 发现老版资源布局，开始精准处理必学区卡片...")
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
                                    print(f"    ⏭️ 资源 [{res_name}] 已完成，跳过...")
                                    continue
                                print(f"    ▶ 点击进入: {res_name}")
                                if res_title_loc.count() > 0:
                                    res_title_loc.click(force=True)
                                else:
                                    card.click(force=True)
                                time.sleep(4)

                                if page.locator("video:visible").count() > 0:
                                    handle_video(page)
                                    time.sleep(3)
                                elif (
                                    page.locator(
                                        ".ppt-preview-container, .pdf-container"
                                    ).count()
                                    > 0
                                ):
                                    handle_ppt(page)
                                else:
                                    print(
                                        f"    ❓ 非标准视听资料 [{res_name}]，按文档类处理..."
                                    )
                                    handle_ppt(page)

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
                                    print(f"    ⏭️ 资源 [{res_name}] 已完成，跳过...")
                                    continue

                                print(f"    ▶ 点击进入: {res_name}")
                                res_title_loc.click(force=True)
                                time.sleep(4)

                                if page.locator("video:visible").count() > 0:
                                    handle_video(page)
                                    time.sleep(3)
                                elif (
                                    page.locator(
                                        ".ppt-preview-container, .pdf-container"
                                    ).count()
                                    > 0
                                ):
                                    handle_ppt(page)
                                else:
                                    print(
                                        f"    ❓ 非标准视听资料 [{res_name}]，按文档类处理..."
                                    )
                                    handle_ppt(page)
                        else:
                            print(
                                f"  ❌ 等待超时，知识页 [{title}] 内部未找到任何资料。可能为建设中。"
                            )

                        print(
                            f"✅ 知识页 [{title}] 探查完毕，加入已处理名单，准备重载页面..."
                        )
                        skip_items.add(knowledge_id)

                        for attempt in range(3):
                            try:
                                page.goto(
                                    TARGET_COURSE_URL,
                                    timeout=20000,
                                    wait_until="domcontentloaded",
                                )
                                time.sleep(4)
                                if check_cookie_expired(page):
                                    return
                                break
                            except Exception:
                                print(
                                    f"  ⚠️ 页面加载超时/中断，正在重试 ({attempt + 1}/3)..."
                                )
                                time.sleep(3)
                        time.sleep(2)
                        clicked_any = True
                        break

                if not clicked_any:
                    print(
                        f"✨ 标签页 【{tab_title}】 的所有知识点均已达成 100% 学习进度！"
                    )
                    break

        print("🎉 恭喜！全书所有必学视频/PPT刷课完毕！")
        time.sleep(3600)


if __name__ == "__main__":
    run_study()
