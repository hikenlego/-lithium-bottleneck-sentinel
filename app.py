import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

# ---------------------------------------------------------
# 0. 기본 설정 및 모던 대시보드 스타일
# ---------------------------------------------------------
st.set_page_config(
    page_title="리튬 공급망 SCM 인텔리전스 시스템",
    layout="wide"
)

# 토글 슬라이드 및 카드 전환 모션 CSS
anim_css = """
<style>
div[data-testid='stMetricValue'] { font-size: 1.6rem; font-weight: 700; color: #1e293b; }
div[data-testid='stSegmentedControl'] {
    background: #f1f5f9; padding: 6px; border-radius: 14px;
    border: 1px solid #e2e8f0; box-shadow: inset 0 2px 4px rgba(0,0,0,0.03);
}
div[data-testid='stSegmentedControl'] button {
    border-radius: 10px !important; font-weight: 600 !important; border: none !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div[data-testid='stSegmentedControl'] button:hover {
    background-color: rgba(255, 255, 255, 0.8) !important;
}
div[data-testid='stSegmentedControl'] button[aria-checked='true'] {
    background: #ffffff !important; color: #0f172a !important;
    box-shadow: 0 4px 10px -2px rgba(0, 0, 0, 0.1) !important;
    transform: scale(1.02);
}
.route-detail-box {
    padding: 20px; border-radius: 12px; background: #ffffff;
    border: 1px solid #e2e8f0; margin-top: 15px; margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
}
.risk-card-high {
    background: #fff5f5; border: 1px solid #feb2b2; border-left: 6px solid #e53e3e;
    padding: 16px 20px; border-radius: 10px; margin-bottom: 12px; min-height: 190px;
}
</style>
"""
st.markdown(anim_css, unsafe_allow_html=True)

st.title("🔋 배터리 리튬 공급망 실시간 외생 병목 모니터링 & SCM 최적화")
st.markdown("##### **호주 포트헤들랜드 선석 과포화 및 기상 변동 — 중국 제련 고집중 — 한국 양극재 클러스터 연계**")
st.write("---")

# 사이드바 공장 운영 변수 입력 UI
st.sidebar.header("⚙️ 공장 운영 및 원가 시뮬레이션")
daily_demand = st.sidebar.number_input("일일 리튬 소요량 (톤/일)", 10.0, 300.0, 65.0, 5.0)
lithium_price = st.sidebar.number_input("수산화리튬 가격 ($/톤)", 5000.0, 80000.0, 15000.0, 500.0)
daily_stop_loss = st.sidebar.number_input("공장 가동 중단 일일 손실 ($/일)", 50000.0, 5000000.0, 850000.0, 50000.0)
holding_cost_rate = st.sidebar.slider("연간 재고 유지비율 (%)", 3.0, 15.0, 8.0, 0.5) / 100.0

# ---------------------------------------------------------
# 1. 해상 운송 거점별 경로 시각화 및 모션 토글 슬라이드
# ---------------------------------------------------------
st.subheader("1. 해상 운송 거점별 경로 및 최적 대안 추천")

route_data = [
    {
        "id": 0, "title": "최단 리드타임 추천", "name": "한-호 직항 장기운송계약(COA) 전용선",
        "vessel_type": "Supramax 55,000 DWT", "route_desc": "호주 포트헤들랜드 선적 -> 한국 광양 직항 입항 (지정 전용 선석)",
        "lead_time": 14, "reliability": 94.5, "freight": 42.0, "color_rgb":,
        "summary": "우기 사이클론 시즌 및 선석 체선 리스크를 최소화하여 공장 셧다운을 완벽 방어하는 최우선 안정 항로",
        "path": [[118.576, -20.3167], [127.697, 34.9754]]
    },
    {
        "id": 1, "title": "최고 정시성 추천", "name": "중국 제련 톨링 경유 정기선",
        "vessel_type": "Ultramax 62,000 DWT", "route_desc": "호주 포트헤들랜드 -> 중국 닝보 기항 (정기 셔틀)",
        "lead_time": 18, "reliability": 88.0, "freight": 33.5, "color_rgb":,
        "summary": "중국 내 가공 위탁 라인과 연계된 정기 항로이나, 통상 규제(FEOC) 시 대체 전환 조치 필요",
        "path": [[118.576, -20.3167], [121.544, 29.8683]]
    },
    {
        "id": 2, "title": "최저 운임 추천", "name": "스팟 시장 자유 용선 (동남아 환적)",
        "vessel_type": "Handymax 45,000 DWT", "route_desc": "호주 -> 싱가포르 환적 -> 한국 광양 (스팟 용선)",
        "lead_time": 24, "reliability": 76.2, "freight": 28.0, "color_rgb":,
        "summary": "톤당 운임이 가장 경제적이나 환적 대기와 비정기선 특성상 리드타임 변동성이 크게 발생",
        "path": [[118.576, -20.3167], [103.8198, 1.3521], [127.697, 34.9754]]
    }
]

