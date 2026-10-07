import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import requests
import json

# ---------------------------------------------------------
# 0. 기본 설정 및 사이드바 시뮬레이션 파라미터
# ---------------------------------------------------------
st.set_page_config(
    page_title="리튬 공급망 조달 병목 대응 의사결정 시스템",
    layout="wide"
)

# 토글 슬라이드 세그먼트 및 카드 애니메이션 커스텀 CSS
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    /* 슬라이드 다운 애니메이션 카드 */
    .route-card {
        padding: 24px;
        border-radius: 14px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025);
        margin-top: 15px;
        margin-bottom: 25px;
        animation: slideDownFade 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes slideDownFade {
        from { opacity: 0; transform: translateY(-12px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

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
# 1. 해상 운송 거점별 경로 및 토글 슬라이드 UI
# ---------------------------------------------------------
st.header("1. 해상 운송 거점별 경로 및 최적 대안 추천")

route_data = [
    {
        "id": 0,
        "title": "최단 리드타임 추천",
        "name": "한-호 직항 장기운송계약(COA) 전용선",
        "vessel_type": "Supramax 55,000 DWT",
        "route_desc": "호주 포트헤들랜드 선적 -> 한국 광양 직항 입항 (지정 전용 선석)",
        "lead_time": 14,
        "reliability": 94.5,
        "freight": 42.0,
        "color": "#2ecc71",
        "summary": "우기 사이클론 시즌 및 선석 체선 리스크를 최소화하여 공장 셧다운을 완벽 방어하는 최우선 안정 항로입니다.",
        "coords": [[-20.3167, 118.576], [34.9754, 127.697]]
    },
    {
        "id": 1,
        "title": "최고 정시성 추천",
        "name": "중국 제련 톨링 경유 정기선",
        "vessel_type": "Ultramax 62,000 DWT",
        "route_desc": "호주 포트헤들랜드 -> 중국 닝보 기항 (정기 컨테이너/벌크 셔틀)",
        "lead_time": 18,
        "reliability": 88.0,
        "freight": 33.5,
        "color": "#3498db",
        "summary": "중국 내 가공 위탁 라인과 연계된 안정적 스케줄 항로이나, 통상 규제(FEOC) 시 대체 전환 조치가 필요합니다.",
        "coords": [[-20.3167, 118.576], [29.8683, 121.544]]
    },
    {
        "id": 2,
        "title": "최저 운임 추천",
        "name": "스팟 시장 자유 용선 (동남아 환적)",
        "vessel_type": "Handymax 45,000 DWT",
        "route_desc": "호주 -> 싱가포르항 환적 -> 한국 광양 (스팟 용선 부킹)",
        "lead_time": 24,
        "reliability": 76.2,
        "freight": 28.0,
        "color": "#e74c3c",
        "summary": "톤당 운임이 가장 경제적이나, 환적 대기와 비정기선 특성상 리드타임 변동성이 크게 발생하는 옵션입니다.",
        "coords": [[-20.3167, 118.576], [1.3521, 103.8198], [34.9754, 127.697]]
    }
]

# 가로형 토글 슬라이드 세그먼트 컨트롤 UI
toggle_options = ["🌐 전체 항로 종합 비교", "🚀 최단 리드타임 추천", "⏱️ 최고 정시성 추천", "💰 최저 운임 추천"]

selected_toggle = st.segmented_control(
    "운송 최적화 시나리오 선택",
    toggle_options,
    default="🌐 전체 항로 종합 비교",
    label_visibility="collapsed"
)

# 토글 선택값에 따른 active_id 매핑
if selected_toggle == "🚀 최단 리드타임 추천":
    active_id = 0
elif selected_toggle == "⏱️ 최고 정시성 추천":
    active_id = 1
elif selected_toggle == "💰 최저 운임 추천":
    active_id = 2
else:
    active_id = None

# 슬라이드 다운 세부 정보 패널 (전체 보기일 때와 단일 선택일 때의 반응)
if active_id is not None:
    curr = route_data[active_id]
    st.markdown(f"""
    <div class="route-card" style="border-left: 6px solid {curr['color']};">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin:0; color: #1e293b; font-size: 1.35rem;">📌 {curr['title']} : {curr['name']}</h3>
            <span style="background-color: {curr['color']}; color: white; padding: 5px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">선택된 최적 대안</span>
        </div>
        <p style="margin: 10px 0 16px 0; color: #64748b; font-size: 1.05rem;">{curr['route_desc']} (투입 선형: <b>{curr['vessel_type']}</b>)</p>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 14px;">
            <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #e2e8f0;">
                <div style="font-size: 0.85rem; color: #64748b;">조달 소요 일수 (리드타임)</div>
                <div style="font-size: 1.7rem; font-weight: bold; color: #0f172a;">{curr['lead_time']} 일</div>
            </div>
            <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #e2e8f0;">
                <div style="font-size: 0.85rem; color: #64748b;">운항 정시성 지수</div>
                <div style="font-size: 1.7rem; font-weight: bold; color: #0f172a;">{curr['reliability']} %</div>
            </div>
            <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #e2e8f0;">
                <div style="font-size: 0.85rem; color: #64748b;">해상 운임 지표</div>
                <div style="font-size: 1.7rem; font-weight: bold; color: #0f172a;">${curr['freight']} <span style="font-size: 0.95rem; font-weight: normal; color: #64748b;">/ 톤</span></div>
            </div>
        </div>
        <div style="font-size: 0.95rem; color: #334155; line-height: 1.5;"><b>전략 분석</b>: {curr['summary']}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    # 전체 보기 모드일 때 간략 요약 그리드 노출
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.caption("최단 리드타임 대안")
        st.metric(route_data[0]["name"], f"{route_data[0]['lead_time']} 일", f"${route_data[0]['freight']}/톤")
    with col_b:
        st.caption("최고 정시성 대안")
        st.metric(route_data[1]["name"], f"{route_data[1]['reliability']} %", f"{route_data[1]['lead_time']}일 소요")
    with col_c:
        st.caption("최저 운임 대안")
        st.metric(route_data[2]["name"], f"${route_data[2]['freight']} / 톤", f"정시성 {route_data[2]['reliability']}%")

# ---------------------------------------------------------
# 오픈스트리트맵(OSM) 기반 상태 유지 Leaflet 지도 (키 불필요)
# ---------------------------------------------------------
routes_json = json.dumps(route_data)
active_id_str = "null" if active_id is None else str(active_id)

map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body, #map {{
            width: 100%;
            height: 440px;
            margin: 0;
            padding: 0;
            border-radius: 12px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const savedLat = sessionStorage.getItem('map_lat') || 8.0;
        const savedLng = sessionStorage.getItem('map_lng') || 120.0;
        const savedZoom = sessionStorage.getItem('map_zoom') || 3;

        const map = L.map('map').setView([savedLat, savedLng], savedZoom);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 18
        }}).addTo(map);

        map.on('moveend', function() {{
            const center = map.getCenter();
            sessionStorage.setItem('map_lat', center.lat);
            sessionStorage.setItem('map_lng', center.lng);
            sessionStorage.setItem('map_zoom', map.getZoom());
        }});

        const routes = {routes_json};
        const activeId = {active_id_str};

        const ports = [
            {{name: "호주 포트헤들랜드 (스포듀민 선적항)", coords: [-20.3167, 118.576]}},
            {{name: "중국 닝보항 (제련 거점 기항)", coords: [29.8683, 121.544]}},
            {{name: "한국 광양항 (수산화리튬 양하항)", coords: [34.9754, 127.697]}},
            {{name: "싱가포르항 (환적 거점)", coords: [1.3521, 103.8198]}}
        ];

        ports.forEach(p => {{
            L.circleMarker(p.coords, {{
                radius: 6,
                fillColor: '#1e293b',
                color: '#ffffff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.95
            }}).bindTooltip(p.name).addTo(map);
        }});

        routes.forEach(r => {{
            let isSelected = (activeId !== null && r.id === activeId);
            let isNone = (activeId === null);

            let weight = isNone ? 4 : (isSelected ? 6 : 2);
            let opacity = isNone ? 0.85 : (isSelected ? 1.0 : 0.2);
            let color = (isNone || isSelected) ? r.color : '#cbd5e1';

            let line = L.polyline(r.coords, {{
                color: color,
                weight: weight,
                opacity: opacity
            }}).addTo(map);

            line.bindTooltip(`<b>${{r.title}}</b><br>${{r.name}}<br>소요: ${{r.lead_time}}일 | 운임: $${{r.freight}}/톤`);
        }});
    </script>
</body>
</html>
"""

components.html(map_html, height=460)

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
