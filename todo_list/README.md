# 待做事件列表

这是一个独立的待办工具，数据会保存在当前文件夹下的 `todos.json` 中。

## 图形界面

双击运行：

```powershell
todo_list\启动待做事件列表.bat
```

或在项目根目录运行：

```powershell
python .\todo_list\app.py
```

图形界面支持新增、筛选、搜索、编辑、完成/重新打开、删除待办。

## 常用命令

```powershell
python .\todo_list\main.py
python .\todo_list\main.py add "整理 Egan1.0 的想法目录" -p high -d 2026-07-01 -n "先按功能拆文件夹"
python .\todo_list\main.py list
python .\todo_list\main.py list -s active
python .\todo_list\main.py list -d overdue
python .\todo_list\main.py done 1
python .\todo_list\main.py reopen 1
python .\todo_list\main.py edit 1 -t "更新后的标题" -p medium -d 2026-07-03
python .\todo_list\main.py delete 1
```

## 已支持功能

- 新增、查看、完成、重新打开、编辑、删除待办
- 高、中、低优先级
- 截止日期与逾期提醒
- 按状态、优先级、今日到期、逾期筛选
- 按标题或备注搜索
- 自动统计总数、待办数、已完成数、今日到期数、逾期数
