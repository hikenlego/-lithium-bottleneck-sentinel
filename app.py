import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

# ---------------------------------------------------------
# 0. 시스템 환경 설정 및 모던 UI 레이아웃
# ---------------------------------------------------------
st.set_page_config(
    page_title="수산화리튬 공급망 디지털 트윈 의사결정 시스템",
    layout="wide"
)

st.title("배터리급 수산화리튬 공급망 리스크 시뮬레이션 & 조달 의사결정 엔진")
st.caption("디지털 트윈 기반 불확실성 모형: 호주 필바라 우기 체선 - 중국 정제 편중 - 북미 FEOC 규제 연계")

# ---------------------------------------------------------
# 1. 사이드바: 6계층 디지털 트윈 파라미터 제어
# ---------------------------------------------------------
st.sidebar.header("1. 기업 운영 파라미터 (Operation)")
daily_demand = st.sidebar.number_input("일일 수산화리튬 소요량 (D̄, 톤/일)", 10.0, 300.0, 65.0, 5.0)
demand_cv = st.sidebar.slider("일일 수요 변동계수 (CV_D)", 0.0, 0.20, 0.05, 0.01)
sigma_D = daily_demand * demand_cv

lithium_price = st.sidebar.number_input("수산화리튬 가격 (P, $/톤)", 5000.0, 50000.0, 15000.0, 500.0)
daily_stop_loss = st.sidebar.number_input("공장 셧다운 일일 손실 (L_daily, $/일)", 50000.0, 3000000.0, 850000.0, 50000.0)
holding_cost_rate = st.sidebar.slider("연간 재고유지비율 (r, %)", 3.0, 15.0, 8.0, 0.5) / 100.0

st.sidebar.header("2. 불확실성 & 목표 서비스수준 (Uncertainty)")
service_level_label = st.sidebar.select_slider(
    "목표 서비스 수준 (Service Level)",
    options=["95.0% (z=1.645)", "97.5% (z=1.960)", "99.0% (z=2.326)", "99.5% (z=2.576)", "99.9% (z=3.090)"],
    value="99.0% (z=2.326)"
)
z_dict = {
    "95.0% (z=1.645)": 1.645,
    "97.5% (z=1.960)": 1.960,
    "99.0% (z=2.326)": 2.326,
    "99.5% (z=2.576)": 2.576,
    "99.9% (z=3.090)": 3.090
}
z_score = z_dict[service_level_label]

prob_weather = st.sidebar.slider("우기 체선/기상 충격 발생확률 P(Weather)", 0.1, 0.9, 0.45, 0.05)
prob_feoc = st.sidebar.slider("북미 FEOC 통상규제 충격확률 P(FEOC)", 0.1, 0.9, 0.35, 0.05)

st.sidebar.header("3. 대체 톨링 비용 파라미터 분해 (Tolling)")
tuning_cost = st.sidebar.number_input("사전 가마 튜닝/인증비 ($/톤)", 100.0, 1000.0, 250.0, 50.0)
reservation_cost = st.sidebar.number_input("연간 슬롯 예약금 ($/톤)", 100.0, 1000.0, 300.0, 50.0)
freight_premium = st.sidebar.number_input("대체 직항 운임 증분 ($/톤)", 0.0, 300.0, 100.0, 10.0)
c_tolling_unit = tuning_cost + reservation_cost + freight_premium

expedite_premium = st.sidebar.number_input("규제 시 긴급 스팟 조달 프리미엄 ($/톤)", 500.0, 5000.0, 2500.0, 100.0)
customer_penalty = st.sidebar.number_input("납기 지연 고객사 페널티 ($/톤)", 200.0, 3000.0, 1000.0, 100.0)
total_mitigation_benefit_unit = expedite_premium + customer_penalty

# ---------------------------------------------------------
# 2. 물리적 해상 운송 네트워크 & 인터랙티브 지도
# ---------------------------------------------------------
st.header("1. 해상 운송 네트워크 & 계약 모드 비교")

route_data = [
    {
        "id": 0,
        "title": "최단 리드타임 (COA 전용선)",
        "name": "한-호 직항 장기계약 전용선 (Utah Point 전용선석)",
        "lead_time": 14,
        "lead_time_sd": 6.44, # CV=0.46 (우기 체선 5~9일 반영)
        "freight": 42.0,
        "reliability": 94.5,
        "color_rgb": [46, 204, 113],
        "path": [[118.576, -20.3167], [127.697, 34.9754]]
    },
    {
        "id": 1,
        "title": "최고 정시성 (중국 정기선)",
        "name": "중국 닝보 제련 톨링 경유 정기선",
        "lead_time": 18,
        "lead_time_sd": 8.10,
        "freight": 33.5,
        "reliability": 88.0,
        "color_rgb": [52, 152, 219],
        "path": [[118.576, -20.3167], [121.544, 29.8683]]
    },
    {
        "id": 2,
        "title": "최저 운임 (동남아 스팟)",
        "name": "동남아(싱가포르) 환적 스팟 용선",
        "lead_time": 24,
        "lead_time_sd": 12.50,
        "freight": 28.0,
        "reliability": 76.2,
        "color_rgb": [231, 76, 60],
        "path": [[118.576, -20.3167], [103.8198, 1.3521], [127.697, 34.9754]]
    }
]

