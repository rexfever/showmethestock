"""Backend package marker."""

# DB 패치가 필요하면 여기서 로드 (환경에 따라 건너뛸 수 있음)
import os
import importlib

if os.getenv("SKIP_DB_PATCH") == "1":
    print("⚠️  SKIP_DB_PATCH=1 - db_patch 로드를 건너뜁니다 (테스트/로컬용)")
else:
    try:
        importlib.import_module("backend.db_patch")
    except ModuleNotFoundError as exc:
        if "psycopg" in str(exc):
            print("⚠️  psycopg 모듈을 찾지 못해 db_patch를 건너뜁니다. "
                  "PostgreSQL 기능이 필요한 경우 psycopg를 설치하세요.")
        else:
            raise
