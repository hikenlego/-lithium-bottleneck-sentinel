import streamlit as st
import pandas as pd
import requests

# 0. 페이지 설정
st.set_page_config(page_title="리튬 공급망 SCM 대시보드", layout="wide")

st.title("배터리 리튬 공급망 조달 병목 모니터링 & AI 의사결정 시스템")
st.caption("호주 포트헤들랜드 선석 포화 - 중국 제련 고집중 - 한국 양극재 클러스터 연계")

# 사이드바 변수 설정
st.sidebar.header("공장 운영 파라미터")
daily_demand = st.sidebar.number_input("일일 리튬 소요량 (톤/일)", 10.0, 300.0, 65.0, 5.0)
lithium_price = st.sidebar.number_input("수산화리튬 가격 ($/톤)", 5000.0, 80000.0, 15000.0, 500.0)
daily_stop_loss = st.sidebar.number_input("가동 중단 일일 손실 ($/일)", 50000.0, 5000000.0, 850000.0, 50000.0)
holding_cost_rate = st.sidebar.slider("연간 재고유지비율 (%)", 3.0, 15.0, 8.0, 0.5) / 100.0

# 1. 해상 운송 거점별 경로 및 추천 옵션
st.header("1. 해상 운송 거점별 경로 및 최적 대안 추천")

route_data = [
    {
        "id": 0,
        "title": "최단 리드타임 추천",
        "name": "한-호 직항 장기계약(COA) 전용선",
        "route": "호주 포트헤들랜드 -> 한국 광양 직항",
        "lead_time": 14,
        "reliability": 94.5,
        "freight": 42.0,
        "desc": "우기 사이클론 시즌 및 선석 체선 리스크를 최소화하여 라인 중단을 방어하는 최우선 안정 항로"
    },
    {
        "id": 1,
        "title": "최고 정시성 추천",
        "name": "중국 제련 톨링 경유 정기선",
        "route": "호주 포트헤들랜드 -> 중국 닝보 기항",
        "lead_time": 18,
        "reliability": 88.0,
        "freight": 33.5,
        "desc": "중국 가공 위탁 라인과 연계된 항로이나, IRA FEOC 통상 규제 시 대체 조치 필요"
    },
    {
        "id": 2,
        "title": "최저 운임 추천",
        "name": "스팟 시장 자유 용선 (동남아 환적)",
        "route": "호주 -> 싱가포르 환적 -> 한국 광양",
        "lead_time": 24,
        "reliability": 76.2,
        "freight": 28.0,
        "desc": "운임이 가장 경제적이나 비정기선 환적으로 리드타임 변동성이 크게 발생"
    }
]

toggle_options = ["전체 항로 종합 비교", "최단 리드타임 추천", "최고 정시성 추천", "최저 운임 추천"]
selected_toggle = st.segmented_control("운송 시나리오 선택", toggle_options, default="전체 항로 종합 비교")

if selected_toggle == "최단 리드타임 추천":
    active_idx = 0
elif selected_toggle == "최고 정시성 추천":
    active_idx = 1
elif selected_toggle == "최저 운임 추천":
    active_idx = 2
else:
    active_idx = None

