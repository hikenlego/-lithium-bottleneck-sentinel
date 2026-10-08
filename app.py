# ---------------------------------------------------------
# 배터리급 수산화리튬 공급망 리스크 시뮬레이션 &
# 조달 의사결정 지원 시스템
#
# 핵심 질문:
# 1. 공급이 늦어지면 공장이 멈출 위험이 얼마나 되는가?
# 2. 안전재고를 늘리는 비용보다, 공장 셧다운을 막는 편익이 큰가?
# 3. 중국 정제선이 막히면 대체 정제소를 얼마나 예약해야 하는가?
# ---------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

# ---------------------------------------------------------
# 0. 기본 설정
# ---------------------------------------------------------

st.set_page_config(
    page_title="수산화리튬 공급망 의사결정 시스템",
    layout="wide"
)

st.title("배터리급 수산화리튬 공급망 리스크 시뮬레이션 & 조달 의사결정 엔진")

st.caption(
    "입력된 기업 운영 조건과 기상·통상 리스크를 바탕으로, "
    "안전재고 및 예비 톨링 전략의 비용·편익·위험을 비교합니다."
)

# ---------------------------------------------------------
# 1. 사이드바: 사용자 입력값
# ---------------------------------------------------------

st.sidebar.header("1. 기업 운영 조건")

daily_demand = st.sidebar.number_input(
    "일일 수산화리튬 소요량 (톤/일)",
    min_value=10.0,
    max_value=300.0,
    value=65.0,
    step=5.0
)

demand_cv = st.sidebar.slider(
    "일일 수요 변동계수 (CV)",
    min_value=0.0,
    max_value=0.20,
    value=0.05,
    step=0.01
)

sigma_demand = daily_demand * demand_cv

lithium_price = st.sidebar.number_input(
    "수산화리튬 가격 ($/톤)",
    min_value=5000.0,
    max_value=50000.0,
    value=15000.0,
    step=500.0
)

daily_shutdown_loss = st.sidebar.number_input(
    "공장 셧다운 1일 기회손실 ($/일)",
    min_value=50000.0,
    max_value=3000000.0,
    value=850000.0,
    step=50000.0
)

holding_cost_rate = st.sidebar.slider(
    "연간 재고유지비율 (%)",
    min_value=3.0,
    max_value=15.0,
    value=8.0,
    step=0.5
) / 100.0

st.sidebar.header("2. 리스크 시나리오")

service_level = st.sidebar.select_slider(
    "목표 서비스수준",
    options=[
        "95.0%",
        "97.5%",
        "99.0%",
        "99.5%",
        "99.9%"
    ],
    value="99.0%"
)

z_score_dict = {
    "95.0%": 1.645,
    "97.5%": 1.960,
    "99.0%": 2.326,
    "99.5%": 2.576,
    "99.9%": 3.090
}

z_score = z_score_dict[service_level]

weather_probability = st.sidebar.slider(
    "우기 체선·기상 충격 발생확률",
    min_value=0.05,
    max_value=0.90,
    value=0.45,
    step=0.05
)

feoc_probability = st.sidebar.slider(
    "북미 FEOC·통상규제 충격 발생확률",
    min_value=0.05,
    max_value=0.90,
    value=0.35,
    step=0.05
)

st.sidebar.header("3. 예비 톨링 비용")

tuning_cost_per_ton = st.sidebar.number_input(
    "사전 가마 튜닝·인증비 ($/톤)",
    min_value=100.0,
    max_value=1000.0,
    value=250.0,
    step=50.0
)

reservation_cost_per_ton = st.sidebar.number_input(
    "연간 정제 슬롯 예약비 ($/톤)",
    min_value=100.0,
    max_value=1000.0,
    value=300.0,
    step=50.0
)

freight_premium_per_ton = st.sidebar.number_input(
    "대체 직항 운임 증분 ($/톤)",
    min_value=0.0,
    max_value=300.0,
    value=100.0,
    step=10.0
)

tolling_unit_cost = (
    tuning_cost_per_ton
    + reservation_cost_per_ton
    + freight_premium_per_ton
)

expedite_premium_per_ton = st.sidebar.number_input(
    "규제 발생 시 긴급 조달 프리미엄 ($/톤)",
    min_value=500.0,
    max_value=5000.0,
    value=2500.0,
    step=100.0
)

customer_penalty_per_ton = st.sidebar.number_input(
    "납기 지연·고객사 페널티 ($/톤)",
    min_value=0.0,
    max_value=3000.0,
    value=1000.0,
    step=100.0
)

