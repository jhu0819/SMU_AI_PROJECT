import re
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from ai.state import AgentState
from ai.retriever import get_retriever
from ai.text2sql import get_text2sql_engine
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, List

load_dotenv()

llm = init_chat_model("gpt-5.4-mini")

_retriever = None
_text2sql_engine = None


class VectorSearchQuery(BaseModel):
    """벡터 검색을 위한 쿼리 분석 결과"""
    optimized_query: str = Field(
        description="검색에 최적화된 쿼리. 핵심 키워드를 포함하고 명확하게 작성."
    )
    categories: Optional[List[str]] = Field(
        default=None,
        description="선택된 카테고리 리스트 (1-2개). 명확하게 관련 있는 카테고리만 선택. 애매하거나 불확실한 경우 null 반환. 가능한 값: 학사일정_휴복학, 다전공_부전공_이수, 졸업_인증, 교육과정_이수기준, 수강신청_계절수업, 성적_학사경고, 원격수업_이러닝, 장학금_학자금대출"
    )


class GroundingCheck(BaseModel):
    """생성된 답변의 근거 충실도 평가 결과"""
    is_grounded: bool = Field(
        description="답변의 핵심 사실이 제공된 근거(문서/DB 결과) 안에 실제로 존재하면 true, 근거 없이 지어내거나 근거와 다르면 false"
    )
    reason: Optional[str] = Field(
        default=None,
        description="근거가 부족하다고 판단한 경우 그 이유를 한 문장으로. 근거가 충분하면 null"
    )


def get_cached_retriever():
    """캐시된 retriever 인스턴스 반환 (lazy initialization)"""
    global _retriever
    if _retriever is None:
        _retriever = get_retriever()
    return _retriever


def get_cached_text2sql_engine():
    """캐시된 text2sql_engine 인스턴스 반환 (lazy initialization)"""
    global _text2sql_engine
    if _text2sql_engine is None:
        _text2sql_engine = get_text2sql_engine()
    return _text2sql_engine


def classify_intent(state: AgentState) -> AgentState:
    """
    사용자 질문의 의도를 분류하는 노드

    분류 결과:
    - 'general': 일반적인 대화나 인사
    - 'database': 데이터베이스 조회가 필요한 질문
    - 'vector': 문서 검색이 필요한 질문

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # messages에서 질문 추출
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("No messages provided")

    # 마지막 사용자 메시지를 질문으로 사용
    question = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

    system_prompt = """
당신은 사용자 질문의 의도를 분류하는 전문가입니다.

이전 대화 맥락을 고려하여 현재 질문을 다음 3가지 중 하나로 분류하세요:

1. 'general' - 일반적인 대화, 인사, 간단한 질문
   예: "안녕하세요", "고마워", "날씨 어때?"

2. 'database' - 문화예술교육사(2급) 인정 학과(전공)나 분야별 인정 교과목(학점, 개설학년, 인정시기 등) 조회가 필요한 질문
   예: "디자인 분야 문화예술교육사 인정 학과는 어디인가요?", "연극 분야에서 인정되는 교과목은?", "문화예술교육개론은 몇 학점이고 몇 학년 때 들을 수 있나요?"

3. 'vector' - 학사제도(휴학·복학, 졸업요건, 전공·교양 이수기준, 수강신청, 성적, 계절수업, 학점교류, 강의평가, 원격수업, 장학금 등) 문서 검색이 필요한 질문
   예: "조기졸업 신청 자격이 어떻게 되나요?", "수강신청 최대 학점은 몇 학점인가요?", "국가장학금 신청 조건이 궁금해요"

