"""Owner PIN 설정. 실행: webapp/server에서 `.venv/Scripts/python setup_owner.py`

PIN 원문은 저장하지 않는다 — scrypt 해시만 webapp/.data/owner.json(Git 제외)에 쓴다.
환경변수로 두고 싶으면 --print로 해시만 출력해 DOCUMASTER_OWNER_PIN_HASH에 넣는다.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from app.auth import PIN_PATTERN, hash_pin, write_owner_file
from app.config import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="DocuMaster Owner PIN 설정")
    parser.add_argument("--print", action="store_true", help="파일에 쓰지 않고 해시만 출력")
    args = parser.parse_args()

    pin = getpass.getpass("6자리 PIN 입력: ")
    if not PIN_PATTERN.match(pin):
        print("PIN은 숫자 6자리여야 합니다.", file=sys.stderr)
        return 1
    if getpass.getpass("PIN 확인: ") != pin:
        print("두 PIN이 다릅니다.", file=sys.stderr)
        return 1

    pin_hash = hash_pin(pin)
    if args.print:
        print(pin_hash)
        return 0
    settings = load_settings()
    write_owner_file(settings.owner_file, pin_hash)
    # 기존 세션을 끊는다(다른 브라우저에 남은 로그인)
    from app.db import Database
    db = Database(settings.db_path)
    db.execute("DELETE FROM sessions")
    db.close()
    print(f"Owner PIN 설정 완료 ({settings.owner_file})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