mitigation_benefit_per_ton = (
    expedite_premium_per_ton
    + customer_penalty_per_ton
)

# ---------------------------------------------------------
# 1. 해상 운송 경로 선택 및 지도
# ---------------------------------------------------------

st.header("1. 해상 운송 네트워크 및 운송계약 비교")

route_data = [
    {
        "id": 0,
        "title": "최단 리드타임 (COA 전용선)",
        "name": "한-호 직항 장기운송계약(COA) 전용선",
        "lead_time": 14.0,
        "lead_time_sd": 6.44,
        "freight": 42.0,
        "reliability": 94.5,
        "color": [46, 204, 113],
        "path": [
            [118.576, -20.3167],
            [127.697, 34.9754]
        ]
    },
    {
        "id": 1,
        "title": "최고 정시성 (중국 정기선)",
        "name": "중국 닝보 화학전환 경유 정기선",
        "lead_time": 18.0,
        "lead_time_sd": 8.10,
        "freight": 33.5,
        "reliability": 88.0,
        "color": [52, 152, 219],
        "path": [
            [118.576, -20.3167],
            [121.544, 29.8683]
        ]
    },
    {
        "id": 2,
        "title": "최저 운임 (동남아 환적)",
        "name": "싱가포르 환적 스팟 용선",
        "lead_time": 24.0,
        "lead_time_sd": 12.50,
        "freight": 28.0,
        "reliability": 76.2,
        "color": [231, 76, 60],
        "path": [
            [118.576, -20.3167],
            [103.8198, 1.3521],
            [127.697, 34.9754]
        ]
    }
]

selected_route = st.segmented_control(
    "기준 운송 모드",
    [
        "최단 리드타임 (COA 전용선)",
        "최고 정시성 (중국 정기선)",
        "최저 운임 (동남아 환적)",
        "전체 항로 비교"
    ],
    default="최단 리드타임 (COA 전용선)"
)

if selected_route == "최단 리드타임 (COA 전용선)":
    active_route_id = 0
elif selected_route == "최고 정시성 (중국 정기선)":
    active_route_id = 1
elif selected_route == "최저 운임 (동남아 환적)":
    active_route_id = 2
else:
    active_route_id = None

base_route = route_data[active_route_id if active_route_id is not None else 0]

mean_lead_time = base_route["lead_time"]
lead_time_sd = base_route["lead_time_sd"]

map_routes = []

for route in route_data:

    if active_route_id is None:
        route_color = route["color"] + [200]
        route_width = 45000

    elif route["id"] == active_route_id:
        route_color = route["color"] + [255]
        route_width = 85000

    else:
        route_color = [180, 180, 180, 40]
        route_width = 20000

    map_routes.append(
        {
            "name": route["name"],
            "path": route["path"],
            "color": route_color,
            "width": route_width,
            "tooltip": (
                f"{route['title']} | "
                f"평균 리드타임: {route['lead_time']:.0f}일 | "
                f"리드타임 표준편차: {route['lead_time_sd']:.2f}일 | "
                f"운임: ${route['freight']:.1f}/톤"
            )
        }
    )

port_data = [
    {
        "name": "호주 포트헤들랜드 (스포듀민 선적항)",
        "coords": [118.576, -20.3167]
    },
    {
        "name": "중국 닝보항 (화학전환 거점)",
        "coords": [121.544, 29.8683]
    },
    {
        "name": "한국 광양항 (양극재 클러스터)",
        "coords": [127.697, 34.9754]
    },
    {
        "name": "싱가포르항 (환적 거점)",
        "coords": [103.8198, 1.3521]
    }
]

st.pydeck_chart(
    pdk.Deck(
        layers=[
            pdk.Layer(
                "PathLayer",
                data=map_routes,
                get_path="path",
                get_color="color",
                get_width="width",
                pickable=True
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=port_data,
                get_position="coords",
                get_color=[30, 41, 59],
                get_radius=110000,
                pickable=True
            )
        ],
        initial_view_state=pdk.ViewState(
            longitude=120.0,
            latitude=8.0,
            zoom=2.6,
            pitch=0
        ),
        tooltip={
            "text": "{name}\n{tooltip}"
        },
        map_provider="carto",
        map_style="light"
    ),
    use_container_width=True
)

# ---------------------------------------------------------
# 2. 핵심 파라미터
# ---------------------------------------------------------