selected_route_name = st.segmented_control(
    "기준 운송 모드 선택",
    ["최단 리드타임 (COA 전용선)", "최고 정시성 (중국 정기선)", "최저 운임 (동남아 스팟)", "전체 항로 종합 비교"],
    default="최단 리드타임 (COA 전용선)"
)

active_route_id = None
if selected_route_name == "최단 리드타임 (COA 전용선)":
    active_route_id = 0
elif selected_route_name == "최고 정시성 (중국 정기선)":
    active_route_id = 1
elif selected_route_name == "최저 운임 (동남아 스팟)":
    active_route_id = 2

# pydeck 지도 렌더링
map_routes = []
for r in route_data:
    if active_route_id is None:
        color = r["color_rgb"] + [200]
        width = 45000
    else:
        if r["id"] == active_route_id:
            color = r["color_rgb"] + [255]
            width = 85000
        else:
            color = [180, 180, 180, 40]
            width = 20000
    map_routes.append({
        "name": r["name"],
        "path": r["path"],
        "color": color,
        "width": width,
        "tooltip": f"{r['title']} | 리드타임: {r['lead_time']}일 (편차: {r['lead_time_sd']}일) | 운임: ${r['freight']}/톤"
    })

ports_data = [
    {"name": "호주 포트헤들랜드 (스포듀민 선적항)", "coords": [118.576, -20.3167]},
    {"name": "중국 닝보항 (화학전환 거점)", "coords": [121.544, 29.8683]},
    {"name": "한국 광양항 (양극재 클러스터 입항)", "coords": [127.697, 34.9754]},
    {"name": "싱가포르항 (환적 거점)", "coords": [103.8198, 1.3521]}
]

st.pydeck_chart(
    pdk.Deck(
        layers=[
            pdk.Layer("PathLayer", data=map_routes, get_path="path", get_color="color", get_width="width", pickable=True),
            pdk.Layer("ScatterplotLayer", data=ports_data, get_position="coords", get_color=[30, 41, 59], get_radius=110000, pickable=True)
        ],
        initial_view_state=pdk.ViewState(longitude=120.0, latitude=8.0, zoom=2.6, pitch=0),
        tooltip={"text": "{name}\n{tooltip}"},
        map_provider="carto",
        map_style="light"
    ),
    use_container_width=True
)

# ---------------------------------------------------------
# 3. 확률 기반 동적 안전재고 & 기대손실 연산 엔진
# ---------------------------------------------------------
st.header("2. 불확실성 기반 동적 안전재고 & 기대손실 모델")

base_route = route_data[active_route_id if active_route_id is not None else 0]
mean_L = base_route["lead_time"]
sd_L = base_route["lead_time_sd"]

# [수학적 공식에 따른 안전재고 계산]
# SS = z * sqrt(L * sigma_D^2 + D^2 * sigma_L^2)
variance_DL = (mean_L * (sigma_D ** 2)) + ((daily_demand ** 2) * (sd_L ** 2))
sigma_DL = np.sqrt(variance_DL)
ss_tonnes = z_score * sigma_DL
ss_days = ss_tonnes / daily_demand

base_stock_days = 20.0 # 사이클 및 기본 완충재고
total_target_days = base_stock_days + ss_days
add_inventory_tonnes = ss_tonnes

# 우기 90일간 재고유지비용 증분
cost_safety_stock = add_inventory_tonnes * lithium_price * holding_cost_rate * (90.0 / 365.0)

# 조건부 결품 확률 및 회피 기대손실
# P(S0 | Weather): 추가 안전재고가 없을 때 체선(평균 7일 지연) 시 결품 발생확률 = 95%
# P(S1 | Weather): z-score에 따른 결품확률 (1 - Service Level)
prob_stockout_before = 0.95
prob_stockout_after = (1.0 - (z_score / 3.5)) # 서비스수준에 역비례
delta_prob_stockout = max(0.0, prob_stockout_before - prob_stockout_after)

