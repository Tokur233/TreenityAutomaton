import os
import re
import json
import time
import difflib
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "answers_db.json"
STATE_FILE = "zhihuishu_state.json"


def load_answers():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_answers(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def clean_text(text):
    """清洗文本，去空格换行，精准去除题号和选项前缀，防止误伤真实文本"""
    if not text:
        return ""
    text = text.replace("\n", "").replace(" ", "").replace("\xa0", "").strip()
    text = re.sub(r"^\d+[\.、](【.*?】)?", "", text)
    text = re.sub(r"^[A-Z][\.、]", "", text)
    return text


def handle_exam_loop(page):
    """处理：答题 -> 交卷 -> 报告页 -> 抓答案 的核心死循环"""

    def is_option_selected(opt_locator):
        try:
            cls = opt_locator.get_attribute("class") or ""
            if "is-checked" in cls or "checked" in cls or "active" in cls:
                return True
            input_loc = opt_locator.locator("input")
            if input_loc.count() > 0 and input_loc.first.is_checked():
                return True
        except Exception:
            pass
        return False

    while True:
        time.sleep(3)
        db = load_answers()

        # =============== 状态 A：待作答页面 (考试中) ===============
        if (
            page.locator('text="提交作业"').count() > 0
            or page.locator('text="交卷"').count() > 0
        ):
            print("✍️ 发现试卷，开始智能答题...")

            nodes = page.locator(".font-sec-style-node")
            if nodes.count() > 0:
                for i in range(nodes.count()):
                    nodes.nth(i).click(force=True)
                    time.sleep(1.5)

                    title_loc = page.locator(
                        ".centent-pre .preStyle, .option-name"
                    ).first
                    title = (
                        clean_text(title_loc.inner_text())
                        if title_loc.count() > 0
                        else ""
                    )

                    matches = difflib.get_close_matches(
                        title, list(db.keys()), n=1, cutoff=0.85
                    )

                    options = page.locator(".el-radio, .el-checkbox, ul.radio-view li")
                    inputs = page.locator(
                        '.questionContent input[type="text"], .questionContent textarea'
                    )

                    has_answered = False

                    if matches:
                        correct_texts = db[matches[0]]
                        print(f"  [命中] 第 {i + 1} 题在题库中找到答案！")

                        if inputs.count() > 0:
                            for j in range(inputs.count()):
                                val = (
                                    correct_texts[j]
                                    if j < len(correct_texts)
                                    else correct_texts[0]
                                )
                                inputs.nth(j).fill(val)
                                has_answered = True
                        elif options.count() > 0:
                            for j in range(options.count()):
                                opt = options.nth(j)
                                
                                content_locs = opt.locator('.preStyle, .inner-box, .stem')
                                if content_locs.count() > 0:
                                    opt_text = clean_text(content_locs.first.inner_text())
                                else:
                                    opt_text = clean_text(opt.inner_text())

                                for ct in correct_texts:
                                    if ct == opt_text or difflib.SequenceMatcher(None, ct, opt_text).ratio() > 0.95:
                                        has_answered = True
                                        if not is_option_selected(opt):
                                            opt.click(force=True)
                                            time.sleep(0.5) 
                                        break

                    if not has_answered:
                        print(f"  [盲猜] 第 {i + 1} 题未命中或新题，盲答第一项...")
                        if inputs.count() > 0:
                            inputs.first.fill("1")
                        elif options.count() > 0:
                            if not is_option_selected(options.first):
                                options.first.click(force=True)

                print("📤 全部作答完毕，准备交卷...")
                submit_btns = page.locator(
                    '.reviewDone, :text("提交作业"), :text("交卷")'
                )
                for k in range(submit_btns.count()):
                    if submit_btns.nth(k).is_visible():
                        submit_btns.nth(k).click(force=True)
                        break
                time.sleep(1.5)

                confirm_btn = page.locator(
                    ".el-dialog__wrapper:visible span.button"
                ).filter(has_text=re.compile(r"提交试卷|确定|交卷|提交"))
                if confirm_btn.count() > 0:
                    confirm_btn.first.click(force=True)
                time.sleep(6)

        # =============== 状态 B：点击查看作答记录 (报告页) ===============
        elif (
            page.locator('text="查看作答记录与解析"').count() > 0
            and page.locator('text="查看作答记录与解析"').first.is_visible()
        ):
            mastery_rate = page.locator(".charts-label-rate")
            if mastery_rate.count() > 0 and "100" in mastery_rate.first.inner_text():
                print("🏆 恭喜！当前掌握度已达 100%！")
                break 
            else:
                print("👀 发现【查看作答记录与解析】按钮，点击进入解析页...")
                page.locator('text="查看作答记录与解析"').first.click(force=True)
                time.sleep(5)

        # =============== 状态 C：测试结果页 (抓取答案) ===============
        elif page.locator(".answer-title").count() > 0:
            print("📚 当前为【测试解析页】，开始疯狂提取正确答案...")
            items = page.locator(".exam-item, .question-item")
            added_count = 0

            for i in range(items.count()):
                item = items.nth(i)
                title = clean_text(
                    item.locator(
                        ".quest-title .option-name, .quest-title .preStyle"
                    ).first.inner_text()
                )
                ans_loc = item.locator(".answer-title")
                if ans_loc.count() == 0:
                    continue

                ans_str = clean_text(ans_loc.inner_text()).replace("参考答案：", "")

                if re.match(r"^[A-Z、,\s]+$", ans_str):
                    correct_letters = re.findall(r"[A-Z]", ans_str)
                    correct_texts = []
                    opts = item.locator(
                        ".el-radio__label, .el-checkbox__label, ul.radio-view li"
                    )
                    for j in range(opts.count()):
                        opt = opts.nth(j)
                        opt_raw = opt.inner_text().strip().replace("\n", " ")
                        
                        match = re.search(r"^([A-Z])", opt_raw)
                        if match:
                            letter = match.group(1)
                            
                            content_locs = opt.locator('.preStyle, .inner-box, .stem')
                            if content_locs.count() > 0:
                                text_val = clean_text(content_locs.first.inner_text())
                            else:
                                text_val = clean_text(re.sub(r"^([A-Z])[\.、\s]+", "", opt_raw))
                                
                            if letter in correct_letters:
                                correct_texts.append(text_val)
                                
                    if correct_texts:
                        db[title] = correct_texts
                        added_count += 1
                else:
                    db[title] = [ans_str]
                    added_count += 1

            save_answers(db)
            print(f"💾 题库已更新！录入 {added_count} 题，总库容: {len(db)} 题。")

            retest_btn = page.locator('text="重新答题"')
            if retest_btn.count() > 0 and retest_btn.first.is_visible():
                print("🔄 点击【重新答题】发起二次冲锋...")
                retest_btn.first.click(force=True)
            else:
                break 
            time.sleep(5)

        # =============== 状态 D：发现二次去提升按钮 (报告页) ===============
        elif page.locator('.improve-btn:has-text("去提升")').count() > 0:
            mastery_rate = page.locator(".charts-label-rate")
            if mastery_rate.count() > 0 and "100" in mastery_rate.first.inner_text():
                print("🏆 恭喜！当前掌握度已达 100%！")
                break 
            else:
                print("👉 点击报告页【去提升 →】，进入考场...")
                page.locator('.improve-btn:has-text("去提升")').first.click(force=True)
                time.sleep(4)

        else:
            print("❓ 页面状态加载中...")
            time.sleep(3)


def run_exam():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, args=["--mute-audio", "--start-maximized"]
        )

        TARGET_COURSE_URL = os.getenv("TARGET_COURSE_URL")
        
        if not TARGET_COURSE_URL:
            print("⚠️ 请先在 .env 文件中设置 TARGET_COURSE_URL")
            return

        def check_cookie_expired(current_page):
            """探针：检查页面是否被强制重定向到了登录网关"""
            if "passport.zhihuishu.com" in current_page.url or current_page.locator('.wall-warp, .login-box, #f_sign_up').count() > 0:
                print("\n⚠️ 警报：登录记忆 (Cookie) 已过期或在异地登录被踢下线！")
                if os.path.exists(STATE_FILE):
                    os.remove(STATE_FILE)
                    print("🗑️ 已自动为您删除失效的 Cookie 文件 (zhihuishu_state.json)。")
                print("💡 请直接重新运行本脚本，根据弹窗重新扫码/密码登录即可恢复进度！")
                return True
            return False

        if os.path.exists(STATE_FILE):
            print("🍪 发现本地登录记忆！免密空降中...")
            context = browser.new_context(no_viewport=True, storage_state=STATE_FILE)
            page = context.new_page()
            page.goto(TARGET_COURSE_URL)
            print("⏳ 正在等待页面加载...")
            time.sleep(6)

            # 首次进入时验证一遍 Cookie 生死
            if check_cookie_expired(page):
                return
            
            print("🎉 免密登录成功！直接开始干活！")
        else:
            print("⚠️ 未发现登录记忆。")
            context = browser.new_context(no_viewport=True)
            page = context.new_page()
            page.goto("https://www.zhihuishu.com/")
            print("--------------------------------------------------")
            print("🚨 【首次运行授权】请在弹出的浏览器中手动登录，进入课程学习页面后按【Enter】键！")
            print("--------------------------------------------------")
            input()
            context.storage_state(path=STATE_FILE)
            print("💾 登录状态已永久保存！")
            
            page.goto(TARGET_COURSE_URL)
            print("⏳ 正在前往课程主页...")
            time.sleep(6)

        try:
            page.wait_for_selector(".ant-tabs-tab", timeout=15000)
        except Exception:
            # 如果没找到顶部标签，再核实一下是不是被弹回登录页了
            if check_cookie_expired(page):
                return
            print("❌ 未加载出顶部标签页，请确认是否处于正确的课程页面。")
            return

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

                    if knowledge_id in skip_items:
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

                                handle_exam_loop(page)
                                print(f"✅ 章节 [{title}] 攻克完毕，重新加载页面重置状态...")
                                
                            else:
                                print("  ❓ 报告页无提升入口，加入黑名单并刷新页面...")
                                skip_items.add(knowledge_id)
                        else:
                            print(
                                f"  ⏭️ 此知识页无提升任务(或建设中)，加入黑名单并刷新页面..."
                            )
                            skip_items.add(knowledge_id)

                        # 执行安全的重载，并夹带断连检查
                        for attempt in range(3):
                            try:
                                page.goto(TARGET_COURSE_URL, timeout=20000, wait_until="domcontentloaded")
                                time.sleep(4)
                                # 如果中途因为 Cookie 失效被弹回主页，立即拦截并清理文件！
                                if check_cookie_expired(page):
                                    return
                                break
                            except Exception:
                                print(f"  ⚠️ 页面加载超时/中断，正在重试 ({attempt + 1}/3)...")
                                time.sleep(3)
                        time.sleep(2)

                        clicked_any = True
                        break  

                if not clicked_any:
                    print(f"✨ 标签页 【{tab_title}】 的所有可用内容已 100% 满分！")
                    break

        print("🎉 全书所有章节的可用提升任务均已完成！")
        time.sleep(3600)


if __name__ == "__main__":
    run_exam()