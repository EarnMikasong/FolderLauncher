# Folder Launcher

一个面向 Windows 的键盘优先文件夹启动器。它替代原来的 PowerShell 编号菜单，用现代图形界面管理常用目录，并能在指定目录中启动 Claude、Agy 或用户自定义命令。

## 主要功能

- 粘贴路径或通过文件夹选择器添加目录
- 按路径前缀自动归类，采用最长前缀匹配
- 根据已登记路径自动建立父子层级
- 使用数字键进入分类或执行文件夹的默认动作
- 列表自动分页显示，分类数量不写死
- 选中目录后，右侧直接显示文件夹、Claude、Claude 继续、Agy、Agy 继续等快捷动作
- 每个文件夹可选择仅打开、运行命令，或同时执行两者
- Claude 和 Agy 支持普通启动与 `--continue`
- 可以新增程序和参数分离的自定义命令
- 配置保存在用户目录，升级 EXE 不会覆盖配置

## 快速开始

从源码运行：

```powershell
cd folder-launcher
python -m pip install -r requirements.txt
pythonw app.py
```

调试时需要查看异常输出，可以使用：

```powershell
python app.py
```

首次启动会自动导入旧工具中的九个目录。

## 操作方式

| 操作 | 键盘或界面 |
| --- | --- |
| 进入分类或子层级 | 对应数字键，或单击“进入” |
| 选择目录 | 单击目录行 |
| 执行目录默认动作 | 对应数字键、双击目录行或单击“运行” |
| 临时选择启动方式 | 在右侧“快捷动作”中点击 |
| 打开选中目录 | `Enter` 或右侧“打开文件夹” |
| 返回上一级 | `Esc`、`Backspace` 或左上角返回按钮 |
| 翻页 | `←` / `→`、`PageUp` / `PageDown` 或翻页按钮 |
| 添加目录 | 粘贴路径后回车，或点击“选择文件夹” |
| 编辑配置 | 点击“管理” |

带有子目录的条目会先进入下一层；进入后右侧仍可对当前条目执行快捷动作。叶子条目按数字键时直接执行默认动作。

右侧的快捷动作只是本次运行，不会修改默认动作。需要让数字键以后默认启动 Claude 或 Agy 时，在“数字键默认动作”中选择并保存。

## 启动方式

每个文件夹可以独立配置：

- 仅打开资源管理器
- 同时打开资源管理器并运行 Claude
- 同时打开资源管理器并运行 `claude --continue`
- 同时打开资源管理器并运行 Agy
- 同时打开资源管理器并运行 `agy --continue`
- 只运行命令，不打开资源管理器

启动器 EXE 本身使用无控制台模式。Claude、Agy 属于交互式命令，因此选择这些启动方式时会单独打开命令终端，并把目标文件夹设为工作目录。

## 配置文件

运行配置位于：

```text
%APPDATA%\FolderLauncher\config.json
```

建议通过“管理”界面修改。程序使用临时文件加原子替换的方式保存配置，避免写入中断产生半份 JSON。

开发和自动化测试可以通过环境变量 `FOLDER_LAUNCHER_CONFIG` 临时指定其他配置位置。

分类中的“路径前缀”每行一个。例如：

```text
D:\实习\京西智谷
D:\其他工作目录
```

新路径会匹配最长的有效前缀。如果没有前缀匹配，则进入“未分类”。

自定义命令由“程序”和“默认参数”组成，参数每行一个。自定义命令会在本机执行，只应配置自己信任的程序。

## 构建 EXE

本机需要 Python 3.10 或更高版本、CustomTkinter 以及 PyInstaller。双击 `build.bat`，或执行：

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --collect-all customtkinter --name FolderLauncher app.py
```

输出文件：

```text
dist\FolderLauncher.exe
```

`--windowed` 保证启动器运行时不显示 Python 控制台窗口。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试覆盖配置读写、路径前缀匹配、父子层级构建，以及 Claude/Agy 命令参数生成。

## 代码结构

```text
folder-launcher/
├─ app.py                         程序入口
├─ folder_launcher/
│  ├─ config.py                  默认数据与配置持久化
│  ├─ hierarchy.py               路径分类和层级算法
│  ├─ launcher.py                Explorer 与终端启动
│  ├─ models.py                  配置数据模型
│  └─ ui.py                      Tkinter 图形界面
├─ tests/                         核心逻辑测试
├─ requirements.txt              界面依赖
├─ build.bat                      Windows 打包脚本
└─ README.md
```

界面层不直接解析路径或拼接命令。路径关系、配置读写和进程启动分别由独立模块负责，便于后续增加搜索、系统托盘或其他终端实现。
