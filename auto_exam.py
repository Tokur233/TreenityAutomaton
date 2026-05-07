import time
from playwright.sync_api import sync_playwright
from config import TARGET_COURSE_URL
from core_auth import login_and_get_page, check_cookie_expired
from core_utils import load_manual_blacklist, load_exceptions
from actions import handle_exam_loop
import re


def run_exam():
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
                exceptions_list = load_exceptions()
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
                        title_loc.inner_text() if title_loc.count() > 0 else "未知章节"
                    )
                    knowledge_id = item.get_attribute("knowledgeid") or title

                    if title in manual_blacklist:
                        print(f"  🛑 知识页 [{title}] 命中手动黑名单，直接无视...")
                        continue

                    if knowledge_id in skip_items or knowledge_id in exceptions_list:
                        continue

                    progress_loc = item.locator(".el-progress__text span").first
                    progress_num = (
                        progress_loc.inner_text().strip()
                        if progress_loc.count() > 0
                        else "0"
                    )

                    if progress_num != "100":
                        print(
                            f"🎯 锁定未满分知识页 [{title}] (当前掌握度 {progress_num}%)，进入探索..."
                        )
                        item.scroll_into_view_if_needed()
                        item.click(force=True)
                        time.sleep(5)

                        improve_btn_main = (
                            page
                            .locator("button, div, span")
                            .filter(has_text=re.compile(r"^去提升$"))
                            .first
                        )
                        if (
                            improve_btn_main.count() > 0
                            and improve_btn_main.is_visible()
                        ):
                            improve_btn_main.click(force=True)
                            time.sleep(4)
                            improve_btn_inner = page.locator(
                                '.improve-btn:has-text("去提升")'
                            )
                            if (
                                improve_btn_inner.count() > 0
                                and improve_btn_inner.is_visible()
                            ):
                                print("  👉 点击报告页【去提升 →】，正式进入考场...")
                                improve_btn_inner.click(force=True)
                                time.sleep(4)

                                loop_status = handle_exam_loop(page, knowledge_id)

                                if loop_status == "SKIP":
                                    print(
                                        f"✅ 章节 [{title}] 达到熔断条件已被加入例外名单，准备跳过..."
                                    )
                                else:
                                    print(
                                        f"✅ 章节 [{title}] 攻克完毕，重新加载页面重置状态..."
                                    )
                            else:
                                print("  ❓ 报告页无提升入口，加入黑名单并刷新页面...")
                                skip_items.add(knowledge_id)
                        else:
                            print(
                                f"  ⏭️ 此知识页无提升任务(或建设中)，加入黑名单并刷新页面..."
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
                    print(f"✨ 标签页 【{tab_title}】 的所有可用内容已处理完毕！")
                    break

        print("🎉 全书所有章节的可用提升任务均已完成！")
        time.sleep(3600)


if __name__ == "__main__":
    run_exam()
