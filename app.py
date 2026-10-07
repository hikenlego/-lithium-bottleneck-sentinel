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

# 토글 슬라이드 애니메이션 및 카드 전환 모션 CSS (문법 안전성 확보)
custom_css = """
<style>
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    
    div[data-testid="stSegmentedControl"] {
        background: #f1f5f9;
        padding: 5px;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.04);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    div[data-testid="stSegmentedControl"] button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        border: none !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1