반드시 'general', 'database', 'vector' 중 하나만 답변하세요.
다른 설명 없이 분류 결과만 반환하세요.
"""

    # 시스템 메시지 + 전체 대화 히스토리
    conversation = [SystemMessage(content=system_prompt)] + messages

    response = llm.invoke(conversation)
    intent = response.content.strip().lower()

    # 유효한 의도인지 확인
    if intent not in ['general', 'database', 'vector']:
        intent = 'general'

    return {
        "intent": intent,
        "question": question
    }


def general_answer(state: AgentState) -> AgentState:
    """
    일반적인 질문에 직접 답변하는 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # 대화 히스토리 가져오기
    messages = state.get("messages", [])

    system_prompt = """
당신은 친절한 AI 어시스턴트입니다.
사용자의 질문에 자연스럽고 도움이 되는 답변을 제공하세요.
"""

    # 시스템 메시지 + 기존 대화 히스토리
    conversation = [SystemMessage(content=system_prompt)] + messages

    response = llm.invoke(conversation)
    answer = response.content

    return {
        "messages": [AIMessage(content=answer)]
    }


def vector_search(state: AgentState) -> AgentState:
    """
    Qdrant 벡터 검색을 수행하는 노드

    1. LLM으로 질문 분석 (최적화된 쿼리 + 카테고리 추출)
    2. 병렬 벡터 검색 수행

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # 대화 히스토리 가져오기
    messages = state.get("messages", [])

    # 재작성된 쿼리가 있으면 사용, 없으면 원본 질문 사용
    original_query = state.get("rewritten_query") or state.get("question", "")

    # 이전 대화 맥락이 있으면 완전한 질문으로 재구성
    if len(messages) > 1 and not state.get("rewritten_query"):
        # rewritten_query가 없을 때만 (첫 시도) 맥락 고려
        system_prompt_complete = """
당신은 질문 분석 전문가입니다.
이전 대화 맥락을 고려하여 현재 질문을 완전하고 명확한 질문으로 재구성하세요.

예시:
- 이전: "수강신청 정정 기간 언제야?" → 현재: "포기 기간은?" → 재구성: "수강신청 포기 기간은 언제야?"
- 이전: "국가장학금 신청 조건" → 현재: "더 자세히 알려줘" → 재구성: "국가장학금 신청 조건을 더 자세히 알려줘"

완전한 질문만 반환하세요. 설명은 포함하지 마세요.
만약 현재 질문이 이미 완전하다면 그대로 반환하세요.
"""
        conversation_complete = [SystemMessage(content=system_prompt_complete)] + messages
        response_complete = llm.invoke(conversation_complete)
        original_query = response_complete.content.strip()

    # 1. LLM으로 쿼리 분석 및 카테고리 추출 (Structured Output)
    # 시스템 프롬프트: 역할 정의 및 카테고리 설명
    system_prompt = """당신은 검색 쿼리 최적화 전문가입니다.
사용자의 질문을 분석하여 벡터 검색에 최적화된 쿼리를 생성하고, 적절한 카테고리를 선택하는 역할을 수행합니다.

사용 가능한 카테고리:
- 학사일정_휴복학: 학사일정, 공휴일·휴보강, 휴학, 복학, 전과 관련
- 다전공_부전공_이수: 다전공, 부전공, 마이크로전공, 심화전공, 미래설계학기(학점)제 관련
- 졸업_인증: 졸업요건, 조기졸업, 학사학위취득유예·재수, 포트폴리오졸업인증, 외국어졸업인증 관련
- 교육과정_이수기준: 전공·교양 교육과정 편성, 입학연도별 졸업이수학점, 편입·복학생 이수기준 관련
- 수강신청_계절수업: 수강신청 일정·방법·학점, 재수강, 계절수업, 학점교류, 교차수강신청 관련
- 성적_학사경고: 성적평가, 성적이의신청, 학사경고, 강의평가 관련
- 원격수업_이러닝: e-Campus, 원격수업(e-러닝/화상/b-러닝), 온라인 시험(퀴즈) 관련
- 장학금_학자금대출: 교내·교외·국가장학금, 학자금대출 관련

카테고리 선택 규칙:
1. 명확하게 관련 있는 카테고리를 1-2개 선택합니다
2. 여러 카테고리와 관련될 수 있으면 최대 2개까지 선택
3. 애매하거나 확신이 없으면 반드시 null을 반환 (잘못된 카테고리보다 null이 나음)
4. 억지로 카테고리를 선택하지 말고, 확실한 경우에만 선택

