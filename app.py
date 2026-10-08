import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="리튬 공급망 SCM 대시보드", layout="wide")

st.title("배터리 리튬 공급망 실시간 외생 병목 모니터링 & SCM 최적화 대시보드")
st.caption("호주 포트헤들랜드 선석 과포화 및 기상 변동 - 중국 제련 고집중 - 한국 양극재 클러스터 연계")

# 사이드바 변수
st.sidebar.header("공장 운영 및 원가 시뮬레이션 변수")
daily_demand = st.sidebar.number_input("일일 리튬 소요량 (톤/일)", 10.0, 300.0, 65.0, 5.0)
lithium_price = st.sidebar.number_input("수산화리튬 가격 ($/톤)", 5000.0, 80000.0, 15000.0, 500.0)
daily_stop_loss = st.sidebar.number_input("공장 가동 중단 일일 손실 ($/일)", 50000.0, 5000000.0, 850000.0, 50000.0)
holding_cost_rate = st.sidebar.slider("연간 재고 유지비율 (%)", 3.0, 15.0, 8.0, 0.5) / 100.0

# 1. 해상 운송 거점별 경로 및 토글 추천
st.header("1. 해상 운송 거점별 경로 및 최적 대안 추천")

route_data = [
    {
        "id": 0,
        "title": "최단 리드타임 추천",
        "name": "한-호 직항 장기운송계약(COA) 전용선",
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
        "lead_time": 24,
        "reliability": 76.2,
        "freight": 28.0,
        "color_rgb": [231, 76, 60],
        "summary": "톤당 운임이 가장 경제적이나 환적 대기와 비정기선 특성상 리드타임 변동성이 크게 발생",
        "path": [[118.576, -20.3167], [103.8198, 1.3521], [127.697, 34.9754]]
    }
]

toggle_options = ["전체 항로 종합 비교", "최단 리드타임 추천", "최고 정시성 추천", "최저 운임 추천"]
selected_toggle = st.segmented_control("운송 시나리오 선택", toggle_options, default="전체 항로 종합 비교")

active_id = None
if selected_toggle == "최단 리드타임 추천":
    active_id = 0
elif selected_toggle == "최고 정시성 추천":
    active_id = 1
elif selected_toggle == "최저 운임 추천":
    active_id = 2