# 기본 운영재고: 정상적인 주문-입고 주기를 감당하는 재고
base_stock_days = 20.0

# 우기 체선 지연: 5~9일 발생 가능
weather_delay_min = 5.0
weather_delay_max = 9.0

# 중국 정제선 차단 시 대체 정제 전환 공백
regulation_gap_days = 120.0

# 예비 톨링 커버리지 비율
tolling_coverage = st.slider(
    "예비 톨링 커버리지 비율",
    min_value=0.10,
    max_value=0.80,
    value=0.40,
    step=0.05
)

# ---------------------------------------------------------
# 2. 안전재고 계산
# ---------------------------------------------------------

st.header("2. 불확실성 기반 동적 안전재고")

st.info(
    f"""
    **안전재고의 목적**  
    평균보다 긴 납기 지연, 수요 급증, 품질 불량 등이 발생했을 때  
    공장이 멈추지 않도록 추가로 보유하는 재고입니다.

    **계산식**  
    \\[
    SS = z \\times \\sqrt{{\\bar{{L}}\\sigma_D^2 + \\bar{{D}}^2\\sigma_L^2}}
    \\]
    """
)

safety_stock_variance = (
    mean_lead_time * sigma_demand ** 2
    + daily_demand ** 2 * lead_time_sd ** 2
)

safety_stock_tonnes = (
    z_score * np.sqrt(safety_stock_variance)
)

safety_stock_days = (
    safety_stock_tonnes / daily_demand
)

total_defense_days = (
    base_stock_days + safety_stock_days
)

safety_stock_cost = (
    safety_stock_tonnes
    * lithium_price
    * holding_cost_rate
    * (90.0 / 365.0)
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "계산된 안전재고",
    f"{safety_stock_tonnes:,.0f} 톤",
    f"{safety_stock_days:.1f}일분"
)

col2.metric(
    "총 방어재고 수준",
    f"{total_defense_days:.1f}일분",
    f"기본 {base_stock_days:.0f}일 + 안전 {safety_stock_days:.1f}일"
)

col3.metric(
    "안전재고 유지비용",
    f"${safety_stock_cost:,.0f}",
    "우기 90일 기준"
)

col4.metric(
    "선택 운송경로",
    base_route["title"],
    f"평균 {mean_lead_time:.0f}일 / 편차 {lead_time_sd:.2f}일"
)

# ---------------------------------------------------------
# 3. 몬테카를로 시뮬레이션
# ---------------------------------------------------------

st.header("3. 몬테카를로 리스크 시뮬레이션")

st.caption(
    "우기 체선 발생 여부, 체선 지연일수, FEOC 규제 발생 여부를 "
    "확률적으로 샘플링하여 전략별 순편익 분포를 산출합니다."
)

n_simulation = 1000

rng = np.random.default_rng(42)

weather_occurs = rng.binomial(
    1,
    weather_probability,
    n_simulation
)

weather_delay = (
    rng.uniform(
        weather_delay_min,
        weather_delay_max,
        n_simulation
    )
    * weather_occurs
)

feoc_occurs = rng.binomial(
    1,
    feoc_probability,
    n_simulation
)

# ---------------------------------------------------------
# 2-1. 안전재고 효과
# ---------------------------------------------------------

# 기존 정책: 기본 운영재고만 보유
loss_before_weather = (
    np.maximum(
        0,
        weather_delay - base_stock_days
    )
    * daily_shutdown_loss
)

# 개선 정책: 기본 운영재고 + 안전재고
loss_after_weather = (
    np.maximum(
        0,
        weather_delay - total_defense_days
    )
    * daily_shutdown_loss
)

# 안전재고가 회피하는 기대손실
safety_stock_benefit_simulation = (
    loss_before_weather - loss_after_weather
)

expected_safety_stock_benefit = (
    safety_stock_benefit_simulation.mean()
)

safety_stock_net_benefit = (
    expected_safety_stock_benefit - safety_stock_cost
)

safety_stock_roi = (
    safety_stock_net_benefit / safety_stock_cost * 100
    if safety_stock_cost > 0
    else 0.0
)

# ---------------------------------------------------------
# 2-2. 예비 톨링 효과
# ---------------------------------------------------------

# 규제 발생 시 총 조달 공백 물량
total_gap_demand = (
    daily_demand * regulation_gap_days
)

# 예비 톨링으로 방어하는 물량
tolling_covered_demand = (
    total_gap_demand * tolling_coverage
)

