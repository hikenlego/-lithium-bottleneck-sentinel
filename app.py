import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import requests
import json

# ---------------------------------------------------------
# 0. 기본 설정 및 사이드바 시뮬레이션 파라미터
# ---------------------------------------------------------
st.set_page_config(
    page_title="리튬 공급망 조달 병목 대응 의사결정 시스템",
    layout="wide"
)

st.title("배터리 리튬 공급망 실시간 외생 병목 모니터링 & SCM 최적화 대시보드")
st.markdown("호주 포트헤들랜드 선석 과포화 및 기상 변동 - 중국 제련 고집중 - 한국 양극재 클러스터 연계")

# 사이드바: 기업 맞춤형 원가 및 공장 운영 변수 입력 UI
st.sidebar.header("공장 운영 및 원가 시뮬레이션 변수")
st.sidebar.markdown("기업별 맞춤형 파라미터를 조정하여 정밀 ROI를 도출합니다.")

daily_demand = st.sidebar.number_input(
    "일일 수산화리튬 소요량 (톤/일)", 
    min_value=10.0, max_value=300.0, value=65.0, step=5.0
)
lithium_price = st.sidebar.number_input(
    "수산화리튬 현물 가격 ($/톤)", 
    min_value=5000.0, max_value=80000.0, value=15000.0, step=500.0
)
daily_stop_loss = st.sidebar.number_input(
    "공장 가동 중단 시 일일 기회비용 손실 ($/일)", 
    min_value=50000.0, max_value=5000000.0, value=850000.0, step=50000.0
)
holding_cost_rate = st.sidebar.slider(
    "연간 재고 유지비율 (금융이자, 보관료 등 %)", 
    min_value=3.0, max_value=15.0, value=8.0, step=0.5
) / 100.0

# ---------------------------------------------------------
# 1. 해상 운송 거점별 경로 및 최적 대안 추천
# ---------------------------------------------------------
st.header("1. 해상 운송 거점별 경로 및 최적 대안 추천")
st.caption("추천 상단 버튼을 클릭하면 해당 항로가 지도 위에 강조 표시되며, 초기 상태에서는 모든 항로가 균일하게 표시됩니다.")

# 세션 상태 초기화 (초기값 None: 아무것도 선택되지 않은 전체 균일 상태)
if "selected_route_id" not in st.session_state:
    st.session_state.selected_route_id = None

# 실무 계약 모드 기반 표준 운송 데이터셋
route_data = [
    {
        "id": 0,
        "name": "한-호 직항 장기운송계약(COA) 전용선",
        "vessel_type": "Supramax 55,000 DWT",
        "route_desc": "호주 포트헤들랜드 -> 한국 광양 (지정 선석 직송)",
        "lead_time": 14,
        "reliability": 94.5,
        "freight": 42.0,
        "color": "#2ecc71", # 초록색
        "coords": [[-20.3167, 118.576], [34.9754, 127.697]]
    },
    {
        "id": 1,
        "name": "중국 제련 톨링 경유 정기선",
        "vessel_type": "Ultramax 62,000 DWT",
        "route_desc": "호주 포트헤들랜드 -> 중국 닝보 (제련 라인 기항)",
        "lead_time": 18,
        "reliability": 88.0,
        "freight": 33.5,
        "color": "#3498db", # 파란색
        "coords": [[-20.3167, 118.576], [29.8683, 121.544]]
    },
    {
        "id": 2,
        "name": "스팟 시장 자유 용선 (동남아 환적)",
        "vessel_type": "Handymax 45,000 DWT",
        "route_desc": "호주 -> 싱가포르 환적 -> 한국 광양 (스팟 부킹)",
        "lead_time": 24,
        "reliability": 76.2,
        "freight": 28.0,
        "color": "#e74c3c", # 빨간색
        "coords": [[-20.3167, 118.576], [1.3521, 103.8198], [34.9754, 127.697]]
    }
]

# 상단 추천 영역 (버튼 자체로 바로 항로 선택 트리거)
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("최단 리드타임 추천", use_container_width=True, type="primary" if st.session_state.selected_route_id == 0 else "secondary"):
        st.session_state.selected_route_id = 0
    st.metric(route_data[0]["name"], f"{route_data[0]['lead_time']} 일")
    st.caption(f"운임: ${route_data[0]['freight']}/톤 | 정시성: {route_data[0]['reliability']}%")

