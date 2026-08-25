｢SMU_GUIDE RAG SYSTEM｣ 
사용자가 궁금한 학사 정보를 자연어로 질문하면 AI가 관련 자료를 검색하고, 필요한 정보를 이해하기 쉬운 형태로 안내해주는 AI 기반 학사안내 시스템을 기획하였다.
상명대학교 학사안내 PDF 자료를 기반으로 RAG 시스템을 구축하여 사용자의 질문과 관련된 학사 정보를 검색하도록 하였다.
질문의 유형에 따라 일반 답변, 학사 문서 검색, 데이터베이스 조회로 작업을 구분하고, 검색 결과가 부족하거나 데이터베이스 조회에 오류가 발생할 경우 재검색 및 SQL 재생성을 수행하도록 AI 워크플로를 구현하였다.
이를 통해 학생들이 학사 자료를 직접 찾아보는 번거로움을 줄이고, 자연어 질문만으로 필요한 학사 정보를 빠르게 확인할 수 있도록 하였다.


＃ 예시 질문 5개
1. 문화예술학사를 취득 할 수 있는 학과
2. 인더스트리얼디자인전공이 문화예술학사를 취득하기 위한 인정 교과목명
3. 상명대학교 장학금 제도
4. 상명대학교 휴학 제도
5. 단국대학교 수강신청 기간

# 데모 실행 화면
<img width="1432" height="695" alt="image" src="https://github.com/user-attachments/assets/378831be-2578-4411-98dd-a0d7ebc62184" />
<img width="1432" height="443" alt="image" src="https://github.com/user-attachments/assets/f98992c4-eb00-4cf5-b9b3-554a1f4e729e" />
<img width="1432" height="630" alt="image" src="https://github.com/user-attachments/assets/e374d64e-53c4-4581-8d2a-5436099a3eb6" />
<img width="1432" height="658" alt="image" src="https://github.com/user-attachments/assets/ccce4d6d-1b5b-4e2c-9725-f6e51be33398" />
<img width="1432" height="172" alt="image" src="https://github.com/user-attachments/assets/a505dfbf-3315-4a4c-8774-a71ac3f544e9" />


