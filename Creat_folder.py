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

    os.makedirs(BASE_DIR, exist_ok=True)

    while True:

        today_folder = create_today_folder()

        wait_seconds = seconds_until_midnight()

        print(
            f"等待 {int(wait_seconds)} 秒后检查..."
        )

        time.sleep(wait_seconds)

        delete_if_empty(today_folder)


if __name__ == "__main__":
    main()