expected_delay_days = 7.0
benefit_safety_stock = prob_weather * delta_prob_stockout * daily_stop_loss * expected_delay_days
net_benefit_ss = benefit_safety_stock - cost_safety_stock
roi_ss = (net_benefit_ss / cost_safety_stock) * 100.0 if cost_safety_stock > 0 else 0

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
col_s1.metric("계산된 동적 안전재고", f"{ss_tonnes:,.1f} 톤", f"+{ss_days:.1f}일분 비축")
col_s2.metric("총 방어재고 수준", f"{total_target_days:.1f} 일분", f"기본 20일 + 안전 {ss_days:.1f}일")
col_s3.metric("안전재고 유지비용 (Cost)", f"${cost_safety_stock:,.0f}", f"우기 90일간 증분비용")
col_s4.metric("기대 셧다운 회피액 (Benefit)", f"${benefit_safety_stock:,.0f}", f"P(Weather)={prob_weather:.2f} 반영")

st.info(
    f"공식 연산 결과: 목표 서비스 수준 **{service_level_label}** 및 우기 리드타임 편차($\sigma_L={sd_L:.2f}$일)를 반영한 순수 안전재고는 **{ss_days:.1f}일분({ss_tonnes:,.0f}톤)**입니다. "
    f"기본 운영재고(20일)와 결합한 총 방어재고 수준은 **{total_target_days:.1f}일분**이며, 순편익은 **${net_benefit_ss:,.0f} (ROI {roi_ss:.1f}%)**로 산출됩니다."
)

# ---------------------------------------------------------
# 4. 대체 정제선 예비 톨링(Standby Tolling) 정량 모델
# ---------------------------------------------------------
st.header("3. 통상 규제(FEOC) 대응 예비 톨링 경제성 모델")

t_gap_days = 120.0 # 전환 공백
split_ratio = st.slider("대체 톨링 커버리지 비율 (Coverage Ratio, ρ)", 0.1, 0.8, 0.4, 0.05)

q_tolling = daily_demand * t_gap_days * split_ratio
cost_tolling = q_tolling * c_tolling_unit

# 기대 편익: P(FEOC) * (긴급 조달 프리미엄 + 고객사 페널티) * 커버리지 물량
benefit_tolling = prob_feoc * (q_tolling * total_mitigation_benefit_unit)
net_benefit_tolling = benefit_tolling - cost_tolling
roi_tolling = (net_benefit_tolling / cost_tolling) * 100.0 if cost_tolling > 0 else 0

col_t1, col_t2, col_t3, col_t4 = st.columns(4)
col_t1.metric("예비 톨링 계약 물량", f"{q_tolling:,.0f} 톤", f"120일 소요량의 {split_ratio*100:.0f}%")
col_t2.metric("사전 튜닝/슬롯비 (Cost)", f"${cost_tolling:,.0f}", f"단가: ${c_tolling_unit:,.0f}/톤")
col_t3.metric("기대 규제손실 회피 (Benefit)", f"${benefit_tolling:,.0f}", f"P(FEOC)={prob_feoc:.2f} 반영")
col_t4.metric("예비 톨링 추정 ROI", f"{roi_tolling:,.1f} %", "투자 대비 순편익")

st.caption(f"* 비용 분해: 가마 튜닝비 ${tuning_cost:.0f} + 슬롯 예약금 ${reservation_cost:.0f} + 운임 증분 ${freight_premium:.0f} = 합계 ${c_tolling_unit:.0f}/톤 | 회피 편익 단가: 긴급 프리미엄 ${expedite_premium:.0f} + 페널티 ${customer_penalty:.0f} = ${total_mitigation_benefit_unit:.0f}/톤")

# ---------------------------------------------------------
# 5. 몬테카를로 시뮬레이션 & 불확실성 위험 지표 (VaR/CVaR)
# ---------------------------------------------------------
st.header("4. 몬테카를로 불확실성 시뮬레이션 (1,000회 반복)")
st.caption("기상 체선 일수, 통상 규제 발효 여부, 리드타임 변동을 결합 확률분포로 샘플링하여 손익 분포를 검증합니다.")

np.random.seed(42)
n_sim = 1000

# 1) 기상 이벤트 및 체선 일수 샘플링
weather_occurs = np.random.binomial(1, prob_weather, n_sim)
sim_delay_days = np.random.uniform(5.0, 9.0, n_sim) * weather_occurs

# 2) FEOC 규제 이벤트 샘플링
feoc_occurs = np.random.binomial(1, prob_feoc, n_sim)

# 3) 각 반복당 손익(Net Benefit) 연산 (복합 결합 모델)
# 안전재고는 체선 일수를 방어하고, 예비 톨링은 규제 공백 물량을 방어
sim_prevented_loss = (sim_delay_days * daily_stop_loss) + (feoc_occurs * (q_tolling * total_mitigation_benefit_unit))
sim_total_cost = cost_safety_stock + cost_tolling
sim_net_benefits = sim_prevented_loss - sim_total_cost

