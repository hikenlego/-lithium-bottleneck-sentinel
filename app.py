import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import requests
import json

# 0. 기본 설정
st.set_page_config(page_title="리튬 공급망 SCM 시스템", layout="wide")

# CSS 주입
custom_css = (
    "<style>"
    "div[data-testid='stMetricValue'] { font-size: 1.8rem; }"
    "div[data-testid='stSegmentedControl'] {"
    "    background: #f1f5f9; padding: 5px; border-radius: 14px;"
    "    border: 1px solid #e2e8f0; box-shadow: inset 0 2px 4px rgba(0,0,0,0.04);"
    "}"
    "div[data-testid='stSegmentedControl'] button {"
    "    border-radius: 10px !important; font-weight: 600 !important; border: none !important;"
    "    transition: all 0.3s ease !important;"
    "}"
    "div[data-testid='stSegmentedControl'] button:hover {"
    "    background-color: rgba(255, 255, 255, 0.7) !important;"
    "}"
    "div[data-testid='stSegmentedControl'] button[aria-checked='true'] {"
    "    background: #ffffff !important; color: #0f172a !important;"
    "    box-shadow: 0 4px 10px -2px rgba(0, 0, 0, 0.1) !important;"
    "}"
    ".route-card {"
    "    padding: 24px; border-radius: 14px; background: #ffffff;"
    "    border: 1px solid #e2e8f0; margin-top: 15px; margin-bottom: 25px;"
    "    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);"
    "}"
    "</style>"
)
st.markdown(custom_css, unsafe_allow_html=True)

st.title("배터리 리튬 공급망 실시간 외생 병목 모니터링 & SCM 최적화 대시보드")
st.markdown("호주 포트헤들랜드 선석 과포화 및 기상 변동 - 중국 제련 고집중 - 한국 양극재 클러스터 연계")

# 사이드바 변수
st.sidebar.header("공장 운영 및 원가 시뮬레이션 변수")
daily_demand = st.sidebar.number_input("일일 리튬 소요량 (톤/일)", 10.0, 300.0, 65.0, 5.0)
lithium_price = st.sidebar.number_input("수산화리튬 가격 ($/톤)", 5000.0, 80000.0, 15000.0, 500.0)
daily_stop_loss = st.sidebar.number_input("가동 중단 손실액 ($/일)", 50000.0, 5000000.0, 850000.0, 50000.0)
holding_cost_rate = st.sidebar.slider("연간 재고유지비율 (%)", 3.0, 15.0, 8.0, 0.5) / 100.0

# 1. 해상 운송 거점별 경로 및 모션 토글 슬라이드
st.header("1. 해상 운송 거점별 경로 및 최적 대안 추천")

route_data = [
    {
        "id": 0,
        "title": "최단 리드타임 추천",
        "name": "한-호 직항 장기운송계약(COA) 전용선",
        "vessel_type": "Su