출력 지침:
1. optimized_query: 검색에 효과적인 핵심 키워드를 포함한 쿼리로 최적화
2. categories: 명확하게 관련 있는 카테고리 1-2개를 리스트로 반환. 불확실하면 null"""

    # 유저 프롬프트: 실제 질문
    user_prompt = f"다음 질문을 분석해주세요:\n\n{original_query}"

    # 메시지 객체 생성 (Structured Output용)
    llm_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    # Structured Output으로 LLM 호출
    structured_llm = llm.with_structured_output(VectorSearchQuery)
    query_analysis = structured_llm.invoke(llm_messages)

    optimized_query = query_analysis.optimized_query
    categories = query_analysis.categories

    print(f"[벡터 검색 쿼리 분석]")
    print(f"  원본 쿼리: {original_query}")
    print(f"  최적화된 쿼리: {optimized_query}")
    print(f"  선택된 카테고리: {categories}")

    # 2. 병렬 벡터 검색 수행 (카테고리 필터 적용)
    retriever = get_cached_retriever()
    results = retriever.search(optimized_query, k=3, score_threshold=0.5, categories=categories)

    return {
        "vector_results": results
    }


def rewrite_query(state: AgentState) -> AgentState:
    """
    검색 결과가 부족할 때 쿼리를 재작성하는 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # 대화 히스토리 가져오기
    messages = state.get("messages", [])

    system_prompt = """
당신은 검색 쿼리 최적화 전문가입니다.

사용자의 질문이 검색 결과를 얻지 못했습니다.
이전 대화 맥락을 고려하여 질문을 다시 작성하여 더 나은 검색 결과를 얻을 수 있도록 하세요.

최적화 방법:
- 이전 대화에서 언급된 맥락을 포함
- 동의어나 관련 용어 추가
- 질문을 더 구체적이거나 더 일반적으로 변경
- 핵심 키워드 강조

재작성된 쿼리만 반환하세요. 설명은 포함하지 마세요.
"""

    # 시스템 메시지 + 전체 대화 히스토리
    conversation = [SystemMessage(content=system_prompt)] + messages

    response = llm.invoke(conversation)
    rewritten = response.content.strip()

    return {
        "rewritten_query": rewritten,
        "retry_count": state.get("retry_count", 0) + 1
    }


def database_query(state: AgentState) -> AgentState:
    """
    Text2SQL을 수행하여 데이터베이스를 조회하는 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # 대화 히스토리 가져오기
    messages = state.get("messages", [])
    question = state.get("question", "")

    text2sql_engine = get_cached_text2sql_engine()

    # 이전 시도의 피드백 구성: SQL 오류뿐 아니라 "0건 반환"도 재시도에 활용
    previous_error = state.get("error")
    previous_sql = state.get("sql_query")
    if not previous_error and previous_sql and text2sql_engine.is_empty_result(state.get("db_results")):
        previous_error = (
            f"이전 쿼리가 결과를 찾지 못했습니다 (0건 반환):\n{previous_sql}\n"
            "WHERE 조건에 사용한 값이 실제 데이터에 존재하는지, 불필요한 필터를 걸고 있지는 않은지 다시 검토하세요."
        )

    # 이전 대화 맥락이 있으면 완전한 질문으로 재구성
    if len(messages) > 1:
        system_prompt = """
당신은 질문 분석 전문가입니다.
이전 대화 맥락을 고려하여 현재 질문을 완전하고 명확한 질문으로 재구성하세요.

예시:
- 이전: "디자인 분야 인정 학과 알려줘" → 현재: "몇 개야?" → 재구성: "디자인 분야 문화예술교육사 인정 학과가 몇 개야?"
- 이전: "연극 분야 인정 교과목" → 현재: "학점도 알려줘" → 재구성: "연극 분야 문화예술교육사 인정 교과목의 학점도 알려줘"

