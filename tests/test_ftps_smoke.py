"""FTPS 端到端冒烟测试。

在进程内启动 ThreadedFTPServer (TLS_FTPHandler + 临时自签名证书)，
使用 ftplib.FTP_TLS 走完整链路：
登录（验证 vendored ftp_PASS 的 encry2sha256 密码钩子）/ 上传 / 列表 / 下载 / 删除 / 建删目录。
"""
import datetime
import ftplib
import io
import ssl
import threading

import pytest

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

import Settings
from mypyftpdlib.authorizers import DummyAuthorizer
from mypyftpdlib.handlers import TLS_FTPHandler
from mypyftpdlib.servers import ThreadedFTPServer

TEST_PASSWORD = "test123"


def generateTestCert(certPath, keyPath):
    """生成临时自签名证书与私钥 (PEM)，与 ftpServer.generateTlsCert 等价但写入测试目录。"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    certPath.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keyPath.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


@pytest.fixture()
def ftpsServer(tmp_path):
    certPath = tmp_path / "test.crt"
    keyPath = tmp_path / "test.key"
    generateTestCert(certPath, keyPath)

    rootDir = tmp_path / "root"
    rootDir.mkdir()

    authorizer = DummyAuthorizer()
    # vendored ftp_PASS 会对客户端提交的明文密码先做 encry2sha256 再比对，
    # 因此这里存入的必须是哈希后的密码。
    authorizer.add_user(
        "tester",
        Settings.Settings.encry2sha256(TEST_PASSWORD),
        str(rootDir),
        perm="elradfmwMT",
    )

    handler = type(
        "TestTLSHandler",
        (TLS_FTPHandler,),
        {
            "authorizer": authorizer,
            "encoding": "utf8",
            "certfile": str(certPath),
            "keyfile": str(keyPath),
            "tls_control_required": True,
            "tls_data_required": True,
            "ssl_context": None,
        },
    )

    server = ThreadedFTPServer(("127.0.0.1", 0), handler)
    port = server.socket.getsockname()[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield {"host": "127.0.0.1", "port": port}

    server.close_all()
    thread.join(timeout=5)


def makeClient(serverInfo) -> ftplib.FTP_TLS:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    client = ftplib.FTP_TLS(context=ctx)
    client.connect(serverInfo["host"], serverInfo["port"], timeout=10)
    client.login("tester", TEST_PASSWORD)
    client.prot_p()  # 数据通道加密 (PROT P)
    return client


def test_ftps_login_upload_download_delete(ftpsServer):
    client = makeClient(ftpsServer)

    payload = ("hello ftps smoke 中文内容\n" * 100).encode("utf-8")
    client.storbinary("STOR hello.txt", io.BytesIO(payload))

    assert "hello.txt" in client.nlst()

    buf = io.BytesIO()
    client.retrbinary("RETR hello.txt", buf.write)
    assert buf.getvalue() == payload

    client.delete("hello.txt")
    assert "hello.txt" not in client.nlst()

    client.quit()


def test_ftps_mkdir_rmdir(ftpsServer):
    client = makeClient(ftpsServer)

    client.mkd("subdir")
    assert "subdir" in client.nlst()
    client.rmd("subdir")
    assert "subdir" not in client.nlst()

    client.quit()


def test_ftps_wrong_password_rejected(ftpsServer):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    client = ftplib.FTP_TLS(context=ctx)
    client.connect(ftpsServer["host"], ftpsServer["port"], timeout=10)
    with pytest.raises(ftplib.error_perm):
        client.login("tester", "wrong-password")
    client.close()
