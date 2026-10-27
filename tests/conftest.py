import datetime
import ftplib
import ssl
import sys
import threading
from pathlib import Path

import pytest

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

import Settings
from mypyftpdlib.authorizers import DummyAuthorizer
from mypyftpdlib.handlers import TLS_FTPHandler
from mypyftpdlib.servers import ThreadedFTPServer

# 将仓库根目录加入 sys.path，便于测试导入 Settings / mypyftpdlib 等模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_USER = "tester"
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
    """在进程内启动强制 TLS 的 FTPS 服务器，返回连接信息。"""
    certPath = tmp_path / "test.crt"
    keyPath = tmp_path / "test.key"
    generateTestCert(certPath, keyPath)

    rootDir = tmp_path / "root"
    rootDir.mkdir()

    authorizer = DummyAuthorizer()
    # vendored ftp_PASS 会对客户端提交的明文密码先做 encry2sha256 再比对，
    # 因此这里存入的必须是哈希后的密码。
    authorizer.add_user(
        TEST_USER,
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


@pytest.fixture()
def makeFtpsClient(ftpsServer):
    """返回已建立 TLS 控制与数据通道的客户端工厂。"""

    def _make() -> ftplib.FTP_TLS:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        client = ftplib.FTP_TLS(context=ctx)
        client.connect(ftpsServer["host"], ftpsServer["port"], timeout=10)
        client.login(TEST_USER, TEST_PASSWORD)
        client.prot_p()  # 数据通道加密 (PROT P)
        return client

    return _make