if active_idx is not None:
    curr = route_data[active_idx]
    st.success(f"선택된 대안: {curr['title']} - {curr['name']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("조달 리드타임", f"{curr['lead_time']} 일")
    c2.metric("운항 정시성", f"{curr['reliability']} %")
    c3.metric("해상 운임", f"${curr['freight']} / 톤")
    st.info(f"구간: {curr['route']} | 분석: {curr['desc']}")
else:
    df_display = pd.DataFrame(route_data)[["title", "name", "lead_time", "reliability", "freight", "route"]]
    df_display.columns = ["추천 구분", "운송 모드", "리드타임(일)", "정시성(%)", "운임($/톤)", "운항 구간"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

# 2. 실시간 외생 변수 모니터링 (Perplexity 연동)
st.header("2. AI 외생 변수 실시간 모니터링 & 자동 판별")
api_key = st.text_input("Perplexity API Key 입력", type="password", placeholder="pplx-...")

target_scenario = st.radio(
    "감지 대상 시나리오",
    (
        "시나리오 1: 호주 필바라 기상 악화 및 항만 폐쇄 (사이클론 병목)",
        "시나리오 2: 통상 규제 및 단일국 의존 (미국 IRA FEOC / 중국 통제)"
    )
)

def query_perplexity(scen, key):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    q = "Check weather and port conditions at Port Hedland Pilbara." if "시나리오 1" in scen else "Check US IRA FEOC restrictions on Chinese refined lithium."
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "You are a supply chain analyst. Start with [STATUS: HIGH_RISK] or [STATUS: NORMAL], followed by 3 short bullet points."},
            {"role": "user", "content": q}
        ],
        "temperature": 0.1
    }
    res = requests.post(url, json=payload, headers=headers)
    return res.json()["choices"][0]["message"]["content"] if res.status_code == 200 else f"오류 발생: {res.text}"

if st.button("실시간 외생 변수 분석 시작"):
    if not api_key:
        st.error("Perplexity API 키를 입력해 주세요.")
    else:
        with st.spinner("글로벌 공급망 데이터를 실시간 검증 중입니다..."):
            report = query_perplexity(target_scenario, api_key)
        
        st.subheader("모니터링 판별 결과")
        if "HIGH_RISK" in report:
            st.error("경보 발령: 공급망 외부 충격 요인이 감지되었습니다.")
        else:
            st.success("정상 상태: 중대한 외부 충격 요인이 없습니다.")
        st.markdown(report)

# 3. 정량 솔루션 및 ROI 산출
st.header("3. 병목 솔루션 수치 산정 및 정량적 ROI 시뮬레이션")

if "시나리오 1" in target_scenario:
    st.subheader("[솔루션 1]: 동적 안전재고(Dynamic Safety Stock) 선제 비축")
    additional_days = 21
    req_stock_ton = daily_demand * additional_days
    inv_cost = (req_stock_ton * lithium_price) * (holding_cost_rate * (additional_days / 365.0))
    prevented_days = 7
    prevented_loss = prevented_days * daily_stop_loss
    net_benefit = prevented_loss - inv_cost
    roi = (net_benefit / inv_cost) * 100.0 if inv_cost > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("권장 추가 비축량", f"{req_stock_ton:,.0f} 톤", f"+{additional_days}일분")
    c2.metric("재고 유지 비용", f"${inv_cost:,.0f}")
    c3.metric("회피 손실액", f"${prevented_loss:,.0f}", f"{prevented_days}일 방어")
    c4.metric("추정 ROI", f"{roi:,.1f} %")
    st.info(f"동적 안전재고 비축을 통해 약 ${inv_cost:,.0f} 비용으로 ${prevented_loss:,.0f} 손실을 방어하여 순편익 ${net_benefit:,.0f} (ROI {roi:.1f}%)를 달성합니다.")
else:
    st.subheader("[솔루션 2]: 국내/FTA 대체 제련소 예비 톨링(Standby Tolling) 가동")
    transition_days = 120
    standby_ton = daily_demand * transition_days * 0.40
    total_standby_cost = standby_ton * 650.0
    prevented_disruption_value = (daily_demand * transition_days) * 3500.0
    net_benefit = prevented_disruption_value - total_standby_cost
    roi = (net_benefit / total_standby_cost) * 100.0 if total_standby_cost > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("예비 톨링 물량", f"{standby_ton:,.0f} 톤", "수요의 40%")
    c2.metric("사전 계약비용", f"${total_standby_cost:,.0f}")
    c3.metric("규제 손실 회피액", f"${prevented_disruption_value:,.0f}", "120일 공백 방어")
    c4.metric("추정 ROI", f"{roi:,.1f} %")
    st.info(f"예비 톨링 계약을 통해 약 ${total_standby_cost:,.0f} 비용으로 ${prevented_disruption_value:,.0f} 손실을 방어하여 순편익 ${net_benefit:,.0f} (ROI {roi:.1f}%)를 달성합니다.")