with col2:
    if st.button("최고 정시성 추천", use_container_width=True, type="primary" if st.session_state.selected_route_id == 1 else "secondary"):
        st.session_state.selected_route_id = 1
    st.metric(route_data[1]["name"], f"{route_data[1]['reliability']} %")
    st.caption(f"리드타임: {route_data[1]['lead_time']}일 | 운임: ${route_data[1]['freight']}/톤")

with col3:
    if st.button("최저 운임 추천", use_container_width=True, type="primary" if st.session_state.selected_route_id == 2 else "secondary"):
        st.session_state.selected_route_id = 2
    st.metric(route_data[2]["name"], f"${route_data[2]['freight']} / 톤")
    st.caption(f"리드타임: {route_data[2]['lead_time']}일 | 정시성: {route_data[2]['reliability']}%")

# 전체 초기화 보조 링크
if st.session_state.selected_route_id is not None:
    if st.button("모든 항로 전체 보기 (초기화)"):
        st.session_state.selected_route_id = None
        st.rerun()

# 지도 시각화 (선택 여부에 따른 조건부 스타일링)
m = folium.Map(location=[5.0, 120.0], zoom_start=3)

for r in route_data:
    # 아무것도 선택되지 않았을 때(None): 모두 기준 두께와 고유 색상으로 균일 표시
    if st.session_state.selected_route_id is None:
        line_weight = 4
        line_opacity = 0.85
        line_color = r["color"]
        tooltip_prefix = "[표준]"
    else:
        # 특정 항로가 선택되었을 때
        is_selected = (r["id"] == st.session_state.selected_route_id)
        line_weight = 6 if is_selected else 2
        line_opacity = 1.0 if is_selected else 0.2
        line_color = r["color"] if is_selected else "#bdc3c7"
        tooltip_prefix = "[선택됨]" if is_selected else "[일반]"

    folium.PolyLine(
        locations=r["coords"],
        color=line_color,
        weight=line_weight,
        opacity=line_opacity,
        tooltip=f"{tooltip_prefix} {r['name']} | {r['lead_time']}일 | ${r['freight']}/톤"
    ).add_to(m)

# 고정 key를 주어 줌 레벨과 드래그 위치가 리셋되지 않고 유지되도록 최적화
st_folium(m, width=1200, height=430, key="main_folium_map", returned_objects=[])

# ---------------------------------------------------------
# 2. 내장 전문 프롬프트 기반 Perplexity 실시간 외생 변수 자동 모니터링
# ---------------------------------------------------------
st.header("2. AI 외생 변수 실시간 모니터링 & 자동 판별")
st.caption("내장된 전문 프롬프트가 Perplexity 웹 검색 API를 통해 글로벌 규제 및 기상 변수를 자동 수집합니다.")

api_key = st.text_input("Perplexity API Key 입력", type="password", placeholder="pplx-...")

SYSTEM_PROMPT = """You are an elite raw material supply chain risk monitoring engine.
Your task is to analyze real-time external conditions and determine if an operational disruption risk is active.
Answer strictly based on verified recent web facts. 
Provide a clear classification at the top:
[STATUS: HIGH_RISK] or [STATUS: NORMAL]
Followed by exactly 3 bullet points summarizing the verified facts (dates, regions, weather/policy updates)."""

target_scenario = st.radio(
    "자동 감지 대상 시나리오 선택",
    (
        "시나리오 1: 호주 필바라 기상 악화 및 항만 폐쇄 (사이클론/라니냐 병목)",
        "시나리오 2: 통상 규제 및 단일국 의존 (미국 IRA FEOC / 중국 수출 통제)"
    )
)

def fetch_perplexity_status(scenario_type, key):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    if "시나리오 1" in scenario_type:
        user_query = "Check the current weather conditions, cyclone warnings, and port operations at Port Hedland and Pilbara Western Australia. Are there active cyclone disruptions, heavy rainfall, or terminal berth closures affecting bulk mining shipments?"
    else:
        user_query = "What is the latest status regarding US IRA FEOC guidelines on Chinese refined lithium hydroxide, or any recent export restrictions from China? Are Korean battery material manufacturers actively facing trade compliance restrictions for Chinese-refined lithium?"

    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ],
        "temperature": 0.1
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"API 연결 오류 (Status {response.status_code}): {response.text}"

is_high_risk = False
ai_report = ""

