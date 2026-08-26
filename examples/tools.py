from langchain.tools import tool
import subprocess
import sys
import os

# ============================================
# 여행 도메인 커스텀 도구 (day7 팀 프로젝트)
# ============================================

@tool(parse_docstring=True)
def search_flights(departure: str, destination: str, departure_date: str, max_price: int = 1000000) -> str:
    """출발지, 도착지, 날짜를 기준으로 항공권을 검색합니다.

    Args:
        departure: 출발 도시명 (예: '서울')
        destination: 도착 도시명 (예: '도쿄')
        departure_date: 출발 날짜 (YYYY-MM-DD 형식)
        max_price: 최대 가격(원). 기본값은 1,000,000원

    Returns:
        조건에 맞는 항공편 목록을 담은 JSON 문자열
    """
    import json

    try:
        flight_db = [
            {"airline": "대한항공", "departure": "서울", "destination": "도쿄", "date": "2026-09-01", "price": 320000, "duration": "2시간 30분"},
            {"airline": "아시아나항공", "departure": "서울", "destination": "도쿄", "date": "2026-09-01", "price": 280000, "duration": "2시간 40분"},
            {"airline": "제주항공", "departure": "서울", "destination": "오사카", "date": "2026-09-05", "price": 210000, "duration": "2시간 20분"},
            {"airline": "대한항공", "departure": "서울", "destination": "뉴욕", "date": "2026-10-10", "price": 1450000, "duration": "14시간 30분"},
        ]

        results = [
            f for f in flight_db
            if f["departure"] == departure
            and f["destination"] == destination
            and f["date"] == departure_date
            and f["price"] <= max_price
        ]

        if not results:
            return json.dumps({"message": "조건에 맞는 항공편이 없습니다.", "results": []}, ensure_ascii=False)

        return json.dumps({"message": f"{len(results)}건의 항공편을 찾았습니다.", "results": results}, ensure_ascii=False)
    except Exception as e:
        return f"실패: {str(e)}"


