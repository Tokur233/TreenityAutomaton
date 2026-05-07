import re
import time
import difflib
from config import EXCEPTIONS_FILE
from core_utils import (
    load_answers,
    save_answers,
    clean_title,
    clean_option,
    add_to_exceptions,
)


def handle_video(page):
    """处理视频播放及弹窗操作"""
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
                print("  ✅ 视频已播放到底！停留 5 秒等待平台记录进度...")
                time.sleep(5)
                break

            inactivity_msg = page.get_by_text("长时间未操作")
            if inactivity_msg.count() > 0 and inactivity_msg.first.is_visible():
                print("  ⚠️ 检测到防挂机弹窗，自动关闭...")
                page.locator('button:has-text("确定")').first.click(force=True)
                time.sleep(1.5)
                video_locator.evaluate("v => v.play()")
                continue

            dialogs = page.locator('.el-dialog:visible, [role="dialog"]:visible')
            if dialogs.count() > 0:
                options = dialogs.first.locator(".el-radio, .option-item, .el-checkbox")
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

            is_paused = video_locator.evaluate("v => v.paused")
            if is_paused and not is_ended:
                video_locator.evaluate("v => v.play()")

            time.sleep(5)


def handle_ppt(page):
    """处理 PPT/PDF 类型资料"""
    print("  📄 发现文档资料(PPT/PDF)，点开即完成，停留 5 秒等待系统记录...")
    time.sleep(5)
    print("  ✅ 资料阅读任务完成！")


def handle_exam_loop(page, knowledge_id):
    """处理：答题 -> 交卷 -> 报告页 -> 抓答案 的核心死循环"""
    attempt_count = 0
    best_score = 0

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

        best_result_loc = page.locator(".best-result")
        if best_result_loc.count() > 0 and best_result_loc.first.is_visible():
            score_text = best_result_loc.first.inner_text()
            match = re.search(r"(\d+)%", score_text)
            if match:
                best_score = int(match.group(1))

        if attempt_count > 7 or (attempt_count > 5 and best_score >= 90):
            print(
                f"🛑 触发强制跳过机制 (当前尝试次数: {attempt_count}, 最好成绩: {best_score}%)，已加入 {EXCEPTIONS_FILE}！"
            )
            add_to_exceptions(knowledge_id)
            return "SKIP"

        if (
            page.locator('text="提交作业"').count() > 0
            or page.locator('text="交卷"').count() > 0
        ):
            print(f"✍️ 发现试卷，开始智能答题 (第 {attempt_count + 1} 次冲锋)...")
            nodes = page.locator(".font-sec-style-node")
            if nodes.count() > 0:
                for i in range(nodes.count()):
                    nodes.nth(i).click(force=True)
                    time.sleep(1.5)

                    title_loc = page.locator(
                        ".centent-pre .preStyle:visible, .option-name:visible"
                    ).first
                    title = (
                        clean_title(title_loc.inner_text())
                        if title_loc.count() > 0
                        else ""
                    )

                    matches = difflib.get_close_matches(
                        title, list(db.keys()), n=1, cutoff=0.92
                    )

                    options = page.locator(
                        ".el-radio:visible, .el-checkbox:visible, ul.radio-view li:visible"
                    )
                    inputs = page.locator(
                        '.questionContent input[type="text"]:visible, .questionContent textarea:visible, .input-ques input:visible'
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
                                    else correct_texts[-1]
                                )
                                target_input = inputs.nth(j)
                                target_input.click()
                                time.sleep(0.1)
                                target_input.press_sequentially(val, delay=100)
                                time.sleep(0.2)
                                target_input.evaluate(
                                    "node => { node.dispatchEvent(new Event('input', { bubbles: true })); node.dispatchEvent(new Event('change', { bubbles: true })); }"
                                )
                                target_input.press("Enter")
                                target_input.blur()
                                time.sleep(0.4)
                            has_answered = True

                        elif options.count() > 0:
                            for j in range(options.count()):
                                opt = options.nth(j)
                                content_locs = opt.locator(
                                    ".preStyle, .inner-box, .stem"
                                )
                                opt_text = (
                                    clean_option(content_locs.first.inner_text())
                                    if content_locs.count() > 0
                                    else clean_option(opt.inner_text())
                                )
                                for ct in correct_texts:
                                    if (
                                        ct == opt_text
                                        or difflib.SequenceMatcher(
                                            None, ct, opt_text
                                        ).ratio()
                                        > 0.95
                                    ):
                                        has_answered = True
                                        if not is_option_selected(opt):
                                            opt.click(force=True)
                                            time.sleep(0.5)
                                        break

                    if not has_answered:
                        print(f"  [盲猜] 第 {i + 1} 题未命中或新题，盲答兜底...")
                        if inputs.count() > 0:
                            for j in range(inputs.count()):
                                target_input = inputs.nth(j)
                                target_input.click()
                                time.sleep(0.1)
                                target_input.press_sequentially("1", delay=100)
                                time.sleep(0.2)
                                target_input.evaluate(
                                    "node => { node.dispatchEvent(new Event('input', { bubbles: true })); node.dispatchEvent(new Event('change', { bubbles: true })); }"
                                )
                                target_input.press("Enter")
                                target_input.blur()
                                time.sleep(0.4)
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
                    ".el-dialog__wrapper:visible span.button, .el-message-box__btns .el-button, .warningInfo .el-button--primary"
                ).filter(has_text=re.compile(r"提交试卷|确定|交卷|提交"))
                if confirm_btn.count() > 0:
                    confirm_btn.first.click(force=True)

                attempt_count += 1
                time.sleep(6)

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

        elif page.locator(".answer-title").count() > 0:
            print("📚 当前为【测试解析页】，开始疯狂提取正确答案...")
            items = page.locator(".exam-item, .question-item")
            added_count = 0
            for i in range(items.count()):
                item = items.nth(i)
                title_loc = item.locator(
                    ".quest-title .option-name, .quest-title .preStyle"
                ).first
                title = clean_title(title_loc.inner_text())
                ans_loc = item.locator(".answer-title")
                if ans_loc.count() == 0:
                    continue
                ans_str = (
                    ans_loc
                    .inner_text()
                    .replace("\n", "")
                    .replace(" ", "")
                    .replace("\xa0", "")
                    .strip()
                )
                ans_str = ans_str.replace("参考答案：", "")

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
                            content_locs = opt.locator(".preStyle, .inner-box, .stem")
                            text_val = (
                                clean_option(content_locs.first.inner_text())
                                if content_locs.count() > 0
                                else clean_option(
                                    re.sub(r"^([A-Z])[\.、\s]+", "", opt_raw)
                                )
                            )
                            if letter in correct_letters:
                                correct_texts.append(text_val)
                    if correct_texts:
                        db[title] = correct_texts
                        added_count += 1
                elif "(1)" in ans_str or "（1）" in ans_str:
                    parts = re.split(r"[\(（]\d+[\)）]", ans_str)
                    correct_texts = [p.strip() for p in parts if p.strip()]
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

    return "SUCCESS"
