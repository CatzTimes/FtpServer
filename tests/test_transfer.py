"""传输性能与边界正确性测试。

护住 mypyftpdlib 本地定制的传输路径改动（缓冲区大小 / 接收批处理）：
1. 吞吐基准：16MiB 随机数据 STOR+RETR，软断言 ≥10 MiB/s 防性能退化；
2. 块边界正确性：缓冲区尺寸 ±1 字节的 sha256 完整性；
3. REST 断点续传：奇数偏移续读内容一致。
"""
import hashlib
import io
import os
import time

import pytest

# 涉及的缓冲区档位（与 vendored 定制联动：65536/262144）
BOUNDARY_SIZES = [
    65535,
    65536,
    65537,
    262143,
    262144,
    262145,
    (1 << 20) - 1,
    1 << 20,
    (1 << 20) + 1,
]


def test_transfer_throughput(makeFtpsClient):
    client = makeFtpsClient()

    payload = os.urandom(16 << 20)  # 16MiB
    t0 = time.perf_counter()
    client.storbinary("STOR bench.bin", io.BytesIO(payload), blocksize=1 << 20)
    t1 = time.perf_counter()
    buf = io.BytesIO()
    client.retrbinary("RETR bench.bin", buf.write, blocksize=1 << 20)
    t2 = time.perf_counter()

    assert hashlib.sha256(buf.getvalue()).digest() == hashlib.sha256(payload).digest()

    uploadMiBps = len(payload) / 1048576 / (t1 - t0)
    downloadMiBps = len(payload) / 1048576 / (t2 - t1)
    print(f"\nSTOR {uploadMiBps:.1f} MiB/s | RETR {downloadMiBps:.1f} MiB/s")

    assert uploadMiBps >= 10, f"上传吞吐退化: {uploadMiBps:.1f} MiB/s"
    assert downloadMiBps >= 10, f"下载吞吐退化: {downloadMiBps:.1f} MiB/s"

    client.quit()


@pytest.mark.parametrize("size", BOUNDARY_SIZES)
def test_chunk_boundary_integrity(makeFtpsClient, size):
    client = makeFtpsClient()

    payload = os.urandom(size)
    client.storbinary("STOR boundary.bin", io.BytesIO(payload))

    buf = io.BytesIO()
    client.retrbinary("RETR boundary.bin", buf.write)

    assert hashlib.sha256(buf.getvalue()).digest() == hashlib.sha256(payload).digest()

    client.quit()


def test_rest_resume(makeFtpsClient):
    client = makeFtpsClient()

    payload = os.urandom(300_001)  # 非对齐大小，覆盖奇数偏移
    client.storbinary("STOR resume.bin", io.BytesIO(payload))

    offset = 123_457  # 奇数偏移
    resp = client.sendcmd(f"REST {offset}")
    assert resp.startswith("350")

    buf = io.BytesIO()
    client.retrbinary("RETR resume.bin", buf.write)
    assert hashlib.sha256(buf.getvalue()).digest() == hashlib.sha256(
        payload[offset:]
    ).digest()

    client.quit()
