import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import requests

# ---------------------------------------------------------
# 0. 페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="리튬 공급망 SCM 의사결정 시스템",
    layout="wide"
)

st.title("배터리 리튬 공급망 조달 병목 모니터링 & AI 의사결정 대시보드")
st.markdown("호주 포트헤들랜드 - 중국 제련 거점 - 한국 양극재 클러스터 연계 최적화")

# ---------------------------------------------------------
# 1. 해상 운송 경로 분석 및 3대 최적 추천
# ---------------------------------------------------------
st.header("1. 실시간 해상 운송 경로 분석 및 추천")

route_data = [
    {
        "carrier": "A선사 (한-중-호 전용선)",
        "origin": "Port Hedland",
        "destination": "Gwangyang",
        "route_type": "호주 -> 광양 직항",
        "lead_time_days": 14,
        "reliability": 94.5,
        "freight_cost_usd": 42.0,
        "coords": [[-20.3167, 118.576], [34.9754, 127.697]]
    },
    {
        "carrier": "B선사 (중국 기항 정기선)",
        "origin": "Port Hedland",
        "destination": "Ningbo",
        "route_type": "호주 -> 닝보 톨링 라인",
        "lead_time_days": 18,
        "reliability": 88.0,
        "freight_cost_usd": 33.5,
        "coords": [[-20.3167, 118.576], [29.8683, 121.544]]
    },
    {
        "carrier": "C선사 (글로벌 스팟 벌크)",
        "origin": "Port Hedland",
        "destination": "Gwangyang",
        "route_type": "동남아 경유 환적",
        "lead_time_days": 24,
        "reliability": 76.2,
        "freight_cost_usd": 28.0,
        "coords": [[-20.3167, 118.576], [1.3521, 103.8198], [34.9754, 127.697]]
    }
]

df_routes = pd.DataFrame(route_data)

# 3대 최적 옵션 추출
best_lead_time = df_routes.loc[df_routes["lead_time_days"].idxmin()]
best_reliability = df_routes.loc[df_routes["reliability"].idxmax()]
best_cost = df_routes.loc[df_routes["freight_cost_usd"].idxmin()]

# 추천 카드 3개 표시
col1, col2, col3 = st.columns(3)
with col1:
    st.success("최단 리드타임 추천")
    st.metric("선사", best_lead_time["carrier"])
    st.write(f"소요 시간: {best_lead_time['lead_time_days']}일 (운임: ${best_lead_time['freight_cost_usd']}/톤)")
with col2:
    st.info("최고 정시성 추천")
    st.metric("선사", best_reliability["carrier"])
    st.write(f"정시성: {best_reliability['reliability']}% (소요: {best_reliability['lead_time_days']}일)")
with col3:
    st.warning("최저 운임 추천")
    st.metric("선사", best_cost["carrier"])
    st.write(f"운임: ${best_cost['freight_cost_usd']}/톤 (정시성: {best_cost['reliability']}%)")

# 지도 렌더링
m = folium.Map(location=[5.0, 120.0], zoom_start=3)
colors = ["#2ecc71", "#3498db", "#e74c3c"]

for idx, r in df_routes.iterrows():
    folium.PolyLine(
        locations=r["coords"],
        color=colors[idx % len(colors)],
        weight=4,
        opacity=0.8,
        tooltip=f"{r['carrier']} | {r['route_type']} | {r['lead_time_days']}일 | ${r['freight_cost_usd']}/톤"
    ).add_to(m)

st_folium(m, width=1200, height=450)

# ---------------------------------------------------------
# 2. AI 외생 변수 감지 & SCM 솔루션 ROI 분석
# ---------------------------------------------------------
st.header("2. AI 외생 변수 감지 & SCM 솔루션 ROI 분석")

perplexity_api_key = st.text_input("Perplexity API Key 입력", type="password")

scenario = st.selectbox(
    "감지할 병목 시나리오(IF 조건) 선택",
    [
        "시나리오 A: 호주 필바라 우기 사이클론 기상 악화 및 항만 폐쇄 리스크",
        "시나리오 B: 미국 IRA FEOC 규제 강화에 따른 중국 제련 톨링 퇴출 리스크"
    ]
)