완전한 질문만 반환하세요. 설명은 포함하지 마세요.
만약 현재 질문이 이미 완전하다면 그대로 반환하세요.
"""
        conversation = [SystemMessage(content=system_prompt)] + messages
        response = llm.invoke(conversation)
        complete_question = response.content.strip()
    else:
        complete_question = question

    # Text2SQL 실행
    result = text2sql_engine.query(complete_question, previous_error=previous_error)

    return {
        "sql_query": result["sql_query"],
        "db_results": result["result"],
        "error": result["error"],
        "retry_count": state.get("retry_count", 0) + 1
    }


def generate_answer(state: AgentState) -> AgentState:
    """
    검색 결과를 바탕으로 최종 답변을 생성하는 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # 대화 히스토리 가져오기
    messages = state.get("messages", [])

    # 검색 결과가 전혀 없는 경우, LLM 호출 없이 고정 답변을 반환
    # (프롬프트 지시만으로는 "정보 없음" 처리를 100% 보장할 수 없어 코드로 강제)
    if (
        state.get("intent") in ("vector", "database")
        and not state.get("vector_results")
        and not state.get("db_results")
    ):
        return {
            "messages": [AIMessage(
                content="해당 정보를 찾을 수 없습니다. 이 챗봇은 상명대학교 학사 정보만 안내합니다."
            )],
            "citations": [],
        }

    # 컨텍스트 구성
    context_parts = []

    # 벡터 검색 결과가 있으면 추가
    if state.get("vector_results"):
        docs = state["vector_results"]
        context_parts.append("관련 문서:")
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "알 수 없음")
            page = doc.metadata.get("page", "?")
            category = doc.metadata.get("category", "")

            # 출처 정보 구성
            source_info = f"출처: {source}, 페이지: {page}"
            if category:
                source_info += f", 카테고리: {category}"

            context_parts.append(f"\n[문서 {i}] {source_info}\n{doc.page_content}")

    # DB 검색 결과가 있으면 추가
    if state.get("db_results"):
        context_parts.append(f"\n\n데이터베이스 조회 결과:\n{state['db_results']}")
        if state.get("sql_query"):
            context_parts.append(f"\n실행된 SQL:\n{state['sql_query']}")

    context = "\n".join(context_parts)

    docs = state.get("vector_results") or []

    citation_rule = (
        "- [문서 N] 내용을 인용해서 답변한 문장 끝에는 반드시 해당 번호를 [N] 형식으로 표기하세요 "
        '(예: "휴학은 최대 4학기까지 가능합니다[1]."). 여러 문서를 참고했다면 [1][2]처럼 모두 표기하세요'
        if docs else
        "- 데이터베이스 조회 결과를 바탕으로 답변할 때는 [N] 같은 인용 표기를 사용하지 마세요"
    )

    system_prompt = f"""
당신은 문화예술교육사(2급) 인정 학과·인정 교과목(art, art_2) 정보와 상명대학교 학사 안내(휴학·복학, 졸업, 수강신청, 성적, 장학금 등) 전문가입니다.

다음 정보를 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요:

<context>
{context}
</context>

답변 시 다음 규칙을 따르세요:
- 주어진 정보를 자연스럽고 간결하게 전달하세요
- 구체적인 날짜, 수치, 학점, 분야, 학과명 등의 정보를 명확히 포함하세요
- 불필요한 전제 조건이나 한계를 언급하지 말고, 질문에 직접 답변하세요
- 위 <context>가 비어있거나, 질문이 상명대학교가 아닌 다른 학교(예: 질문에 다른 대학교 이름이 명시된 경우)에 관한 것이라면, 절대로 일반 지식으로 추측하여 답변하지 말고 "해당 정보를 찾을 수 없습니다. 이 챗봇은 상명대학교 학사 정보만 안내합니다."라고 답변하세요
- 그 외의 경우, 정보가 정말로 없는 경우에만 "해당 정보를 찾을 수 없습니다"라고 말하세요
- 사용자에게 도움이 되는 친절하고 자연스러운 어조로 답변하세요
- 이전 대화 맥락을 고려하여 답변하세요
{citation_rule}
"""

    # 시스템 메시지 + 기존 대화 히스토리
    conversation = [SystemMessage(content=system_prompt)] + messages

    response = llm.invoke(conversation)
    answer = response.content

    # 답변에서 실제로 인용된 [N] 표기를 찾아 출처 목록 구성
    citations = []
    if docs:
        cited_indices = sorted(set(int(n) for n in re.findall(r"\[(\d+)\]", answer)))
        for idx in cited_indices:
            if 1 <= idx <= len(docs):
                doc = docs[idx - 1]
                citations.append({
                    "index": idx,
                    "source": doc.metadata.get("source", "알 수 없음"),
                    "page": doc.metadata.get("page", "N/A"),
                })

    return {
        "messages": [AIMessage(content=answer)],
        "citations": citations,
    }


