import os
import shutil
import time
from datetime import datetime, timedelta

# 根目录
BASE_DIR = r"C:\Users\chenyi\Desktop\time_folder"


def create_today_folder():
    """创建当天日期文件夹"""

    today = datetime.now().strftime("%Y%m%d")
    folder = os.path.join(BASE_DIR, today)

    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"创建文件夹：{folder}")

    return folder


def is_folder_empty(folder):
    """判断文件夹是否为空"""

    if not os.path.exists(folder):
        return True

    return len(os.listdir(folder)) == 0


def delete_if_empty(folder):
    """如果为空则删除"""

    if is_folder_empty(folder):
        shutil.rmtree(folder)
        print(f"删除空文件夹：{folder}")
    else:
        print(f"文件夹有内容，保留：{folder}")


def delete_old_empty_folders():
    """程序启动时检查并删除历史空文件夹"""

    if not os.path.exists(BASE_DIR):
        return

    today = datetime.now().strftime("%Y%m%d")

    for name in os.listdir(BASE_DIR):

        folder = os.path.join(BASE_DIR, name)

        # 不是文件夹
        if not os.path.isdir(folder):
            continue

        # 跳过今天
        if name == today:
            continue

        # 只处理 yyyyMMdd 格式
        if len(name) != 8 or not name.isdigit():
            continue

        if is_folder_empty(folder):
            shutil.rmtree(folder)
            print(f"启动检查：删除空文件夹：{folder}")


def seconds_until_midnight():
    """计算距离明天0点还有多少秒"""

    now = datetime.now()

    tomorrow = (
        now + timedelta(days=1)
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    return (tomorrow - now).total_seconds()


def main():

    # 创建根目录
    os.makedirs(BASE_DIR, exist_ok=True)

    # 启动时先清理历史空文件夹
    delete_old_empty_folders()

    while True:

        # 创建今天文件夹
        today_folder = create_today_folder()

        # 等待到明天0点
        wait_seconds = seconds_until_midnight()

        print(f"等待 {int(wait_seconds)} 秒后检查...")

        time.sleep(wait_seconds)

        # 检查今天文件夹是否为空
        delete_if_empty(today_folder)


if __name__ == "__main__":
    main()