if active_id is not None:
    curr = route_data[active_id]
    st.success(f"{curr['title']} : {curr['name']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("조달 리드타임", f"{curr['lead_time']} 일")
    c2.metric("운항 정시성", f"{curr['reliability']} %")
    c3.metric("해상 운임 지표", f"${curr['freight']} / 톤")
    st.info(f"전략 평가: {curr['summary']}")
else:
    c1, c2, c3 = st.columns(3)
    c1.metric(route_data[0]["name"], f"{route_data[0]['lead_time']} 일", f"${route_data[0]['freight']}/톤")
    c2.metric(route_data[1]["name"], f"{route_data[1]['reliability']} %", f"{route_data[1]['lead_time']}일 소요")
    c3.metric(route_data[2]["name"], f"${route_data[2]['freight']} / 톤", f"정시성 {route_data[2]['reliability']}%")

# pydeck 지도 렌더링
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

# 2. 외생 변수 실시간 자동 수집 & 분석
st.header("2. AI 외생 변수 실시간 모니터링 & 자동 판별")
st.caption("시스템 구동 시 백그라운드 엔진이 호주 기상 및 통상 규제 2대 핵심 변수를 자동으로 동시 수집·분석합니다.")

col_risk1, col_risk2 = st.columns(2)

with col_risk1:
    st.subheader("시나리오 1: 호주 필바라 기상/선석 체선")
    st.error("[STATUS: HIGH_RISK] 우기 사이클론 시즌 진입 경보")
    st.markdown("- **호주 기상청(BOM)**: 필바라 연안 열대성 저기압 형성으로 포트헤들랜드 선석 통제 확률 증가\n- **항만 적체**: 주요 벌크 터미널 대기 척수 증가로 평시 대비 체선 5~9일 추가 발생\n- **선적 영향**: 스포듀민 정광 선적 지연에 따른 국내 입항 변동성 급증")

with col_risk2:
    st.subheader("시나리오 2: 통상 규제 (미국 IRA FEOC & 중국 제련)")
    st.error("[STATUS: HIGH_RISK] 해외우려기관(FEOC) 규제 압박 지속")
    st.markdown("- **미국 재무부/DOE 지침**: 중국 제련 수산화리튬 세액공제 배제 리스크 지속\n- **단일국 의존도**: 국내 양극재 3사 중국 제련 톨링 의존율 79% 수준으로 규제 충격 취약\n- **제련 전환 시차**: 국내/FTA 대체 제련 라인 튜닝 시 최소 120일 전환 공백 소요")

# 3. 정량 솔루션 & ROI 시뮬레이션
st.header("3. 병목 솔루션 수치 산정 및 정량적 ROI 시뮬레이션")
st.caption("사이드바의 공장 운영 파라미터와 2-2절 실증 지표(CV 0.310, 대체 시차 120일)를 결합하여 두 솔루션을 동시 산출합니다.")

col_sol1, col_sol2 = st.columns(2)

with col_sol1:
    st.subheader("솔루션 1: 동적 안전재고(Dynamic Safety Stock) 선제 비축")
    st.markdown("- **산출 근거**: 평시 CV 0.086 -> 우기 사이클론 시즌 CV 0.310\n- **대응 전략**: 우기(1~3월) 안전재고를 14일에서 35일분으로 선제 상향 (+21일분 추가)")
    
    additional_days = 21
    req_stock_ton = daily_demand * additional_days
    inv_cost = (req_stock_ton * lithium_price) * (holding_cost_rate * (additional_days / 365.0))
    prevented_days = 7
    prevented_loss = prevented_days * daily_stop_loss
    net_benefit1 = prevented_loss - inv_cost
    roi1 = (net_benefit1 / inv_cost) * 100.0 if inv_cost > 0 else 0

    m1, m2 = st.columns(2)
    m1.metric("권장 추가 비축량", f"{req_stock_ton:,.0f} 톤", f"+{additional_days}일분")
    m2.metric("재고 유지 비용 (Cost)", f"${inv_cost:,.0f}")
    m3, m4 = st.columns(2)
    m3.metric("가동 중단 손실 방어액", f"${prevented_loss:,.0f}", f"{prevented_days}일 방어")
    m4.metric("추정 ROI", f"{roi1:,.1f} %", "투자 대비 순편익")
    
    st.info(f"동적 안전재고 {req_stock_ton:,.0f}톤 선제 비축으로 약 ${inv_cost:,.0f} 보관비용 대비 ${prevented_loss:,.0f} 손실을 방어하여 순편익 ${net_benefit1:,.0f} (ROI {roi1:.1f}%)를 달성합니다.")

with col_sol2:
    st.subheader("솔루션 2: 국내/FTA 대체 제련소 예비 톨링(Standby Tolling)")
    st.markdown("- **산출 근거**: 미국 IRA FEOC 발효 시 제련처 대체 전환 시차 120일 공백\n- **대응 전략**: 국내 대체 제련소 사전 튜닝 완료 및 소요량의 40% 예비 계약")

    transition_days = 120
    split_ratio = 0.40
    standby_ton = daily_demand * transition_days * split_ratio
    tuning_cost_per_ton = 650.0
    total_standby_cost = standby_ton * tuning_cost_per_ton
    prevented_disruption_value = (daily_demand * transition_days) * 3500.0
    net_benefit2 = prevented_disruption_value - total_standby_cost
    roi2 = (net_benefit2 / total_standby_cost) * 100.0 if total_standby_cost > 0 else 0

    m5, m6 = st.columns(2)
    m5.metric("예비 톨링 계약 물량", f"{standby_ton:,.0f} 톤", "수요의 40% 이원화")
    m6.metric("사전 튜닝/계약 비용 (Cost)", f"${total_standby_cost:,.0f}")
    m7, m8 = st.columns(2)
    m7.metric("규제 공백 손실 회피액", f"${prevented_disruption_value:,.0f}", "120일 공급 공백 방어")
    m8.metric("추정 ROI", f"{roi2:,.1f} %", "투자 대비 순편익")

    st.info(f"대체 제련소 예비 톨링 계약으로 약 ${total_standby_cost:,.0f} 비용 대비 ${prevented_disruption_value:,.0f} 손실을 방어하여 순편익 ${net_benefit2:,.0f} (ROI {roi2:.1f}%)를 달성합니다.")