def grade_answer(state: AgentState) -> AgentState:
    """
    생성된 답변이 검색된 근거(문서/DB 결과)에 실제로 기반하는지 검증하는 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태 (is_grounded, grounding_reason)
    """
    messages = state.get("messages", [])
    answer = messages[-1].content if messages else ""

    # 근거가 필요 없는 general 답변(인사 등)은 검증을 건너뜀
    if state.get("intent") == "general":
        return {"is_grounded": True, "grounding_reason": None}

    vector_results = state.get("vector_results")
    db_results = state.get("db_results")

    context_parts = []
    if vector_results:
        for i, doc in enumerate(vector_results, 1):
            context_parts.append(f"[문서 {i}]\n{doc.page_content}")
    if db_results:
        context_parts.append(f"[DB 조회 결과]\n{db_results}")
    # 검색 결과가 비어있는 경우도 명시적으로 전달 (근거 없이 답변했는지 판단 가능하도록)
    context = "\n\n".join(context_parts) if context_parts else "(검색된 근거 없음)"

    system_prompt = f"""
당신은 AI 답변의 사실 근거를 검증하는 평가자입니다.

아래 <근거> 안의 정보만을 기준으로, <답변>의 핵심 내용이 실제로 근거에 의해 뒷받침되는지 평가하세요.
근거가 "(검색된 근거 없음)"인데 답변이 구체적인 사실을 주장하고 있다면, 이는 근거 없이 지어낸 답변이므로 반드시 is_grounded: false로 평가하세요.

<근거>
{context}
</근거>

<답변>
{answer}
</답변>

평가 기준:
- 답변의 핵심 사실(날짜, 수치, 학점, 학과명 등)이 근거 안에 실제로 존재하면 is_grounded: true
- 답변이 근거에 없는 내용을 지어내거나(hallucination), 근거와 명백히 다른 내용을 말하면 is_grounded: false
- 답변이 단순히 "정보를 찾을 수 없다"는 취지라면 is_grounded: true로 간주하세요 (근거 없다고 정직하게 말한 것이므로)
"""

    structured_llm = llm.with_structured_output(GroundingCheck)
    grading = structured_llm.invoke([SystemMessage(content=system_prompt)])

    return {
        "is_grounded": grading.is_grounded,
        "grounding_reason": grading.reason,
    }


def route_by_intent(state: AgentState) -> str:
    """
    의도에 따라 다음 노드를 결정하는 라우팅 함수

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    intent = state.get("intent", "general")

    if intent == "general":
        return "general_answer"
    elif intent == "database":
        return "database_query"
    elif intent == "vector":
        return "vector_search"
    else:
        return "general_answer"


def check_vector_results(state: AgentState) -> str:
    """
    벡터 검색 결과를 확인하고 다음 노드를 결정하는 함수

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    results = state.get("vector_results", [])
    retry_count = state.get("retry_count", 0)

    # 결과가 있거나 재시도 횟수가 2회 이상이면 답변 생성
    retriever = get_cached_retriever()
    if retriever.is_relevant(results) or retry_count >= 2:
        return "generate_answer"
    else:
        return "rewrite_query"


def check_db_results(state: AgentState) -> str:
    """
    데이터베이스 검색 결과를 확인하고 다음 노드를 결정하는 함수

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    error = state.get("error")
    result = state.get("db_results")
    retry_count = state.get("retry_count", 0)

    # 오류가 없고 결과가 있으면 답변 생성
    text2sql_engine = get_cached_text2sql_engine()
    if not error and result and not text2sql_engine.is_empty_result(result):
        return "generate_answer"

    # 재시도 횟수가 2회 이상이면 답변 생성 (오류 메시지 포함)
    if retry_count >= 2:
        return "generate_answer"

    # 재시도
    return "database_query"