# 예비 톨링으로 방어하지 못하는 물량
tolling_uncovered_demand = (
    total_gap_demand * (1 - tolling_coverage)
)

# 예비 톨링 비용
tolling_cost = (
    tolling_covered_demand * tolling_unit_cost
)

# 규제가 발생했을 때 예비 톨링이 없는 경우의 손실
loss_without_tolling = (
    feoc_occurs
    * total_gap_demand
    * mitigation_benefit_per_ton
)

# 규제가 발생했을 때 예비 톨링이 있는 경우의 손실
loss_with_tolling = (
    feoc_occurs
    * tolling_uncovered_demand
    * mitigation_benefit_per_ton
)

# 예비 톨링이 회피하는 기대손실
tolling_benefit_simulation = (
    loss_without_tolling - loss_with_tolling
)

expected_tolling_benefit = (
    tolling_benefit_simulation.mean()
)

tolling_net_benefit = (
    expected_tolling_benefit - tolling_cost
)

tolling_roi = (
    tolling_net_benefit / tolling_cost * 100
    if tolling_cost > 0
    else 0.0
)

# ---------------------------------------------------------
# 2-3. 복합 전략 효과
# ---------------------------------------------------------

combined_benefit_simulation = (
    safety_stock_benefit_simulation
    + tolling_benefit_simulation
)

combined_cost = (
    safety_stock_cost + tolling_cost
)

combined_net_benefit_simulation = (
    combined_benefit_simulation - combined_cost
)

combined_expected_net_benefit = (
    combined_net_benefit_simulation.mean()
)

combined_roi = (
    combined_expected_net_benefit / combined_cost * 100
    if combined_cost > 0
    else 0.0
)

# ---------------------------------------------------------
# 안전재고 결과
# ---------------------------------------------------------

st.subheader("안전재고 전략의 경제성")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "기대 셧다운 회피액",
    f"${expected_safety_stock_benefit:,.0f}",
    "몬테카를로 1,000회 평균"
)

col2.metric(
    "안전재고 유지비용",
    f"${safety_stock_cost:,.0f}",
    "우기 90일 기준"
)

col3.metric(
    "안전재고 순편익",
    f"${safety_stock_net_benefit:,.0f}",
    "회피편익 - 유지비용"
)

col4.metric(
    "안전재고 ROI",
    f"{safety_stock_roi:,.1f}%",
    "유지비용 대비 순편익"
)

st.info(
    f"""
    현재 설정에서는 목표 서비스수준 **{service_level}**,  
    우기 체선 지연 **{weather_delay_min:.0f}~{weather_delay_max:.0f}일**,  
    선택 운송경로의 평균 리드타임 **{mean_lead_time:.0f}일**을 반영하여  
    안전재고 **{safety_stock_days:.1f}일분({safety_stock_tonnes:,.0f}톤)**을 산출했습니다.

    기본 운영재고 **{base_stock_days:.0f}일분**과 결합하면  
    총 방어재고 수준은 **{total_defense_days:.1f}일분**입니다.
    """
)

# ---------------------------------------------------------
# 예비 톨링 결과
# ---------------------------------------------------------

st.subheader("예비 톨링 전략의 경제성")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "예비 톨링 계약 물량",
    f"{tolling_covered_demand:,.0f} 톤",
    f"120일 소요량의 {tolling_coverage * 100:.0f}%"
)

col2.metric(
    "예비 톨링 비용",
    f"${tolling_cost:,.0f}",
    f"단가 ${tolling_unit_cost:,.0f}/톤"
)

col3.metric(
    "기대 규제손실 회피액",
    f"${expected_tolling_benefit:,.0f}",
    f"FEOC 확률 {feoc_probability * 100:.0f}% 반영"
)

col4.metric(
    "예비 톨링 ROI",
    f"{tolling_roi:,.1f}%",
    "투입비용 대비 순편익"
)

st.caption(
    f"""
    비용 구성: 가마 튜닝·인증비 ${tuning_cost_per_ton:,.0f}/톤  
    + 정제 슬롯 예약비 ${reservation_cost_per_ton:,.0f}/톤  
    + 대체 직항 운임 증분 ${freight_premium_per_ton:,.0f}/톤  
    = 총 ${tolling_unit_cost:,.0f}/톤

    회피 편익 단가: 긴급 조달 프리미엄 ${expedite_premium_per_ton:,.0f}/톤  
    + 납기 지연·고객사 페널티 ${customer_penalty_per_ton:,.0f}/톤  
    = 총 ${mitigation_benefit_per_ton:,.0f}/톤
    """
)

