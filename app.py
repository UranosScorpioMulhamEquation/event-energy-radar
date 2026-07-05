import streamlit as st
import pandas as pd
import numpy as np
import uuid
import os
import math
from datetime import date, time, timedelta

# ==================== محرك الحساب الخفي (Ephem Engine) ====================
try:
    import ephem
    ASTRO_AVAILABLE = True
except ImportError:
    ASTRO_AVAILABLE = False
    st.warning("يرجى التأكد من تثبيت مكتبة ephem في بيئة العمل.")

# ==================== قاعدة بيانات المنتخبات المتأهلة للدور الثاني (آخر 50 عاماً) ====================
TEAMS_DB = {
    "Argentina (AFA)": date(1893, 2, 21),
    "Brazil (CBF)": date(1914, 6, 8),
    "France (FFF)": date(1919, 4, 7),
    "Germany (DFB)": date(1900, 1, 28),
    "Italy (FIGC)": date(1898, 3, 26),
    "England (FA)": date(1863, 10, 26),
    "Spain (RFEF)": date(1913, 9, 29),
    "Netherlands (KNVB)": date(1889, 12, 8),
    "Portugal (FPF)": date(1914, 3, 31),
    "Croatia (HNS)": date(1912, 6, 13),
    "Uruguay (AUF)": date(1900, 3, 30),
    "Belgium (KBVB)": date(1895, 9, 1),
    "Mexico (FMF)": date(1927, 8, 23),
    "USA (USSF)": date(1913, 4, 5),
    "Japan (JFA)": date(1921, 9, 10),
    "South Korea (KFA)": date(1933, 9, 19),
    "Switzerland (SFV)": date(1895, 4, 15),
    "Colombia (FCF)": date(1924, 10, 12),
    "Chile (FFCh)": date(1895, 6, 19),
    "Sweden (SvFF)": date(1904, 12, 18),
    "Morocco (FRMF)": date(1956, 2, 26),
    "Senegal (FSF)": date(1960, 8, 31),
    "Poland (PZPN)": date(1919, 12, 21),
    "Denmark (DBU)": date(1889, 5, 18),
    "Paraguay (APF)": date(1906, 6, 18),
    "Nigeria (NFF)": date(1945, 1, 1),
    "Ghana (GFA)": date(1957, 1, 1),
    "Australia (FA)": date(1961, 1, 1),
}

# ==================== Metadata & UI Setup ====================
st.set_page_config(page_title="Event Energy & Predictive Radar", layout="wide")
st.title("Event Energy & Predictive Radar")
st.markdown("### Developed By Mulham Ahmad.")

# ==================== الدوال الأساسية (USM Engine) ====================
def run_usm_engine_daily(birth_date):
    homo_k = 6.18
    eris_k = 9.3
    neptune_k = 10.77
    tolerance = 0.3
    
    data = []
    
    for i in range(1, 200):
        homo_dev = abs((i / homo_k) - round(i / homo_k))
        eris_dev = abs((i / eris_k) - round(i / eris_k))
        neptune_dev = abs((i / neptune_k) - round(i / neptune_k))
        
        status = "CRITICAL" if (homo_dev <= tolerance and eris_dev <= tolerance and neptune_dev <= tolerance) else "Normal"
        
        offset_day = int(eris_dev * 30)
        offset_month = int(homo_dev * 12)
        target_year = birth_date.year + i
        
        new_day = birth_date.day + offset_day
        new_month = birth_date.month + offset_month
        new_year = target_year
        
        while new_day > 30: 
            new_day -= 30
            new_month += 1
        
        while new_month > 12:
            new_month -= 12
            new_year += 1
            
        risk_date_str = f"{new_year}-{new_month:02d}-{new_day:02d}"
        data.append([risk_date_str, i, round(homo_dev, 4), round(eris_dev, 4), round(neptune_dev, 4), status])
        
    return pd.DataFrame(data, columns=["Risk Date", "Age (Year)", "Homo Dev", "Eris Dev", "Neptune Dev", "Status"])

def is_year_critical(birth_date, event_date):
    homo_k = 6.18
    eris_k = 9.3
    neptune_k = 10.77
    tolerance = 0.3
    
    age_at_event = event_date.year - birth_date.year
    if age_at_event <= 0:
        return False
        
    homo_dev = abs((age_at_event / homo_k) - round(age_at_event / homo_k))
    eris_dev = abs((age_at_event / eris_k) - round(age_at_event / eris_k))
    neptune_dev = abs((age_at_event / neptune_k) - round(age_at_event / neptune_k))
    
    return (homo_dev <= tolerance and eris_dev <= tolerance and neptune_dev <= tolerance)

# ==================== دوال الحساب الطاقي المخفي ====================
zodiac_signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 
                'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

def get_energy_positions(target_date, target_time="12:00:00", entities_list=[]):
    if not ASTRO_AVAILABLE:
        return {}
    
    date_str = target_date.strftime("%Y/%m/%d")
    time_str = target_time if isinstance(target_time, str) else target_time.strftime("%H:%M:%S")
    compute_date = f"{date_str} {time_str}"
    
    positions = {}
    
    for entity in entities_list:
        if entity == 'Sun': p = ephem.Sun()
        elif entity == 'Moon': p = ephem.Moon()
        elif entity == 'Mars': p = ephem.Mars()
        elif entity == 'Venus': p = ephem.Venus()
        elif entity == 'Jupiter': p = ephem.Jupiter()
        elif entity == 'Uranus': p = ephem.Uranus()
        else: continue
        
        p.compute(compute_date)
        lon_rad = ephem.Ecliptic(p).lon
        lon_deg = math.degrees(lon_rad) % 360
        idx = int(lon_deg / 30)
        positions[entity] = zodiac_signs[idx]
        
    return positions