if st.button("실시간 외생 변수 자동 수집 및 분석 시작"):
    if not api_key:
        st.error("Perplexity API 키를 입력해 주세요.")
    else:
        with st.spinner("호주 기상청 및 글로벌 통상 규제 데이터베이스를 실시간 검색 중입니다..."):
            ai_report = fetch_perplexity_status(target_scenario, api_key)
            if "HIGH_RISK" in ai_report:
                is_high_risk = True

        st.subheader("실시간 정성 데이터 수집 및 판별 보고서")
        if is_high_risk:
            st.error("경보 발령: 공급망 외부 충격(외생 변수)이 감지되었습니다. 즉시 대응 솔루션을 가동합니다.")
        else:
            st.success("안정 상태: 중대한 외부 병목 요인이 감지되지 않았습니다. 상시 완충 모니터링을 유지합니다.")
        
        st.markdown(ai_report)

# ---------------------------------------------------------
# 3. 2-2절 정량 지표 기반 솔루션 수치화 & ROI 계산 엔진
# ---------------------------------------------------------
st.header("3. 병목 솔루션 수치 산정 및 정량적 ROI 시뮬레이션")
st.caption("앞서 실증된 2-2절의 정량 지표(CV 0.310, 대체 시차 120일)와 사이드바 파라미터를 결합하여 산출합니다.")

if "시나리오 1" in target_scenario:
    st.subheader("[솔루션 1]: 동적 안전재고(Dynamic Safety Stock) 선제적 비축 모델")
    st.markdown("""
    - **산출 근거 (2-2 실증 수치)**: 평시 CV 0.086 $\\rightarrow$ 우기 사이클론 시즌 CV 0.310 (변동폭 3.6배 증폭)
    - **전략**: 우기(1~3월) 진입 전 안전재고 일수를 평시 14일분에서 **35일분으로 선제적 상향 (+21일분 추가 비축)**
    """)

    additional_days = 21
    req_stock_ton = daily_demand * additional_days
    inv_cost = (req_stock_ton * lithium_price) * (holding_cost_rate * (additional_days / 365.0))
    prevented_days = 7
    prevented_loss = prevented_days * daily_stop_loss
    net_benefit = prevented_loss - inv_cost
    roi = (net_benefit / inv_cost) * 100.0 if inv_cost > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("권장 추가 비축량", f"{req_stock_ton:,.0f} 톤", f"+{additional_days}일분")
    c2.metric("재고 유지 비용 (Cost)", f"${inv_cost:,.0f}")
    c3.metric("회피된 셧다운 손실 (Benefit)", f"${prevented_loss:,.0f}", f"{prevented_days}일 가동 중단 방어")
    c4.metric("추정 ROI", f"{roi:,.1f} %", "투자 대비 순편익")

    st.info(f"동적 안전재고를 {req_stock_ton:,.0f}톤 선제 비축함으로써, 약 ${inv_cost:,.0f}의 보관 비용으로 ${prevented_loss:,.0f}의 공장 가동 중단 손실을 방어하여 **순편익 ${net_benefit:,.0f} (ROI {roi:.1f}%)**를 달성합니다.")

else:
    st.subheader("[솔루션 2]: 국내/FTA 대체 제련소 예비 톨링(Standby Tolling) 가동 모델")
    st.markdown("""
    - **산출 근거 (2-2 실증 수치)**: 미국 IRA FEOC 발효 시 제련처 대체 전환 시차 **100~150일 (중앙값 120일 공백)** 발생
    - **전략**: 국내(광양 등) 대체 제련소와 사전 가마(킬른) 튜닝을 완료하고 **총 소요량의 40%를 예비 톨링(Standby) 물량으로 사전 계약**
    """)

    transition_days = 120
    split_ratio = 0.40
    standby_ton = daily_demand * transition_days * split_ratio
    tuning_cost_per_ton = 650.0
    total_standby_cost = standby_ton * tuning_cost_per_ton
    
    prevented_disruption_value = (daily_demand * transition_days) * 3500.0
    net_benefit = prevented_disruption_value - total_standby_cost
    roi = (net_benefit / total_standby_cost) * 100.0 if total_standby_cost > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("예비 톨링 계약 물량", f"{standby_ton:,.0f} 톤", "수요의 40% 이원화")
    c2.metric("사전 튜닝/계약비용 (Cost)", f"${total_standby_cost:,.0f}")
    c3.metric("규제 공백 손실 회피 (Benefit)", f"${prevented_disruption_value:,.0f}", "120일 공급 공백 방어")
    c4.metric("추정 ROI", f"{roi:,.1f} %", "투자 대비 순편익")

    st.info(f"대체 제련소 예비 톨링 계약을 통해 약 ${total_standby_cost:,.0f}의 사전 비용을 투입하여, ${prevented_disruption_value:,.0f}에 달하는 조달 단절 및 규제 손실을 선제적으로 차단함으로써 **순편익 ${net_benefit:,.0f} (ROI {roi:.1f}%)**를 달성합니다.")