toggle_options = ["전체 항로 종합 비교", "최단 리드타임 추천", "최고 정시성 추천", "최저 운임 추천"]
selected_toggle = st.segmented_control("운송 시나리오 필터링", toggle_options, default="전체 항로 종합 비교")

active_id = None
if selected_toggle != "전체 항로 종합 비교":
    active_id = next((r["id"] for r in route_data if r["title"] == selected_toggle), None)

# 상단 대시보드 스코어카드 및 정보 박스
if active_id is not None:
    curr = route_data[active_id]
    r_hex = f"#{curr['color_rgb'][0]:02x}{curr['color_rgb'][1]:02x}{curr['color_rgb'][2]:02x}"
    
    st.markdown(
        f"<div class='route-detail-box' style='border-left: 6px solid {r_hex};'>"
        f" <div style='display:flex; justify-content:space-between; align-items:center;'>"
        f" <h4 style='margin:0; color:#1e293b;'>📌 {curr['title']} : {curr['name']}</h4>"
        f" <span style='background:{r_hex}; color:white; padding:4px 12px; border-radius:15px; font-weight:bold; font-size:0.85rem;'>선택됨</span>"
        f" </div>"
        f" <p style='margin:8px 0 12px 0; color:#64748b;'>{curr['route_desc']} (투입 선형: <b>{curr['vessel_type']}</b>)</p>"
        f" <div style='color:#334155; font-size:0.95rem;'><b>SCM 전략 평가</b>: {curr['summary']}</div>"
        f"</div>", 
        unsafe_allow_html=True
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("조달 리드타임", f"{curr['lead_time']} 일")
    c2.metric("운항 정시성", f"{curr['reliability']} %")
    c3.metric("해상 운임 지표", f"${curr['freight']} / 톤")
else:
    c1, c2, c3 = st.columns(3)
    c1.metric(route_data[0]["name"], f"{route_data[0]['lead_time']} 일", f"${route_data[0]['freight']}/톤 (최단)")
    c2.metric(route_data[1]["name"], f"{route_data[1]['reliability']} %", f"{route_data[1]['lead_time']}일 소요")
    c3.metric(route_data[2]["name"], f"${route_data[2]['freight']} / 톤", f"정시성 {route_data[2]['reliability']}%")

# Pydeck 지도 데이터 빌드
routes_layer_data = []
for r in route_data:
    if active_id is None:
        color = r["color_rgb"] + [200]
        width = 5
    else:
        if r["id"] == active_id:
            color = r["color_rgb"] + [255]
            width = 8
        else:
            color = [180, 180, 180, 40]
            width = 2

    routes_layer_data.append({
        "name": r["name"],
        "path": r["path"],
        "color": color,
        "width": width,
        "tooltip": f"<b>{r['name']}</b><br>리드타임: {r['lead_time']}일 | 운임: ${r['freight']}/톤"
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
    get_width="width",
    width_min_pixels=2,
    pickable=True
)

scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=ports_data,
    get_position="coords",
    get_color=[15, 23, 42, 220],
    get_radius=150000,
    radius_min_pixels=6,
    pickable=True
)

view_state = pdk.ViewState(longitude=118.0, latitude=12.0, zoom=3.0, pitch=0)

st.pydeck_chart(
    pdk.Deck(
        layers=[path_layer, scatter_layer],
        initial_view_state=view_state,
        tooltip={"html": "{tooltip}{name}"},
        map_provider="carto",
        map_style="light"
    ),
    use_container_width=True
)

# ---------------------------------------------------------
# 2. 2대 외생 변수 실시간 자동 수집 & 종합 AI 분석
# ---------------------------------------------------------
st.write("---")
st.subheader("2. AI 외생 변수 실시간 모니터링 & 위기 감지 지표")
st.caption("시스템 백그라운드에서 핵심 공급망 리스크(호주 기상 및 국가별 규제 변수)를 실시간 동시 파싱하여 동기화합니다.")

col_risk1, col_risk2 = st.columns(2)

with col_risk1:
    st.markdown("#### 🌧️ 시나리오 1: 호주 필바라 기상/선석 체선")
    st.markdown(
        "<div class='risk-card-high'>"
        " <div style='font-weight:bold; font-size:1.05rem; color:#c53030;'>⚠️ [HIGH] 우기 사이클론 시즌 진입 경보</div>"
        " <ul style='margin-top:8px; padding-left:20px; color:#4a5568; font-size:0.9rem; line-height:1.5;'>"
        " <li><b>호주 기상청(BOM)</b>: 필바라 연안 열대성 저기압 발달로 포트헤들랜드 선석 통제 유력</li>"
        " <li><b>항만 체선 현황</b>: 주요 벌크 터미널 대기 척수 증가로 평시 대비 운송 <b>5~9일 지연</b></li>"
        " <li><b>원료 공급 영향</b>: 스포듀민 정광 입항 주기 왜곡으로 국내 양극재 라인 가동 리스크 증대</li>"
        " </ul>"
        "</div>", unsafe_allow_html=True
    )

with col_risk2:
    st.markdown("#### ⚖️ 시나리오 2: 통상 규제 (미국 IRA FEOC & 중국 제련)")
    st.markdown(
        "<div class='risk-card-high'>"
        " <div style='font-weight:bold; font-size:1.05rem; color:#c53030;'>⚠️ [HIGH] 해외우려기관(FEOC) 규제 압박 지속</div>"
        " <ul style='margin-top:8px; padding-left:20px; color:#4a5568; font-size:0.9rem; line-height:1.5;'>"
        " <li><b>미국 재무부/DOE 지침</b>: 중국 내 위탁 가공된 수산화리튬 세액공제($7,500) 배제 장기화</li>"
        " <li><b>의존도 취약성 분석</b>: 국내 배테랑 밸류체인의 중국 제련 톨링 의존도가 <b>79%</b>로 대체재 시급</li>"
        " <li><b>가동 시차 리스크</b>: 규제 대응 목적의 FTA 권역 제련 라인 튜닝 시 <b>최소 120일</b> 소요 예측</li>"
        " </ul>"
        "</div>", unsafe_allow_html=True
    )

# ---------------------------------------------------------
# 3. 2대 시나리오 연계 정량 솔루션 & ROI 시뮬레이션
# ---------------------------------------------------------
st.write("---")
st.subheader("3. 병목 솔루션 수치 산정 및 정량적 ROI 시뮬레이션")
st.caption("입력된 공장 변수와 SCM 통계 지표(기상 변동계수 CV 0.310, 대체 시차 120일)를 융합하여 비용 편익을 실시간 계산합니다.")

col_sol1, col_sol2 = st.columns(2)

with col_sol1:
    st.markdown("#### 📊 Sol 1: 동적 안전재고(Dynamic Safety Stock) 선제 비축")
    st.markdown(
        "- **산출 근거**: 평시 변동계수(CV) 0.086 → 우기 사이클론 시즌 CV 0.310 (변동폭 **3.6배** 증가)\n"
        "- **대응 전략**: 우기 진입 전 안전재고 일수를 기존 14일에서 **35일분으로 선제 상향** (+21일 추가)"
    )
    
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
    