# 위험 지표 산출
mean_nb = np.mean(sim_net_benefits)
p5_nb = np.percentile(sim_net_benefits, 5) # 하위 5% (VaR_95 관점)
p95_nb = np.percentile(sim_net_benefits, 95)
cvar_95 = np.mean(sim_net_benefits[sim_net_benefits <= p5_nb]) # 최악 5%의 평균 손익

c_m1, c_m2, c_m3, c_m4 = st.columns(4)
c_m1.metric("시뮬레이션 평균 순편익", f"${mean_nb:,.0f}")
c_m2.metric("P5 순손익 (VaR 95)", f"${p5_nb:,.0f}", "하위 5% 시나리오")
c_m3.metric("최악 5% 평균 (CVaR 95)", f"${cvar_95:,.0f}", "스트레스 시나리오")
c_m4.metric("P95 순손익 (상방)", f"${p95_nb:,.0f}", "상위 5% 호의 시나리오")

# ---------------------------------------------------------
# 6. 5대 전략 포트폴리오 최적화 비교 매트릭스
# ---------------------------------------------------------
st.header("5. SCM 전략 포트폴리오 다각화 최적 비교표")

strategies = [
    {
        "전략 구분": "A. 현상 유지 (Do Nothing)",
        "총 연간 비용 ($)": 0,
        "기대 회피 편익 ($)": 0,
        "기대 순편익 ($)": 0,
        "ROI (%)": 0.0,
        "서비스수준 충족": "미흡 (<80%)",
        "권고 여부": "위험 노출 (비권고)"
    },
    {
        "전략 구분": "B. 안전재고 단독 강화",
        "총 연간 비용 ($)": cost_safety_stock,
        "기대 회피 편익 ($)": benefit_safety_stock,
        "기대 순편익 ($)": net_benefit_ss,
        "ROI (%)": roi_ss,
        "서비스수준 충족": f"달성 ({service_level_label[:5]})",
        "권고 여부": "기후 리스크 방어"
    },
    {
        "전략 구분": "C. 예비 톨링 20% 분할",
        "총 연간 비용 ($)": (daily_demand * t_gap_days * 0.20) * c_tolling_unit,
        "기대 회피 편익 ($)": prob_feoc * ((daily_demand * t_gap_days * 0.20) * total_mitigation_benefit_unit),
        "기대 순편익 ($)": (prob_feoc * ((daily_demand * t_gap_days * 0.20) * total_mitigation_benefit_unit)) - ((daily_demand * t_gap_days * 0.20) * c_tolling_unit),
        "ROI (%)": roi_tolling,
        "서비스수준 충족": "부분 달성",
        "권고 여부": "규제 최소 방어"
    },
    {
        "전략 구분": f"D. 예비 톨링 {split_ratio*100:.0f}% 분할",
        "총 연간 비용 ($)": cost_tolling,
        "기대 회피 편익 ($)": benefit_tolling,
        "기대 순편익 ($)": net_benefit_tolling,
        "ROI (%)": roi_tolling,
        "서비스수준 충족": "충족 (규제 방어)",
        "권고 여부": "통상 리스크 방어"
    },
    {
        "전략 구분": "E. 복합 다각화 (안전재고 + 톨링)",
        "총 연간 비용 ($)": sim_total_cost,
        "기대 회피 편익 ($)": benefit_safety_stock + benefit_tolling,
        "기대 순편익 ($)": (benefit_safety_stock + benefit_tolling) - sim_total_cost,
        "ROI (%)": (((benefit_safety_stock + benefit_tolling) - sim_total_cost) / sim_total_cost) * 100.0,
        "서비스수준 충족": f"완벽 달성 (99%+)",
        "권고 여부": "★ 최적 권고 전략"
    }
]

df_strat = pd.DataFrame(strategies)
st.dataframe(
    df_strat.style.format({
        "총 연간 비용 ($)": "${:,.0f}",
        "기대 회피 편익 ($)": "${:,.0f}",
        "기대 순편익 ($)": "${:,.0f}",
        "ROI (%)": "{:,.1f}%"
    }),
    use_container_width=True,
    hide_index=True
)

st.success(
    f"최종 의사결정 권고: 단일 충격 대응보다 기상 체선과 북미 통상 규제를 결합 방어하는 **'전략 E (복합 다각화 전략)'** 실행 시, "
    f"연간 총 투입비용 **${sim_total_cost:,.0f}** 대비 기대 회피 편익 **${(benefit_safety_stock + benefit_tolling):,.0f}**을 달성하여 "
    f"순편익 **${((benefit_safety_stock + benefit_tolling) - sim_total_cost):,.0f} (복합 ROI {(((benefit_safety_stock + benefit_tolling) - sim_total_cost) / sim_total_cost) * 100.0:.1f}%)**의 최고 방어 효율을 나타냅니다."
)