@tool(parse_docstring=True)
def search_hotels(city: str, check_in: str, check_out: str, guests: int = 1) -> str:
    """도시와 체크인/체크아웃 날짜를 기준으로 호텔을 검색합니다.

    Args:
        city: 숙박할 도시명 (예: '도쿄')
        check_in: 체크인 날짜 (YYYY-MM-DD 형식)
        check_out: 체크아웃 날짜 (YYYY-MM-DD 형식)
        guests: 투숙 인원수. 기본값은 1명

    Returns:
        조건에 맞는 호텔 목록을 담은 JSON 문자열
    """
    import json

    try:
        hotel_db = [
            {"name": "도쿄 스테이션 호텔", "city": "도쿄", "price_per_night": 180000, "rating": 4.5, "location": "도쿄역 인근"},
            {"name": "신주쿠 파크 호텔", "city": "도쿄", "price_per_night": 120000, "rating": 4.1, "location": "신주쿠"},
            {"name": "오사카 난바 호텔", "city": "오사카", "price_per_night": 95000, "rating": 4.0, "location": "난바"},
            {"name": "맨해튼 센트럴 호텔", "city": "뉴욕", "price_per_night": 350000, "rating": 4.3, "location": "맨해튼"},
        ]

        if check_in >= check_out:
            return f"실패: 체크아웃 날짜({check_out})는 체크인 날짜({check_in})보다 이후여야 합니다."

        results = [h for h in hotel_db if h["city"] == city]

        if not results:
            return json.dumps({"message": f"'{city}'에 등록된 호텔이 없습니다.", "results": []}, ensure_ascii=False)

        return json.dumps(
            {
                "message": f"{len(results)}건의 호텔을 찾았습니다. (체크인: {check_in}, 체크아웃: {check_out}, 인원: {guests}명)",
                "results": results,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return f"실패: {str(e)}"


@tool(parse_docstring=True)
def get_attractions(city: str, category: str = "") -> str:
    """도시와 관심 카테고리를 기준으로 관광지 정보를 조회합니다.

    Args:
        city: 조회할 도시명 (예: '도쿄')
        category: 관심 카테고리 (예: '맛집', '명소', '액티비티'). 지정하지 않으면 전체 반환

    Returns:
        추천 장소 목록을 담은 JSON 문자열
    """
    import json

    try:
        attraction_db = [
            {"city": "도쿄", "category": "명소", "name": "센소지", "description": "아사쿠사의 대표 사찰", "hours": "06:00-17:00"},
            {"city": "도쿄", "category": "맛집", "name": "츠키지 장외시장", "description": "신선한 해산물 맛집 거리", "hours": "05:00-14:00"},
            {"city": "도쿄", "category": "액티비티", "name": "팀랩 플래닛", "description": "디지털 아트 체험 전시", "hours": "10:00-21:00"},
            {"city": "오사카", "category": "명소", "name": "오사카성", "description": "오사카를 대표하는 성", "hours": "09:00-17:00"},
        ]

        results = [a for a in attraction_db if a["city"] == city and (not category or a["category"] == category)]

        if not results:
            return json.dumps({"message": f"'{city}' ({category or '전체'}) 조건에 맞는 정보가 없습니다.", "results": []}, ensure_ascii=False)

        return json.dumps({"message": f"{len(results)}건의 장소를 찾았습니다.", "results": results}, ensure_ascii=False)
    except Exception as e:
        return f"실패: {str(e)}"


# ============================================
# 파일 시스템 도구 (코딩 에이전트 예시)
# ============================================

@tool(parse_docstring=True)
def read_file(file_path: str) -> str:
    """파일의 내용을 읽어서 반환합니다.

    Args:
        file_path: 읽을 파일의 경로 (상대 경로 또는 절대 경로)

    Returns:
        파일 내용 또는 오류 메시지
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        line_count = len(content.split("\n"))
        return f"파일: {file_path}\n총 {line_count}줄\n\n{content}"
    except FileNotFoundError:
        return f"오류: 파일을 찾을 수 없습니다: {file_path}"
    except PermissionError:
        return f"오류: 파일에 대한 읽기 권한이 없습니다: {file_path}"
    except Exception as e:
        return f"오류: {str(e)}"


@tool(parse_docstring=True)
def write_file(file_path: str, content: str) -> str:
    """파일에 내용을 작성합니다. 파일이 없으면 생성하고, 있으면 덮어씁니다.

    Args:
        file_path: 작성할 파일의 경로
        content: 파일에 쓸 내용

    Returns:
        성공 메시지 또는 오류 메시지
    """
    try:
        # 디렉터리가 없으면 생성
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        line_count = len(content.split("\n"))
        return f"성공: 파일이 작성되었습니다: {file_path} (총 {line_count}줄)"
    except PermissionError:
        return f"오류: 파일에 대한 쓰기 권한이 없습니다: {file_path}"
    except Exception as e:
        return f"오류: {str(e)}"


@tool(parse_docstring=True)
def delete_file(file_path: str) -> str:
    """파일을 삭제합니다.

    Args:
        file_path: 삭제할 파일의 경로

    Returns:
        성공 메시지 또는 오류 메시지
    """
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            return f"성공: 파일이 삭제되었습니다: {file_path}"
        else:
            return f"오류: 파일을 찾을 수 없습니다: {file_path}"
    except PermissionError:
        return f"오류: 파일에 대한 삭제 권한이 없습니다: {file_path}"
    except Exception as e:
        return f"오류: {str(e)}"


@tool(parse_docstring=True)
def create_directory(dir_path: str) -> str:
    """새로운 디렉터리를 생성합니다.

    Args:
        dir_path: 생성할 디렉터리의 경로

    Returns:
        성공 메시지 또는 오류 메시지
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        return f"성공: 디렉터리가 생성되었습니다: {dir_path}"
    except PermissionError:
        return f"오류: 디렉터리 생성 권한이 없습니다: {dir_path}"
    except Exception as e:
        return f"오류: {str(e)}"


@tool(parse_docstring=True)
def list_directory(dir_path: str = ".") -> str:
    """디렉터리의 파일과 폴더 목록을 반환합니다.

    Args:
        dir_path: 조회할 디렉터리 경로 (기본값: 현재 디렉터리)

    Returns:
        파일 및 폴더 목록 또는 오류 메시지
    """
    try:
        if not os.path.exists(dir_path):
            return f"오류: 디렉터리를 찾을 수 없습니다: {dir_path}"

        if not os.path.isdir(dir_path):
            return f"오류: {dir_path}는 디렉터리가 아닙니다"

        items = os.listdir(dir_path)

        if not items:
            return f"디렉터리가 비어있습니다: {dir_path}"

        # 파일과 폴더 분류
        folders = []
        files = []

        for item in sorted(items):
            item_path = os.path.join(dir_path, item)
            if os.path.isdir(item_path):
                folders.append(f"[폴더] {item}/")
            else:
                size = os.path.getsize(item_path)
                files.append(f"[파일] {item} ({size} bytes)")

        result = f"디렉터리: {dir_path}\n\n"

        if folders:
            result += "폴더:\n" + "\n".join(folders) + "\n\n"

        if files:
            result += "파일:\n" + "\n".join(files)

        return result

    except PermissionError:
        return f"오류: 디렉터리에 대한 읽기 권한이 없습니다: {dir_path}"
    except Exception as e:
        return f"오류: {str(e)}"


@tool(parse_docstring=True)
def execute_python_code(code: str) -> str:
    """Python 코드를 실행하고 결과를 반환합니다.

    Args:
        code: 실행할 Python 코드 문자열

    Returns:
        코드 실행 결과 또는 오류 메시지
    """
    try:
        # 보안상의 이유로 제한된 환경에서 실행
        # 실제 프로덕션에서는 샌드박스 환경 사용 권장
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.getcwd()
        )

        output_parts = []

        if result.stdout:
            output_parts.append(f"출력:\n{result.stdout.strip()}")

        if result.stderr:
            output_parts.append(f"오류:\n{result.stderr.strip()}")

        if result.returncode == 0:
            if output_parts:
                return "실행 성공\n\n" + "\n\n".join(output_parts)
            else:
                return "실행 성공 (출력 없음)"
        else:
            return f"실행 실패 (종료 코드: {result.returncode})\n\n" + "\n\n".join(output_parts)

    except subprocess.TimeoutExpired:
        return "오류: 코드 실행 시간이 10초를 초과했습니다."
    except Exception as e:
        return f"오류: {str(e)}"


CUSTOM_TOOLS = [
    search_flights,
    search_hotels,
    get_attractions,
]

FILE_TOOLS = [
    read_file,
    write_file,
    delete_file,
    create_directory,
    list_directory,
    execute_python_code
]
