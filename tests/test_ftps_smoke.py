"""FTPS 端到端冒烟测试。

服务器 fixture 与客户端工厂位于 conftest.py。
覆盖：登录（验证 vendored ftp_PASS 的 encry2sha256 密码钩子）/ 上传 / 列表 /
下载 / 删除 / 建删目录 / 错误密码拒绝。
"""
import ftplib
import io

import pytest


def test_ftps_login_upload_download_delete(makeFtpsClient):
    client = makeFtpsClient()

    payload = ("hello ftps smoke 中文内容\n" * 100).encode("utf-8")
    client.storbinary("STOR hello.txt", io.BytesIO(payload))

    assert "hello.txt" in client.nlst()

    buf = io.BytesIO()
    client.retrbinary("RETR hello.txt", buf.write)
    assert buf.getvalue() == payload

    client.delete("hello.txt")
    assert "hello.txt" not in client.nlst()

    client.quit()


def test_ftps_mkdir_rmdir(makeFtpsClient):
    client = makeFtpsClient()

    client.mkd("subdir")
    assert "subdir" in client.nlst()
    client.rmd("subdir")
    assert "subdir" not in client.nlst()

    client.quit()


def test_ftps_wrong_password_rejected(ftpsServer):
    import ssl

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    client = ftplib.FTP_TLS(context=ctx)
    client.connect(ftpsServer["host"], ftpsServer["port"], timeout=10)
    with pytest.raises(ftplib.error_perm):
        client.login("tester", "wrong-password")
    client.close()