def has_harmonious_aspect(base_sign, transit_sign):
    try:
        b_idx = zodiac_signs.index(base_sign)
        t_idx = zodiac_signs.index(transit_sign)
        diff = abs(b_idx - t_idx)
        # التطابق (0)، التسديس (60)، التثليث (120)
        if diff in [0, 2, 10, 4, 8]:
            return True
        return False
    except ValueError:
        return False

def calculate_support_score(base_date, event_date, event_time):
    base_entities = ['Sun', 'Mars']
    base_pos = get_energy_positions(base_date, "12:00:00", base_entities)
    
    transit_entities = ['Sun', 'Moon', 'Mars', 'Venus', 'Jupiter', 'Uranus']
    transit_pos = get_energy_positions(event_date, event_time, transit_entities)
    
    sun_supported = False
    mars_supported = False
    supporting_factors = set()
    
    # فحص التناغم بين المتغيرات العابرة والأساسية
    for t_ent, t_sign in transit_pos.items():
        if has_harmonious_aspect(base_pos.get('Sun'), t_sign):
            sun_supported = True
            supporting_factors.add(t_ent)
            
        if has_harmonious_aspect(base_pos.get('Mars'), t_sign):
            mars_supported = True
            supporting_factors.add(t_ent)
            
    factor_count = len(supporting_factors)
    raw_percentage = factor_count * 16.66
    
    # تطبيق سقف النسبة المئوية
    if sun_supported and mars_supported:
        final_percentage = min(raw_percentage, 100.0)
    elif sun_supported or mars_supported:
        final_percentage = min(raw_percentage, 50.0)
    else:
        final_percentage = 0.0
        
    return round(final_percentage, 2)

# ==================== UI Layout ====================
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Base Inception Date")
    # إضافة خيار اختيار المصدر
    input_method = st.radio("Select Input Method:", ["Select Team from List", "Manual Entry"])
    
    if input_method == "Select Team from List":
        selected_team = st.selectbox("If it's a sporting event, Select National Team:", options=list(TEAMS_DB.keys()))
        birth_date = TEAMS_DB[selected_team]
        st.write(f"Inception Date: **{birth_date.strftime('%Y-%m-%d')}**")
    else:
        birth_date = st.date_input("Select Base Date", value=date(1981, 4, 17), min_value=date(1800, 1, 1), max_value=date(2100, 1, 1))

with col2:
    st.subheader("2. Target Event Details")
    event_date = st.date_input("Select Event Date Or Critical Date", value=date(2026, 7, 19), min_value=date(1800, 1, 1), max_value=date(2100, 1, 1))
    event_time = st.time_input("Select Event Time , If unknown set 08.00", value=time(20, 0)) 

st.markdown("---")

# ==================== أزرار التحليل ====================
c1, c2 = st.columns(2)

with c1:
    if st.button("Generate Historical Radar", use_container_width=True):
        df = run_usm_engine_daily(birth_date)
        def color_status(val):
            return 'background-color: red; color: white' if val == 'CRITICAL' else 'background-color: green; color: white'
        
        styled_df = df.style.map(color_status, subset=['Status'])
        if not df.empty:
            st.dataframe(styled_df, use_container_width=True, height=300)
        else:
            st.warning("No CRITICAL dates found.")

with c2:
    if st.button("Execute Predictive Event Analysis", use_container_width=True):
        if ASTRO_AVAILABLE:
            st.markdown("### 📊 Event Prediction Results")
            
            # 1. فحص الحالة الحرجة
            is_critical = is_year_critical(birth_date, event_date)
            
            # 2. حساب النسبة المئوية للدعم الطاقي
            support_percentage = calculate_support_score(birth_date, event_date, event_time)
            
            # 3. عرض النتائج بمنطق رياضي حاسم
            if is_critical:
                if support_percentage > 0:
                    st.success(f"🟢 **A critical day with a positive trajectory (Positive Critical Day)**")
                    st.write(f"A high energy compatibility was detected that supports achieving a success or victory with a certain percentage: **{support_percentage}%**")
                    st.progress(int(support_percentage))
                else:
                    st.error(f"🔴 **A critical day with no energy support (Negative Critical Day)**")
                    st.write(f"support_percentage: **0%** - The algorithm indicates a lack of immediate support, increasing the likelihood of loss or decline..")
                    st.progress(0)
            else:
                if support_percentage > 0:
                    st.warning(f"⚠️ **day with energy support**")
                    st.write(f"The event does not occur in a year of radical change, but it carries an immediate support level equivalent to: **{support_percentage}%**")
                    st.progress(int(support_percentage))
                else:
                    st.info(f"⚪ **A neutral ordinary day (Neutral Day)**")
                    st.write("support_percentage: **0%** - There is no radical change or significant energy boost at this time.")
                    st.progress(0)
        else:
            st.error("Engine failure: Predictive calculations require 'ephem' library.")
