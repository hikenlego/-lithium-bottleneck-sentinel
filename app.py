import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import requests

# ---------------------------------------------------------
# 0. 기본 설정 및 애니메이션 CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="리튬 공급망 SCM 의사결정 시스템",
    layout="wide"
)

# 모던 토글 바 및 카드 슬라이드다운 애니메이션 주입
anim_css = (
    "<style>"
    "div[data-testid='stMetricValue'] { font-size: 1.8rem; }"
    "div[data-testid='stSegmentedControl'] {"
    "    background: #f1f5f9; padding: 6px; border-radius: 14px;"
    "    border: 1px solid #e2e8f0; box-shadow: inset 0 2px 4px rgba(0,0,0,0.04);"
    "}"
    "div[data-testid='stSegmentedControl'] button {"
    "    border-radius: 10px !important; font-weight: 600 !important; border: none !important;"
    "    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;"
    "}"
    "div[data-testid='stSegmentedControl'] button:hover {"
    "    transform: translateY(-1px);"
    "    background-color: rgba(255, 255, 255, 0.8) !important;"
    "}"
    "div[data-testid='stSegmentedControl'] button[aria-checked='true'] {"
    "    background: #ffffff !important; color: #0f172a !important;"
    "    box-shadow: 0 4px 10px -2px rgba(0, 0, 0, 0.1) !important;"
    "    transform: scale(1.02);"
    "}"
    ".route-detail-box {"
    "    padding: 20px; border-radius: 12px; background: #ffffff;"
    "    border: 1px solid #e2e8f0; margin-top: 15px; margin-bottom: 20px;"
    "    box-shadow: 0 4px 12px rgba(0,0,0,0.05);"
    "    animation: fadeSlide 0.35s ease-out;"
    "}"
    "@keyframes fadeSlide {"
    "    from { opacity: 0; transform: translateY(-8px); }"
    "    to { opacity: 1; transform: translateY(0); }"
    "}"
    "</style>"
)
st.markdown(anim_css, unsafe_allow_html=True)

st.title("배터리 리튬 공급망 실시간 외생 병목 모니터링 & SCM 최적화 대시보드")
st.markdown("호주 포트헤들랜드 선석 과포화 및 기상 변동 - 중국 제련 고집중 - 한국 양극재 클러스터 연계")

# 사이드바 변수 설정
st.sidebar.header("공장 운영 및 원가 시뮬레이션 변수")
daily_demand = st.sidebar.number_input("일일 리튬 소요량 (톤/일)", 10.0, 300.0, 65.0, 5.0)
lithium_price = st.sidebar.number_input("수산화리튬 가격 ($/톤)", 5000.0, 80000.0, 15000.0, 500.0)
daily_stop_loss = st.sidebar.number_input("공장 가동 중단 일일 손실 ($/일)", 50000.0, 5000000.0, 850000.0, 50000.0)
holding_cost_rate = st.sidebar.slider("연간 재고유지비율 (%)", 3.0, 15.0, 8.0, 0.5) / 100.0

# ---------------------------------------------------------
# 1. 해상 운송 거점별 경로 시각화 및 애니메이션 토글 추천
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
        "color_rgb": [46, 204, 113],
        "summary": "우기 사이클론 시즌 및 선석 체선 리스크를 최소화하여 공장 셧다운을 완벽 방어하는 최우선 안정 항로",
        "path": [[118.576, -20.3167], [127.697, 34.9754]]
    },
    {
        "id": 1,
        "title": "최고 정시성 추천",
        "name": "중국 제련 톨링 경유 정기선",
        "vessel_type": "Ultramax 62,000 DWT",
        "route_desc": "호주 포트헤들랜드 -> 중국 닝보 기항 (정기 셔틀)",
        "lead_time": 18,
        "reliability": 88.0,
        "freight": 33.5,
        "color_rgb": [52, 152, 219],
        "summary": "중국 내 가공 위탁 라인과 연계된 정기 항로이나, 통상 규제(FEOC) 시 대체 전환 조치 필요",
        "path": [[118.576, -20.3167], [121.544, 29.8683]]
    },
    {
        "id": 2,
        "title": "최저 운임 추천",
        "name": "스팟 시장 자유 용선 (동남아 환적)",
        "vessel_type": "Handymax 45,000 DWT",
        "route_desc": "호주 -> 싱가포르 환적 -> 한국 광양 (스팟 용선)",
        "lead_time": 24,
        "reliability": 76.2,
        "freight": 28.0,
        "color_rgb": [231, 76, 60],
        "summary": "톤당 운임이 가장 경제적이나 환적 대기와 비정기선 특성상 리드타임 변동성이 크게 발생",
        "path": [[118.576, -20.3167], [103.8198, 1.3521], [127.697, 34.9754]]
    }
]

