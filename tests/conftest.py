import sys
from pathlib import Path

# 将仓库根目录加入 sys.path，便于测试导入 Settings / mypyftpdlib 等模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