# ---------------------------------------------------------
# 몬테카를로 위험 지표
# ---------------------------------------------------------

st.subheader("복합 전략의 불확실성 분석")

var_95 = np.percentile(
    combined_net_benefit_simulation,
    5
)

cvar_95 = (
    combined_net_benefit_simulation[
        combined_net_benefit_simulation <= var_95
    ].mean()
)

p95 = np.percentile(
    combined_net_benefit_simulation,
    95
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "평균 순편익",
    f"${combined_expected_net_benefit:,.0f}",
    "1,000회 시뮬레이션 평균"
)

col2.metric(
    "P5 순편익",
    f"${var_95:,.0f}",
    "하위 5% 악화 시나리오"
)

col3.metric(
    "CVaR 95",
    f"${cvar_95:,.0f}",
    "최악 5% 시나리오 평균"
)

col4.metric(
    "P95 순편익",
    f"${p95:,.0f}",
    "상위 5% 호의적 시나리오"
)

st.caption(
    "P5는 하위 5% 악화 시나리오에서의 순편익이며,  
    CVaR 95는 최악 5% 시나리오의 평균 순편익입니다."
)

# ---------------------------------------------------------
# 전략 포트폴리오 비교
# ---------------------------------------------------------

st.header("4. SCM 전략 포트폴리오 비교")

strategy_data = []

# A. 현상 유지
strategy_data.append(
    {
        "전략": "A. 현상 유지",
        "총비용": 0.0,
        "기대 회피편익": 0.0,
        "기대 순편익": (
            -(loss_before_weather + loss_without_tolling).mean()
        ),
        "비고": "기상·규제 충격에 무방비"
    }
)

# B. 안전재고 단독
strategy_data.append(
    {
        "전략": "B. 안전재고 강화",
        "총비용": safety_stock_cost,
        "기대 회피편익": expected_safety_stock_benefit,
        "기대 순편익": safety_stock_net_benefit,
        "비고": "우기 체선 리스크 방어"
    }
)

# C. 예비 톨링 20%
tolling_20_covered = (
    total_gap_demand * 0.20
)

tolling_20_cost = (
    tolling_20_covered * tolling_unit_cost
)

tolling_20_benefit = (
    feoc_probability
    * tolling_20_covered
    * mitigation_benefit_per_ton
)

strategy_data.append(
    {
        "전략": "C. 예비 톨링 20%",
        "총비용": tolling_20_cost,
        "기대 회피편익": tolling_20_benefit,
        "기대 순편익": (
            tolling_20_benefit - tolling_20_cost
        ),
        "비고": "규제 충격 최소 방어"
    }
)

# D. 예비 톨링 사용자 설정 비율
strategy_data.append(
    {
        "전략": f"D. 예비 톨링 {tolling_coverage * 100:.0f}%",
        "총비용": tolling_cost,
        "기대 회피편익": expected_tolling_benefit,
        "기대 순편익": tolling_net_benefit,
        "비고": "규제 충격 주요 방어"
    }
)

# E. 복합 전략
strategy_data.append(
    {
        "전략": "E. 복합 방어",
        "총비용": combined_cost,
        "기대 회피편익": (
            expected_safety_stock_benefit
            + expected_tolling_benefit
        ),
        "기대 순편익": combined_expected_net_benefit,
        "비고": "기상·규제 동시 방어"
    }
)

df_strategy = pd.DataFrame(strategy_data)

df_strategy["ROI"] = np.where(
    df_strategy["총비용"] > 0,
    df_strategy["기대 순편익"] / df_strategy["총비용"] * 100,
    0.0
)

best_strategy = df_strategy.loc[
    df_strategy["기대 순편익"].idxmax(),
    "전략"
]

st.dataframe(
    df_strategy.style.format(
        {
            "총비용": "${:,.0f}",
            "기대 회피편익": "${:,.0f}",
            "기대 순편익": "${:,.0f}",
            "ROI": "{:,.1f}%"
        }
    ),
    use_container_width=True,
    hide_index=True
)

st.success(
    f"""
    **현재 입력 조건에서 기대 순편익이 가장 높은 전략은  
    ‘{best_strategy}’입니다.**

    본 시스템은 특정 전략을 무조건 권고하지 않으며,  
    기상 충격확률·통상 규제확률·재고유지비율·대체 정제 비용에 따라  
    최적 전략이 달라질 수 있음을 보여줍니다.
    """
)
