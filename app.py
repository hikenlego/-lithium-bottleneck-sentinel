import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import requests
import json

# ---------------------------------------------------------
# 0. 기본 설정 및 인터랙티브 슬라이드 CSS 주입
# ---------------------------------------------------------
st.set_page_config(
    page_title="리튬 공급망 조달 병목 대응 의사결정 시스템",
    layout="wide"
)

# 토글 슬라이드 애니메이션 및 카드 전환 모션 CSS
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    
    /* 세그먼트 컨트롤 컨테이너 모던 라운딩 및 그림자 */
    div[data-testid="stSegmentedControl"] {
        background: #f1f5f9;
        padding: 5px;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.04);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* 개별 세그먼트 버튼 슬라이딩 인터랙션 */
    div[data-testid="stSegmentedControl"] button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        border: none !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    div[data-testid="stSegmentedControl"] button:hover {
        transform: translateY(-1px);
        background-color: rgba(255, 255, 255, 0.7) !important;
    }

    div[data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background: #ffffff !important;
        color: #0f172a !important;
        box-shadow: 0 4px 10px -2px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        transform: scale(1.02);
    }

    /* 하단 상세 패널 슬라이드-인 애니메이션 */
    .route-card {
        padding: 24px;
        border-radius: 14px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0,