# 가로형 슬라이드 토글 세그먼트
toggle_options = ["전체 항로 종합 비교", "최단 리드타임 추천", "최고 정시성 추천", "최저 운임 추천"]
selected_toggle = st.segmented_control("운송 시나리오 선택", toggle_options, default="전체 항로 종합 비교")

active_id = None
if selected_toggle == "최단 리드타임 추천":
    active_id = 0
elif selected_toggle == "최고 정시성 추천":
    active_id = 1
elif selected_toggle == "최저 운임 추천":
    active_id = 2

# 하단 상세 정보 패널 (애니메이션 박스)
if active_id is not None:
    curr = route_data[active_id]
    r_hex = f"#{curr['color_rgb'][0]:02x}{curr['color_rgb'][1]:02x}{curr['color_rgb'][2]:02x}"
    info_box = (
        f"<div class='route-detail-box' style='border-left: 6px solid {r_hex};'>"
        f"  <div style='display:flex; justify-content:space-between; align-items:center;'>"
        f"    <h3 style='margin:0; color:#1e293b;'>📌 {curr['title']} : {curr['name']}</h3>"
        f"    <span style='background:{r_hex}; color:white; padding:4px 12px; border-radius:15px; font-weight:bold; font-size:0.85rem;'>선택된 최적 경로</span>"
        f"  </div>"
        f"  <p style='margin:8px 0 14px 0; color:#64748b;'>{curr['route_desc']} (투입 선형: <b>{curr['vessel_type']}</b>)</p>"
        f"  <div style='color:#334155; margin-bottom:10px;'><b>전략 평가</b>: {curr['summary']}</div>"
        f"</div>"
    )
    st.markdown(info_box, unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("조달 리드타임", f"{curr['lead_time']} 일")
    c2.metric("운항 정시성", f"{curr['reliability']} %")
    c3.metric("해상 운임 지표", f"${curr['freight']} / 톤")
else:
    c1, c2, c3 = st.columns(3)
    c1.metric(route_data[0]["name"], f"{route_data[0]['lead_time']} 일", f"${route_data[0]['freight']}/톤")
    c2.metric(route_data[1]["name"], f"{route_data[1]['reliability']} %", f"{route_data[1]['lead_time']}일 소요")
    c3.metric(route_data[2]["name"], f"${route_data[2]['freight']} / 톤", f"정시성 {route_data[2]['reliability']}%")

# 지도 레이어 구성 (pydeck WebGL 기반)
routes_layer_data = []
for r in route_data:
    if active_id is None:
        color = r["color_rgb"] + [220]
        width = 45000
    else:
        if r["id"] == active_id:
            color = r["color_rgb"] + [255]
            width = 85000
        else:
            color = [180, 180, 180, 40]
            width = 20000

    routes_layer_data.append({
        "name": r["name"],
        "path": r["path"],
        "color": color,
        "width": width,
        "tooltip": f"{r['title']} - {r['name']} ({r['lead_time']}일, ${r['freight']}/톤)"
    })

ports_data = [
    {"name": "호주 포트헤들랜드 (선적항)", "coords": [118.576, -20.3167]},
    {"name": "중국 닝보항 (제련 기항)", "coords": [121.544, 29.8683]},
    {"name": "한국 광양항 (양하항)", "coords": [127.697, 34.9754]},
    {"name": "싱가포르항 (환적 거점)", "coords": [103.8198, 1.3521]}
]

path_layer = pdk.Layer(
    "PathLayer",
    data=routes_layer_data,
    get_path="path",
    get_color="color",
    width_min_pixels=3,
    get_width="width",
    pickable=True
)

scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=ports_data,
    get_position="coords",
    get_color=[30, 41, 59],
    get_radius=110000,
    pickable=True
)

view_state = pdk.ViewState(
    longitude=120.0,
    latitude=8.0,
    zoom=2.6,
    pitch=0
)

st.pydeck_chart(
    pdk.Deck(
        layers=[path_layer, scatter_layer],
        initial_view_state=view_state,
        tooltip={"text": "{name}\n{tooltip}"},
        map_provider="carto",
        map_style="light"
    ),
    use_container_width=True
)

# ---------------------------------------------------------
# 2. 내장 프롬프트 기반 Perplexity 실시간 외생 변수 모니터링
# ---------------------------------------------------------
st.header("2. AI 외생 변수 실시간 모니터링 & 자동 판별")
api_key = st.text_input("Perplexity API Key 입력", type="password", placeholder="pplx-...")

