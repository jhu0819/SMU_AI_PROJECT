import base64
import os
import sys
from pathlib import Path

# src 디렉토리를 Python 경로에 추가
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessageChunk
from ai import create_graph

# 환경 변수 로드
load_dotenv()

graph = create_graph()

LOGO_PATH = Path(__file__).parent / "assets" / "sangmyung_logo.jpg"


def set_background_logo():
    """대화창 배경에 학교 로고를 워터마크로 표시"""
    if not LOGO_PATH.exists():
        return

    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            position: relative;
        }}
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: url("data:image/jpeg;base64,{encoded}");
            background-repeat: no-repeat;
            background-position: center;
            background-size: 40%;
            opacity: 0.06;
            pointer-events: none;
            z-index: 0;
        }}
        .stApp > * {{
            position: relative;
            z-index: 1;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session_state():
    """세션 상태 초기화"""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def display_message(role: str, content: str, workflow_info: dict = None):
    """메시지 표시"""

    if role == "user":
        avatar = "🌸"
    else:
        avatar = "🐰"

    with st.chat_message(role, avatar=avatar):
        st.markdown(content)

        # 워크플로 정보가 있으면 표시 (assistant 메시지에만)
        if role == "assistant" and workflow_info:
            display_citations(workflow_info)
            display_workflow_info(workflow_info)


def display_citations(result: dict):
    """답변 근거 검증 결과와 출처 인용 표시"""
    if not result:
        return

    if result.get("is_grounded") is False:
        st.warning(
            result.get("grounding_reason")
            or "검색된 자료에서 명확한 근거를 찾지 못했습니다. 참고용으로만 확인해주세요."
        )

    citations = result.get("citations")
    if citations:
        st.caption("**출처**")
        for c in citations:
            page = c.get("page")
            page_str = f" (p.{page})" if page not in (None, "N/A") else ""
            st.caption(f"[{c['index']}] {c.get('source', '알 수 없음')}{page_str}")
    elif result.get("db_results"):
        st.caption("📊 학사 데이터베이스 조회 결과를 참고했습니다.")


def stream_graph_response(prompt: str):
    """그래프를 스트리밍으로 실행하며 답변 텍스트를 실시간으로 출력하고, (답변, 최종 상태)를 반환"""
    final_state = {}

    def token_generator():
        for stream_mode, chunk in graph.stream(
            {"messages": [{"role": "user", "content": prompt}]},
            stream_mode=["messages", "values"],
        ):
            if stream_mode == "messages":
                message_chunk, metadata = chunk
                # 노드가 끝나면 델타(AIMessageChunk)와 별개로 완성된 AIMessage가 한 번
                # 더 전달되므로, 중복 출력을 막기 위해 델타만 사용한다
                if (
                    isinstance(message_chunk, AIMessageChunk)
                    and metadata.get("langgraph_node") in ("generate_answer", "general_answer")
                    and message_chunk.content
                ):
                    yield message_chunk.content
            elif stream_mode == "values":
                final_state.update(chunk)

    answer = st.write_stream(token_generator())
    return answer, final_state


def display_workflow_info(result: dict):
    """워크플로 정보 표시"""
    with st.expander("🔍 워크플로 정보"):
        col1, col2 = st.columns(2)

        with col1:
            st.metric("의도", result.get("intent", "N/A"))

            if result.get("retry_count"):
                st.metric("재시도 횟수", result["retry_count"])

        with col2:
            if result.get("vector_results"):
                st.metric("검색된 문서", len(result["vector_results"]))

            if result.get("db_results"):
                st.info("DB 검색 수행됨")

        # 벡터 검색 결과 상세 표시
        if result.get("vector_results"):
            st.markdown("#### 📄 검색된 문서")
            for i, doc in enumerate(result["vector_results"], 1):
                with st.expander(f"문서 {i}: {doc.metadata.get('source', '알 수 없음')}"):
                    # 메타데이터 표시
                    meta_cols = st.columns(3)
                    with meta_cols[0]:
                        st.caption(f"📖 페이지: {doc.metadata.get('page', 'N/A')}")
                    with meta_cols[1]:
                        if doc.metadata.get('category'):
                            st.caption(f"🏷️ 카테고리: {doc.metadata.get('category')}")
                    with meta_cols[2]:
                        if doc.metadata.get('score'):
                            st.caption(f"⭐ 점수: {doc.metadata.get('score', 0):.3f}")

                    # 문서 내용 표시
                    st.markdown("**내용:**")
                    st.text(doc.page_content[:500] + ("..." if len(doc.page_content) > 500 else ""))

        # SQL 쿼리 표시
        if result.get("sql_query"):
            st.code(result["sql_query"], language="sql")

        # 재작성된 쿼리 표시
        if result.get("rewritten_query"):
            st.info(f"재작성된 쿼리: {result['rewritten_query']}")

        # 오류 표시
        if result.get("error"):
            st.error(f"오류: {result['error']}")


def main():
    """메인 함수"""
    st.set_page_config(
        page_title="상명대 학사 안내 에이전트",
        page_icon="🎓",
        layout="wide"
    )

    set_background_logo()

    st.title("🎓 상명대 학사 안내 에이전트 워크플로")
    st.markdown("---")

    # 사이드바 - 환경 변수 확인
    with st.sidebar:
        st.header("⚙️ 설정 확인")

        required_vars = {
            "OPENAI_API_KEY": "OpenAI API",
            "QDRANT_URL": "Qdrant URL",
            "QDRANT_API_KEY": "Qdrant API Key",
            "SUPABASE_DB_URL": "Supabase DB"
        }

        for var, name in required_vars.items():
            if os.getenv(var):
                st.success(f"✓ {name}")
            else:
                st.error(f"✗ {name}")

        st.markdown("---")
        st.header("📖 사용 방법")
        st.markdown("""
        **일반 질문:**
        - "안녕하세요"
        - "고마워"

        **벡터 검색 (예: 학사제도):**
        - "조기졸업 신청 자격이 어떻게 되나요?"
        - "수강신청 최대 학점은 몇 학점인가요?"
        - "국가장학금 신청 조건이 궁금해요"

        **DB 검색 (예: 문화예술교육사 인정 학과·교과목):**
        - "디자인 분야 문화예술교육사 인정 학과는 어디인가요?"
        - "연극 분야에서 인정되는 교과목은?"
        - "문화예술교육개론은 몇 학점이고 몇 학년 때 들을 수 있나요?"
        """)

        if st.button("대화 초기화", type="secondary"):
            st.session_state.messages = []
            st.rerun()

    # 세션 상태 초기화
    init_session_state()

    # 이전 메시지 표시
    for message in st.session_state.messages:
        display_message(
            message["role"],
            message["content"],
            message.get("workflow_info")  # 워크플로 정보가 있으면 전달
        )

    # 사용자 입력
    if prompt := st.chat_input("질문을 입력하세요..."):
        # 사용자 메시지 표시 및 저장
        display_message("user", prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 워크플로 실행 (스트리밍)
        with st.chat_message("assistant", avatar="🐰"):
            try:
                # 그래프를 스트리밍으로 실행하며 답변을 실시간으로 표시
                answer, result = stream_graph_response(prompt)

                if not answer:
                    # 스트리밍 청크가 없는 경우(예: 검색 결과가 없어 LLM 호출 없이
                    # 고정 답변을 반환한 경우), 최종 상태에 담긴 답변을 그대로 표시
                    final_messages = result.get("messages", [])
                    answer = final_messages[-1].content if final_messages else "죄송합니다. 답변을 생성할 수 없습니다."
                    st.markdown(answer)

                # 근거 검증 결과 및 출처 인용 표시
                display_citations(result)

                # 워크플로 정보 표시
                display_workflow_info(result)

                # 어시스턴트 메시지와 워크플로 정보 함께 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "workflow_info": result  # 워크플로 정보 저장
                })

            except Exception as e:
                error_msg = f"오류가 발생했습니다: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })


if __name__ == "__main__":
    main()
