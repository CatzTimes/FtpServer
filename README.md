# 🖥️ FTP文件服务器

[![Version](https://img.shields.io/github/v/release/jark006/ftpServer)](https://github.com/jark006/FtpServer/releases/latest) ![Download](https://img.shields.io/github/downloads/jark006/FtpServer/total) [![Stars](https://img.shields.io/github/stars/jark006/ftpServer)](https://github.com/jark006/FtpServer/stargazers) [![License](https://img.shields.io/github/license/jark006/ftpServer)](https://github.com/jark006/FtpServer/blob/main/LICENSE) ![Platform](https://img.shields.io/badge/OS-Windows%2010/11%2064%20bit-00adef.svg)

一键开启FTP文件服务器，方便其他设备通过网络传输、管理文件，支持IPv4/IPv6、多用户，强制 FTPS [TLS/SSL 显式加密] 传输。

![](preview.png)

## 🔐 FTPS 配置（强制启用）

*本软件强制使用 FTPS [TLS/SSL 显式加密] 传输数据，不支持明文 FTP。启动服务时若未检测到证书文件，会弹出引导对话框要求配置证书。*

证书文件固定为程序所在目录下的 `ftpServer.crt` 与 `ftpServer.key`，以下三种方式均可:

1. 首次开启服务时，在引导对话框中选择 `自动生成证书`（自签名，有效期10年）。

2. 首次开启服务时，在引导对话框中选择 `选择自定义证书`，依次选择已有的证书与私钥文件（PEM 格式），软件会校验两者配对后自动拷贝为上述固定文件名。

3. 在 `托盘图标` 右键菜单中选择 `生成 FTPS TLS/SSL 证书`，或自行使用 `openssl` 命令生成TLS/SSL证书文件，`不要重命名` 文件为其他名称，直接将 `ftpServer.key` 和 `ftpServer.crt` 放到程序所在目录。

    ```sh
    openssl req -x509 -newkey rsa:2048 -keyout ftpServer.key -out ftpServer.crt -nodes -days 3653
    ```

Windows文件管理器对 `显式FTPS` 支持不佳，推荐使用开源客户端软件 [WinSCP](https://winscp.net/eng/index.php)，对 FTPS 支持比较好。FTPS 加密传输会影响传输性能，最大传输速度约 `50MiB/s`。

---

## 👥 多用户配置

*一般单人使用时，只需在软件主页面设置用户名和密码即可。如果需要开放给多人使用，可以按以下步骤建立多个用户，分配不同的读写权限和根目录。*

在主程序所在目录新建文件 `FtpServerUserList.csv` ，使用 `Excel` 或文本编辑器(需熟悉csv文件格式)编辑，一行一个配置：

1. 第一列：用户名，限定英文大小写/数字。
2. 第二列：密码，限定英文大小写/数字/符号。
3. 第三列：权限，详细配置如下。
4. 第四列：根目录路径。

**📇 样例**

|           |        |            |              |
| --------- | ------ | ---------- | ------------ |
| JARK006   | 123456 | readonly   | D:\Downloads |
| JARK007   | 456789 | readwrite  | D:\Data      |
| JARK008   | abc123 | 只读       | D:\FtpRoot   |
| JARK009   | abc456 | elradfmwMT | D:\FtpRoot   |
| anonymous |        | elr        | D:\FtpRoot   |
| ...       |        |            |              |

注： anonymous 是匿名用户，允许不设密码，其他用户必须设置密码。

📜 详细权限配置：

1. 使用 `readonly` 或 `只读` 设置为 `只读权限`。
1. 使用 `readwrite` 或 `读写` 设置为 `读写权限`。
1. 使用 `自定义` 权限设置，从以下权限挑选自行组合(注意大小写)。

参考链接：https://pyftpdlib.readthedocs.io/en/latest/api.html#pyftpdlib.authorizers.DummyAuthorizer.add_user

📄 读取权限：

- `e` : 更改目录 (CWD 命令)
- `l` : 列出文件 (LIST、NLST、STAT、MLSD、MLST、SIZE、MDTM 命令)
- `r` : 从服务器检索文件 (RETR 命令)

📝 写入权限：

- `a` : 将数据附加到现有文件 (APPE 命令)
- `d` : 删除文件或目录 (DELE、RMD 命令)
- `f` : 重命名文件或目录 (RNFR、RNTO 命令)
- `m` : 创建目录 (MKD 命令)
- `w` : 将文件存储到服务器 (STOR、STOU 命令)
- `M` : 更改文件模式 (SITE CHMOD 命令)
- `T` : 更新文件上次修改时间 (MFMT 命令)

**📌 其他**

1. 若读取到有效配置，则自动 `禁用` 主页面的用户/密码设置。
2. 密码不要出现英文逗号 `,` 字符，以免和csv文本格式冲突。
3. 若不需要多用户配置，可将配置文件 `删除` 或 `重命名` 为其他名称。
4. 配置文件可以是UTF-8或GBK编码。

---

## 🧩 使用到的库

1. [pyftpdlib](https://github.com/giampaolo/pyftpdlib) — 本地内嵌为 `mypyftpdlib`，基线为上游 `2.2.0 (release-2.2.0)`，本地定制：中文日志、`ftp_PASS` 密码哈希钩子、Windows `_isabs` 加固、移除 `__main__.py` 与 `curses` 依赖
2. [tkinter](https://docs.python.org/3/library/tkinter.html)
3. [pystray](https://github.com/moses-palmer/pystray)
4. [Pillow](https://github.com/python-pillow/Pillow)
5. [cryptography](https://github.com/pyca/cryptography) — TLS/SSL 证书生成
6. [pyOpenSSL](https://github.com/pyca/pyopenssl) — FTPS 运行时加密

**📌 运行环境**

1. 要求 Python 3.15+（开发验证于 3.15.1），依赖版本固定见 [requirements.txt](requirements.txt)。
2. Nuitka 打包暂缓：4.3.x 对 Python 3.15 仅为实验性支持，且 Python 3.13+ 不兼容 MinGW64，需 MSVC 2022+ 工具链。