target_scenario = st.radio(
    "감지 대상 시나리오 선택",
    (
        "시나리오 1: 호주 필바라 기상 악화 및 항만 폐쇄 (사이클론/라니냐 병목)",
        "시나리오 2: 통상 규제 및 단일국 의존 (미국 IRA FEOC / 중국 수출 통제)"
    )
)

SYSTEM_PROMPT = (
    "You are a raw material supply chain risk monitoring engine. "
    "Analyze real-time external conditions and determine if disruption risk is active. "
    "Classify on the first line strictly as [STATUS: HIGH_RISK] or [STATUS: NORMAL]. "
    "Follow with exactly 3 bullet points summarizing verified recent facts."
)

def query_perplexity(scen, key):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if "시나리오 1" in scen:
        user_q = "Check current weather alerts, cyclone risks, and bulk port operations at Port Hedland Pilbara Western Australia."
    else:
        user_q = "What is the latest status of US IRA FEOC guidelines regarding Chinese lithium refining and impact on Korean cathode manufacturers?"

    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_q}
        ],
        "temperature": 0.1
    }
    res = requests.post(url, json=payload, headers=headers)
    return res.json()["choices"][0]["message"]["content"] if res.status_code == 200 else f"호출 오류: {res.text}"

if st.button("실시간 외생 변수 자동 수집 및 분석 시작"):
    if not api_key:
        st.error("Perplexity API 키를 입력해 주세요.")
    else:
        with st.spinner("글로벌 기상 및 통상 규제 데이터를 실시간 검증 중입니다..."):
            ai_report = query_perplexity(target_scenario, api_key)
        
        st.subheader("실시간 정성 데이터 수집 및 판별 보고서")
        if "HIGH_RISK" in ai_report:
            st.error("경보 발령: 공급망 외부 충격(외생 변수)이 감지되었습니다. 즉시 대응 솔루션을 가동합니다.")
        else:
            st.success("안정 상태: 중대한 외부 병목 요인이 감지되지 않았습니다. 상시 완충 모니터링을 유지합니다.")
        st.markdown(ai_report)

# ---------------------------------------------------------
# 3. 2-2절 실증 지표 기반 솔루션 수치화 & ROI 계산 엔진
# ---------------------------------------------------------
st.header("3. 병목 솔루션 수치 산정 및 정량적 ROI 시뮬레이션")

if "시나리오 1" in target_scenario:
    st.subheader("[솔루션 1]: 동적 안전재고(Dynamic Safety Stock) 선제적 비축 모델")
    st.markdown(
        "- **산출 근거 (2-2 실증 수치)**: 평시 CV 0.086 -> 우기 사이클론 시즌 CV 0.310 (변동폭 3.6배 증폭)\n"
        "- **전략**: 우기(1~3월) 진입 전 안전재고를 평시 14일분에서 **35일분으로 선제적 상향 (+21일분 추가 비축)**"
    )

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
    c3.metric("회피된 셧다운 손실 (Benefit)", f"${prevented_loss:,.0f}", f"{prevented_days}일 방어")
    c4.metric("추정 ROI", f"{roi:,.1f} %")

    st.info(f"동적 안전재고 {req_stock_ton:,.0f}톤을 선제 비축하여 약 ${inv_cost:,.0f}의 비용으로 ${prevented_loss:,.0f}의 가동 중단 손실을 방어하므로 **순편익 ${net_benefit:,.0f} (ROI {roi:.1f}%)**를 달성합니다.")

else:
    st.subheader("[솔루션 2]: 국내/FTA 대체 제련소 예비 톨링(Standby Tolling) 가동 모델")
    st.markdown(
        "- **산출 근거 (2-2 실증 수치)**: 미국 IRA FEOC 발효 시 제련처 대체 전환 시차 **100~150일 (중앙값 120일 공백)** 발생\n"
        "- **전략**: 국내(광양 등) 대체 제련소와 사전 공정 튜닝을 완료하고 **총 소요량의 40%를 예비 톨링 물량으로 사전 계약**"
    )

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
    c2.metric("사전 튜닝/예약비용 (Cost)", f"${total_standby_cost:,.0f}")
    c3.metric("규제 손실 회피 (Benefit)", f"${prevented_disruption_value:,.0f}", "120일 공백 방어")
    c4.metric("추정 ROI", f"{roi:,.1f} %")

    st.info(f"대체 제련소 예비 톨링 계약을 통해 약 ${total_standby_cost:,.0f}의 사전 비용으로 ${prevented_disruption_value:,.0f}의 조달 단절 손실을 차단하여 **순편익 ${net_benefit:,.0f} (ROI {roi:.1f}%)**를 달성합니다.")
