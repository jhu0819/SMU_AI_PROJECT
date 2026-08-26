from langchain.tools import tool
from typing import Optional
import subprocess
import sys
import os

# ============================================
# 여행지 추천 도메인 도구
# ============================================

@tool(parse_docstring=True)
def search_flights(
    departure: Optional[str] = None,
    destination: Optional[str] = None,
    departure_date: Optional[str] = None,
) -> str:
    """출발지, 도착지, 출발일을 기준으로 항공편을 검색합니다.
    출발지나 도착지가 주어지지 않으면 인기 여행지를 추천합니다.
    과거 월별 가격 데이터를 비교하여 가장 저렴한 시기도 함께 안내합니다.

    Args:
        departure: 출발지 (예: '서울'). 지정하지 않으면 인기 여행지를 추천합니다
        destination: 도착지 (예: '제주'). 지정하지 않으면 인기 여행지를 추천합니다
        departure_date: 출발일 (예: '2026-10-05'). 지정하지 않아도 됩니다

    Returns:
        항공편 목록(또는 인기 여행지 추천)과 월별 가격 비교를 통한 최저가 시기 안내
    """
    try:
        # 예시 월별 평균 항공권 가격 데이터 (실제로는 과거 가격 이력 API/DB 연동)
        monthly_price_history = {
            "1월": 75000, "2월": 82000, "3월": 68000, "4월": 65000,
            "5월": 90000, "6월": 95000, "7월": 120000, "8월": 130000,
            "9월": 70000, "10월": 68000, "11월": 60000, "12월": 88000,
        }
        cheapest_month = min(monthly_price_history, key=monthly_price_history.get)
        cheapest_price = monthly_price_history[cheapest_month]

        price_trend = "[월별 평균 항공권 가격 비교]\n"
        for month, price in monthly_price_history.items():
            marker = " ← 최저가 시기" if month == cheapest_month else ""
            price_trend += f"- {month}: {price:,}원{marker}\n"
        price_trend += f"\n과거 가격을 비교했을 때 {cheapest_month}이 평균 {cheapest_price:,}원으로 가장 저렴합니다.\n"

        # 출발지 또는 도착지가 없으면 인기 여행지 추천으로 대체
        if not departure or not destination:
            popular_destinations = [
                {"destination": "제주", "reason": "국내 최고 인기 여행지, 사계절 다양한 명소", "avg_price": 68000},
                {"destination": "부산", "reason": "해운대, 감천문화마을 등 도심+바다 여행", "avg_price": 55000},
                {"destination": "강릉", "reason": "커피거리, 동해 바다 힐링 여행", "avg_price": 60000},
                {"destination": "여수", "reason": "야경 명소와 해상 케이블카", "avg_price": 58000},
            ]

            result = "[출발지/도착지 미입력] 인기 여행지를 추천해드립니다.\n\n"
            for p in popular_destinations:
                result += f"- {p['destination']} | {p['reason']} | 평균 항공권 가격: {p['avg_price']:,}원\n"
            result += f"\n{price_trend}"
            return result

        # 출발지, 도착지가 모두 있는 경우: 항공편 목록 검색
        flights = [
            {"airline": "대한항공", "price": 89000, "depart_time": "08:00", "arrive_time": "09:10", "duration": "1시간 10분"},
            {"airline": "제주항공", "price": 65000, "depart_time": "11:30", "arrive_time": "12:40", "duration": "1시간 10분"},
            {"airline": "아시아나항공", "price": 95000, "depart_time": "15:20", "arrive_time": "16:30", "duration": "1시간 10분"},
        ]

        date_label = f" ({departure_date})" if departure_date else ""
        result = f"[항공편 검색 결과] {departure} → {destination}{date_label}\n\n"
        for f in flights:
            result += (
                f"- {f['airline']} | {f['price']:,}원 | "
                f"{f['depart_time']} 출발 → {f['arrive_time']} 도착 | 소요시간: {f['duration']}\n"
            )
        result += f"\n{price_trend}"
        return result
    except Exception as e:
        return f"오류: {str(e)}"


@tool(parse_docstring=True)
def search_hotels(city: str, check_in: str, check_out: str, guests: int) -> str:
    """도시와 체크인/체크아웃 날짜, 인원수를 기준으로 호텔을 검색합니다.

    Args:
        city: 숙소를 찾을 도시 (예: '부산')
        check_in: 체크인 날짜 (예: '2026-10-05')
        check_out: 체크아웃 날짜 (예: '2026-10-07')
        guests: 투숙 인원수

    Returns:
        호텔명, 1박 가격, 평점, 위치를 담은 숙소 목록 또는 오류 메시지
    """
    try:
        # 예시 호텔 데이터 (실제로는 숙박 예약 API 연동)
        hotels = [
            {"name": "오션뷰 호텔", "price": 120000, "rating": 4.5, "location": f"{city} 해변가"},
            {"name": "시티 비즈니스 호텔", "price": 78000, "rating": 4.1, "location": f"{city} 시내 중심가"},
            {"name": "게스트하우스 온기", "price": 45000, "rating": 4.3, "location": f"{city} 구시가지"},
        ]

        result = f"[호텔 검색 결과] {city} | {check_in} ~ {check_out} | 인원: {guests}명\n\n"
        for h in hotels:
            result += f"- {h['name']} | 1박 {h['price']:,}원 | 평점 {h['rating']} | 위치: {h['location']}\n"
        return result
    except Exception as e:
        return f"오류: {str(e)}"


@tool(parse_docstring=True)
def get_tourist_attractions(city: str, category: Optional[str] = None) -> str:
    """도시의 관광지 정보를 조회합니다.

    Args:
        city: 관광지를 조회할 도시 (예: '경주')
        category: 관심 카테고리 (예: '맛집', '명소', '액티비티'). 지정하지 않으면 전체 반환

    Returns:
        추천 장소명, 간단 설명, 운영시간을 담은 리스트 또는 오류 메시지
    """
    try:
        # 예시 관광지 데이터 (실제로는 관광 정보 API 연동)
        attractions = {
            "맛집": [
                {"name": f"{city} 향토음식점", "desc": "현지인이 추천하는 전통 맛집", "hours": "10:00 - 21:00"},
            ],
            "명소": [
                {"name": f"{city} 전망대", "desc": "도시 전경을 한눈에 볼 수 있는 명소", "hours": "09:00 - 18:00"},
            ],
            "액티비티": [
                {"name": f"{city} 체험 마을", "desc": "지역 문화를 체험할 수 있는 액티비티", "hours": "10:00 - 17:00"},
            ],
        }

        if category:
            if category not in attractions:
                available = ", ".join(attractions.keys())
                return f"오류: '{category}' 카테고리를 찾을 수 없습니다. 사용 가능한 카테고리: {available}"
            places = attractions[category]
            result = f"[{city} 관광지 정보] 카테고리: {category}\n\n"
        else:
            places = [p for items in attractions.values() for p in items]
            result = f"[{city} 관광지 정보] 전체\n\n"

        for p in places:
            result += f"- {p['name']} | {p['desc']} | 운영시간: {p['hours']}\n"
        return result
    except Exception as e:
        return f"오류: {str(e)}"


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
    get_tourist_attractions,
]

FILE_TOOLS = [
    read_file,
    write_file,
    delete_file,
    create_directory,
    list_directory,
    execute_python_code
]