def query_perplexity(prompt, api_key):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": "You are a factual supply chain analyst. Answer strictly based on verified recent web data. Conclude whether the specified condition is TRUE or FALSE, and summarize the verifiable reasons concisely."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"API 호출 오류 (상태 코드: {response.status_code}): {response.text}"

if st.button("실시간 외생 변수 감지 및 솔루션 산출 실행"):
    if not perplexity_api_key:
        st.error("Perplexity API 키를 입력해 주세요.")
    else:
        with st.spinner("Perplexity 실시간 검색 엔진이 최신 외생 변수 데이터를 검증 중입니다..."):
            if "시나리오 A" in scenario:
                query_text = "What is the current meteorological outlook for tropical cyclones and heavy rainfall in the Pilbara region of Western Australia? Are there any port closures or rail disruptions at Port Hedland affecting spodumene shipments right now or in this season?"
            else:
                query_text = "What is the latest status of US IRA FEOC enforcement regarding Chinese lithium refining? Are Korean cathode manufacturers currently required to exclude Chinese-smelted lithium hydroxide to receive tax credits?"
            
            ai_verdict = query_perplexity(query_text, perplexity_api_key)

        st.subheader("외생 변수 실시간 모니터링 판별 결과")
        st.write(ai_verdict)

        # -----------------------------------------------------
        # 정량적 수치 산정 및 ROI 계산 로직
        # -----------------------------------------------------
        st.subheader("정량적 솔루션 적용 규모 및 ROI 분석")

        # 기준 파라미터 (연산 50,000톤급 양극재 생산 라인 기준)
        daily_lithium_demand_ton = 65.0
        lithium_price_per_ton = 18000.0
        line_stop_loss_per_day = 850000.0

        if "시나리오 A" in scenario:
            st.markdown("#### [적용 솔루션]: 동적 안전재고(Dynamic Safety Stock) 선제적 비축")
            additional_stock_days = 21
            target_buffer_ton = daily_lithium_demand_ton * additional_stock_days
            holding_cost_rate = 0.08 / 12 * (additional_stock_days / 30)
            
            total_investment_cost = (target_buffer_ton * lithium_price_per_ton) * holding_cost_rate
            prevented_downtime_days = 7
            prevented_loss = prevented_downtime_days * line_stop_loss_per_day
            net_benefit = prevented_loss - total_investment_cost
            roi = (net_benefit / total_investment_cost) * 100

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("권장 추가 안전재고", f"{target_buffer_ton:,.0f} 톤", f"+{additional_stock_days}일분 비축")
            col_b.metric("재고 유지 비용 (Cost)", f"${total_investment_cost:,.0f}")
            col_c.metric("회피된 셧다운 손실 (Benefit)", f"${prevented_loss:,.0f}")

            st.success(f"**순편익 (Net Benefit)**: ${net_benefit:,.0f} | **추정 ROI**: {roi:.1f}%")
            st.caption("산출 근거: 호주 포트헤들랜드 사이클론 시즌 조달 변동 계수(CV 0.310) 대응 7일간의 생산 라인 완전 정지 리스크 방어 기준.")

        else:
            st.markdown("#### [적용 솔루션]: 국내/FTA 대체 제련소 예비 톨링(Standby Tolling) 가동")
            transition_gap_days = 120
            standby_capacity_ton = daily_lithium_demand_ton * transition_gap_days * 0.4
            tuning_and_reservation_fee = standby_capacity_ton * 650.0
            
            prevented_ira_penalty = (daily_lithium_demand_ton * transition_gap_days) * 3500.0
            net_benefit = prevented_ira_penalty - tuning_and_reservation_fee
            roi = (net_benefit / tuning_and_reservation_fee) * 100

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("예비 톨링 사전 전환 물량", f"{standby_capacity_ton:,.0f} 톤", "총 수요의 40% 이원화")
            col_b.metric("사전 튜닝 및 예약비용", f"${tuning_and_reservation_fee:,.0f}")
            col_c.metric("보조금 박탈 및 공백 회피액", f"${prevented_ira_penalty:,.0f}")

            st.success(f"**순편익 (Net Benefit)**: ${net_benefit:,.0f} | **추정 ROI**: {roi:.1f}%")
            st.caption("산출 근거: 제련처 대체 전환 시차(100~150일) 동안 하류 공장에 발생하는 원료 고갈 및 IRA 보조금 배제 손실 방어 기준.")
