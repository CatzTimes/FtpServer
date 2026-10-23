# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 提供代码库工作指导。

## 项目概述

jark006/FtpServer 的个人 fork。基于 Tkinter GUI 的 Windows FTP 服务器，强制 FTPS (TLS/SSL) 传输，支持 IPv4/IPv6、CSV 多用户配置及系统托盘集成。运行于 Python 3.15+。

## 命令

### 运行应用
```powershell
py -3.15 .\ftpServer.py
```

### 安装依赖
```powershell
py -3.15 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# pywin32 还需后安装
pywin32_postinstall -install
```

### 运行测试
```powershell
.\venv\Scripts\Activate.ps1
pip install pytest
pytest tests
```

## 架构

```
ftpServer.py          # 主入口：GUI (Tkinter) + FTP 服务器生命周期（强制 FTPS，证书引导）
├── Settings.py       # 持久化配置 (JSON) - 端口、编码、凭据
├── UserList.py       # 多用户 CSV 解析器，用于 FtpServerUserList.csv
├── myUtils.py        # 工具函数（图标、路径校验 validateInsideAppDirectory）
└── mypyftpdlib/      # 本地化 pyftpdlib v2.2.0（中文日志）
    ├── authorizers.py    # DummyAuthorizer 用户认证
    ├── handlers/         # FTPHandler, TLS_FTPHandler
    └── servers.py        # ThreadedFTPServer
```

`mypyftpdlib` 基线为上游 pyftpdlib `2.2.0 (release-2.2.0)`，同步上游时必须保留本地定制：中文日志、`handlers/ftp/control.py` 的 `ftp_PASS` 密码哈希钩子（`Settings.Settings.encry2sha256`）、`filesystems.py` 的 `_isabs` Windows 加固、移除 `__main__.py` 与 `curses` 依赖。

### 关键设计模式

1. **GUI/主线程**：Tkinter 事件循环 (`window.mainloop()`)
2. **FTP 服务器线程**：IPv4/IPv6 服务器的独立线程 (`serverThreadFun`)
3. **日志队列**：`queue.Queue` 将 FTP 服务器日志桥接到 GUI 文本控件
4. **系统托盘**：`pystray.Icon` 在守护线程中运行，关闭窗口时最小化到托盘
5. **强制 FTPS**：`startServer()` 无证书时经 `promptTlsCertSetup()` 引导生成/选择自定义证书，`create_server_handler()` 始终返回 TLS handler
6. **证书生成**：`generateTlsCert()` 使用 cryptography x509 API（pyOpenSSL `crypto.*` 已废弃）

### 配置文件

| 文件 | 用途 |
|------|------|
| `ftpServer.json` | 自动生成的设置（端口、用户、目录历史） |
| `FtpServerUserList.csv` | 可选的多用户配置（启用后禁用 GUI 用户设置） |
| `ftpServer.crt` + `ftpServer.key` | 必需的 TLS/SSL 证书，启用强制 FTPS（缺失时启动引导生成/选择） |

### 权限系统

用户权限为传递给 `DummyAuthorizer.add_user()` 的字符代码：
- 读取：`e` (CWD), `l` (LIST), `r` (RETR)
- 写入：`a` (APPE), `d` (DELETE), `f` (RENAME), `m` (MKD), `w` (STOR), `M` (CHMOD), `T` (MFMT)

预定义：`elr`（只读），`elradfmwMT`（读写）

## 备注

- 密码存储使用 SHA-256，带盐值前缀 `ENCRY`
- 同时支持 UTF-8 和 GBK 编码以处理中文文件名
- DPI 缩放通过 `ctypes.windll.shcore.SetProcessDpiAwareness(2)` 处理
- 依赖固定版本于 requirements.txt，Python 3.15+（PEP 686 默认 UTF-8 编码，文件 IO 均显式指定 encoding）
