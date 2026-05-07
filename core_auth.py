import os
import time
from config import STATE_FILE, TARGET_COURSE_URL


def check_cookie_expired(page):
    """探针：检查页面是否被强制重定向到了登录网关"""
    if (
        "passport.zhihuishu.com" in page.url
        or page.locator(".wall-warp, .login-box, #f_sign_up").count() > 0
    ):
        print("\n⚠️ 警报：登录记忆 (Cookie) 已过期或在异地登录被踢下线！")
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print("🗑️ 已自动为您删除失效的 Cookie 文件。")
        print("💡 请直接重新运行本脚本，根据弹窗重新登录即可恢复进度！")
        return True
    return False


def login_and_get_page(browser):
    """处理自动免密登录或首次手动授权流程"""
    if not TARGET_COURSE_URL:
        print("⚠️ 请先在 .env 文件中设置 TARGET_COURSE_URL")
        return None, None

    if os.path.exists(STATE_FILE):
        print("🍪 发现本地登录记忆！免密空降中...")
        context = browser.new_context(no_viewport=True, storage_state=STATE_FILE)
        page = context.new_page()
        page.goto(TARGET_COURSE_URL)
        print("⏳ 正在等待页面加载...")
        time.sleep(6)

        if check_cookie_expired(page):
            return None, None
        print("🎉 免密登录成功！直接开始干活！")
    else:
        print("⚠️ 未发现登录记忆。")
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        page.goto("https://www.zhihuishu.com/")
        print("-" * 50)
        print(
            "🚨 【首次运行授权】请在弹出的浏览器中手动登录，进入课程学习页面后按【Enter】键！"
        )
        print("-" * 50)
        input()
        context.storage_state(path=STATE_FILE)
        print("💾 登录状态已永久保存！")

        page.goto(TARGET_COURSE_URL)
        print("⏳ 正在前往课程主页...")
        time.sleep(6)

    return context, page
