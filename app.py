import streamlit as st
import pandas as pd
import numpy as np
import uuid
import os
import math
from datetime import date, time, datetime, timezone, timedelta
from dataclasses import dataclass

# محاولة استيراد المنطقة الزمنية الحديثة من مكتبة بايثون القياسية
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# ==================== محرك الحساب الدقيق (libephemeris Engine) ====================
# يعتمد المحرك على معادلات فلكية دقيقة خلف الكواليس دون إظهار التفاصيل للمستخدم
try:
    import libephemeris as swe
    ASTRO_AVAILABLE = True
except ImportError:
    try:
        import swisseph as swe
        ASTRO_AVAILABLE = True
    except ImportError:
        ASTRO_AVAILABLE = False
        st.error("خطأ في النظام: لم يتم العثور على مكتبة الحسابات الرياضية الدقيقة 'libephemeris'.")

# ==================== هياكل البيانات المخصصة للحسابات ====================
@dataclass
class City:
    name: str
    latitude: float
    longitude: float

@dataclass
class SolarChart:
    birth_local: datetime
    return_local: datetime
    solar_asc_deg: float
    solar_mc_deg: float
    asc_sign_name: str
    planet_rows: list
    house_system: str

# ==================== قاعدة بيانات المنتخبات الكبرى ====================

TEAMS_DB = {
    "Argentina (AFA)": {"date": date(1893, 2, 21), "city": "Buenos Aires", "lat": -34.6037, "lon": -58.3816, "tz": "America/Argentina/Buenos_Aires"},
    "Brazil (CBF)": {"date": date(1914, 6, 8), "city": "Rio de Janeiro", "lat": -22.9068, "lon": -43.1729, "tz": "America/Sao_Paulo"},
    "France (FFF)": {"date": date(1919, 4, 7), "city": "Paris", "lat": 48.8566, "lon": 2.3522, "tz": "Europe/Paris"},
    "Germany (DFB)": {"date": date(1900, 1, 28), "city": "Leipzig", "lat": 51.3397, "lon": 12.3731, "tz": "Europe/Berlin"},
    "Italy (FIGC)": {"date": date(1898, 3, 26), "city": "Rome", "lat": 41.9028, "lon": 12.4964, "tz": "Europe/Rome"},
    "England (FA)": {"date": date(1863, 10, 26), "city": "London", "lat": 51.5074, "lon": -0.1278, "tz": "Europe/London"},
    "Spain (RFEF)": {"date": date(1913, 9, 29), "city": "Madrid", "lat": 40.4168, "lon": -3.7038, "tz": "Europe/Madrid"},
    "Uruguay (AUF)": {"date": date(1900, 3, 30), "city": "Montevideo", "lat": -34.9011, "lon": -56.1645, "tz": "America/Montevideo"}, # تمت إضافتها
    "Portugal (FPF)": {"date": date(1914, 3, 31), "city": "Lisbon", "lat": 38.7223, "lon": -9.1393, "tz": "Europe/Lisbon"}
}

# ==================== قاعدة بيانات دول ومدن الأحداث العالمية ====================
LOCATION_DB = {
"United States": {
        "New York / New Jersey": "America/New_York", # (مستضيفة النهائي)
        "Los Angeles": "America/Los_Angeles",
        "Dallas": "America/Chicago",
        "Miami": "America/New_York",
        "Atlanta": "America/New_York",
        "Boston": "America/New_York",
        "Houston": "America/Chicago",
        "Philadelphia": "America/New_York",
        "Kansas City": "America/Chicago",
        "Seattle": "America/Los_Angeles",
        "San Francisco Bay Area": "America/Los_Angeles"
    },
    "Canada": {
        "Toronto": "America/Toronto",
        "Vancouver": "America/Vancouver"
    },
    "Mexico": {
        "Mexico City": "America/Mexico_City",
        "Monterrey": "America/Monterrey",
        "Guadalajara": "America/Mexico_City"
    },
    "United Kingdom": {"London": "Europe/London"},
    "France": {"Paris": "Europe/Paris"},
    "Germany": {"Berlin": "Europe/Berlin", "Munich": "Europe/Berlin"},
    "Spain": {"Madrid": "Europe/Madrid", "Barcelona": "Europe/Madrid"},
    "Italy": {"Rome": "Europe/Rome", "Milan": "Europe/Rome"},
    "Brazil": {"Rio de Janeiro": "America/Sao_Paulo", "Sao Paulo": "America/Sao_Paulo"},
    "Argentina": {"Buenos Aires": "America/Argentina/Buenos_Aires"},
    "Qatar": {"Doha": "Asia/Qatar"},
    "Saudi Arabia": {"Riyadh": "Asia/Riyadh"},
    "United Arab Emirates": {"Dubai": "Asia/Dubai", "Abu Dhabi": "Asia/Dubai"},
    "Japan": {"Tokyo": "Asia/Tokyo"},
    "South Korea": {"Seoul": "Asia/Seoul"},
    "Morocco": {"Casablanca": "Africa/Casablanca"},
    "Egypt": {"Cairo": "Africa/Cairo"},
    "South Africa": {"Johannesburg": "Africa/Johannesburg"},
    "Australia": {"Sydney": "Australia/Sydney", "Melbourne": "Australia/Melbourne"}
}

zodiac_signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

# ==================== Metadata & UI Setup ====================
st.set_page_config(page_title="Mathematical Predictive Analysis Model - FIFA World Cup", layout="wide")
st.title("⚽ Mathematical Predictive Analysis Model - FIFA World Cup ⚽")
st.markdown("### By : Mulham Ahmad Halabieh")

# ==================== دوال الحساب الرياضية الداخلية (محتفظ بها دون تغيير) ====================
def get_timezone_for_city(city: City) -> str:
    for team, info in TEAMS_DB.items():
        if info["city"] == city.name:
            return info["tz"]
    return "UTC"

def zodiac_info(longitude: float) -> tuple[str, int, float]:
    signs = ["الحمل", "الثور", "الجوزاء", "السرطان", "الأسد", "العذراء",
             "الميزان", "العقرب", "القوس", "الجدي", "الدلو", "الحوت"]
    sign_idx = int((longitude % 360) / 30)
    degree = (longitude % 30)
    return signs[sign_idx], sign_idx, degree

def find_solar_return_exact(birth_jd_utc: float, target_year: int) -> float:
    natal_sun_lon = swe.calc_ut(birth_jd_utc, swe.SUN)[0][0]
    jd_start = swe.julday(target_year, 1, 1, 0.0)
    jd_end = swe.julday(target_year, 12, 31, 23.999)
    
    for _ in range(50):
        jd_mid = (jd_start + jd_end) / 2.0
        mid_sun_lon = swe.calc_ut(jd_mid, swe.SUN)[0][0]
        diff = (mid_sun_lon - natal_sun_lon) % 360
        if diff > 180: diff -= 360
        if diff < 0: jd_start = jd_mid
        else: jd_end = jd_mid
            
    return (jd_start + jd_end) / 2.0

def calculate_chart(birth_date: date, birth_time_input, birth_city: City, return_city: City, target_year: int) -> SolarChart:
    is_unknown_time = (birth_time_input == "الساعة غير معروفة")
    actual_time = time(12, 0) if is_unknown_time else birth_time_input
    birth_tz_name = get_timezone_for_city(birth_city)
    return_tz_name = get_timezone_for_city(return_city)
    birth_tz = ZoneInfo(birth_tz_name) if birth_tz_name else timezone.utc
    return_tz = ZoneInfo(return_tz_name) if return_tz_name else timezone.utc
    
    birth_local = datetime.combine(birth_date, actual_time, tzinfo=birth_tz)
    birth_utc = birth_local.astimezone(timezone.utc)
    birth_jd_utc = swe.julday(birth_utc.year, birth_utc.month, birth_utc.day, birth_utc.hour + birth_utc.minute/60.0 + birth_utc.second/3600.0)
    
    return_jd_utc = find_solar_return_exact(birth_jd_utc, target_year)
    y, m, d, h_float = swe.revjul(return_jd_utc)
    hours = int(h_float)
    minutes = int((h_float - hours) * 60)
    seconds = int((((h_float - hours) * 60) - minutes) * 60)
    
    return_local = datetime(y, m, d, hours, minutes, seconds, tzinfo=timezone.utc).astimezone(return_tz)
    cusps, ascmc = swe.houses_ex(return_jd_utc, return_city.latitude, return_city.longitude, b'W')
    solar_asc_deg, solar_mc_deg = ascmc[0], ascmc[1]
    asc_sign_name, asc_sign_idx, _ = zodiac_info(solar_asc_deg)
    house_system_name = "Whole Sign (كل برج بيت)"

    if is_unknown_time:
        sun_coords, _ = swe.calc_ut(return_jd_utc, swe.SUN)
        sun_lon_deg = sun_coords[0]
        sun_sign_name, sun_sign_idx, _ = zodiac_info(sun_lon_deg)
        asc_sign_name = f"{sun_sign_name} (طالع شمسي افتراضي)"
        asc_sign_idx = sun_sign_idx 
        solar_asc_deg = sun_lon_deg 
        house_system_name = "Solar Sign (البيوت الشمسية)"

    planets_to_calc = {
        "الشمس": swe.SUN, "القمر": swe.MOON, "عطارد": swe.MERCURY, "الزهرة": swe.VENUS, 
        "المريخ": swe.MARS, "المشتري": swe.JUPITER, "زحل": swe.SATURN, "أورانوس": swe.URANUS, 
        "نبتون": swe.NEPTUNE, "بلوتو": swe.PLUTO
    }
    
    planet_rows = []
    for name, p_id in planets_to_calc.items():
        coords, _ = swe.calc_ut(return_jd_utc, p_id)
        lon_deg, speed = coords[0], coords[3]
        sign_name, sign_idx, deg_rem = zodiac_info(lon_deg)
        house_num = ((sign_idx - asc_sign_idx) % 12) + 1
        planet_rows.append({
            "الكوكب": name, "الموقع": f"{sign_name} {deg_rem:.2f}°", "البيت": str(house_num),
            "الحركة": "متراجع" if speed < 0 else "مباشر", "درجة_البرج": deg_rem, "الطول_المطلق": lon_deg
        })
        
    return SolarChart(birth_local, return_local, solar_asc_deg, solar_mc_deg, asc_sign_name, planet_rows, house_system=house_system_name)

def run_usm_engine_daily(birth_date):
    homo_k = 6.18; eris_k = 9.3; neptune_k = 10.77; tolerance = 0.3
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
    homo_k = 6.18; eris_k = 9.3; neptune_k = 10.77; tolerance = 0.3
    age_at_event = event_date.year - birth_date.year
    if age_at_event <= 0: return False
    homo_dev = abs((age_at_event / homo_k) - round(age_at_event / homo_k))
    eris_dev = abs((age_at_event / eris_k) - round(age_at_event / eris_k))
    neptune_dev = abs((age_at_event / neptune_k) - round(age_at_event / neptune_k))
    return (homo_dev <= tolerance and eris_dev <= tolerance and neptune_dev <= tolerance)

def get_julian_day_precise(target_date, target_time, tz_str="UTC") -> float:
    try: tz = ZoneInfo(tz_str)
    except Exception: tz = timezone.utc
    local_dt = datetime.combine(target_date, target_time)
    local_dt = local_dt.replace(tzinfo=tz)
    utc_dt = local_dt.astimezone(timezone.utc)
    decimal_hour = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, decimal_hour)
    return jd

def get_energy_positions_precise(target_date, target_time="12:00:00", tz_str="UTC", entities_list=[]):
    if not ASTRO_AVAILABLE: return {}
    if isinstance(target_time, str):
        try:
            h, m, s = map(int, target_time.split(':'))
            t_val = time(h, m, s)
        except ValueError: t_val = time(12, 0, 0)
    else: t_val = target_time
    jd_utc = get_julian_day_precise(target_date, t_val, tz_str)
    swe_mapping = {'Sun': swe.SUN, 'Moon': swe.MOON, 'Mars': swe.MARS, 'Venus': swe.VENUS, 'Jupiter': swe.JUPITER, 'Uranus': swe.URANUS}
    positions = {}
    for entity in entities_list:
        p_id = swe_mapping.get(entity)
        if p_id is not None:
            coords, _ = swe.calc_ut(jd_utc, p_id)
            lon_deg = coords[0] % 360
            idx = int(lon_deg / 30)
            positions[entity] = zodiac_signs[idx]
    return positions

def has_harmonious_aspect(base_sign, transit_sign):
    if not base_sign or not transit_sign: return False
    try:
        b_idx = zodiac_signs.index(base_sign)
        t_idx = zodiac_signs.index(transit_sign)
        diff = abs(b_idx - t_idx)
        if diff in [0, 2, 10, 4, 8]: return True
        return False
    except ValueError: return False

def calculate_support_score(base_date, event_date, event_time, base_tz="UTC", event_tz="UTC"):
    base_entities = ['Sun', 'Mars']
    base_pos = get_energy_positions_precise(base_date, time(12, 0), base_tz, base_entities)
    transit_entities = ['Sun', 'Moon', 'Mars', 'Venus', 'Jupiter', 'Uranus']
    transit_pos = get_energy_positions_precise(event_date, event_time, event_tz, transit_entities)
    
    sun_supported = False
    mars_supported = False
    supporting_factors = set()
    
    for t_ent, t_sign in transit_pos.items():
        if has_harmonious_aspect(base_pos.get('Sun'), t_sign):
            sun_supported = True
            supporting_factors.add(t_ent)
        if has_harmonious_aspect(base_pos.get('Mars'), t_sign):
            mars_supported = True
            supporting_factors.add(t_ent)
            
    factor_count = len(supporting_factors)
    raw_percentage = factor_count * 16.66
    
    if sun_supported and mars_supported: final_percentage = min(raw_percentage, 100.0)
    elif sun_supported or mars_supported: final_percentage = min(raw_percentage, 50.0)
    else: final_percentage = 0.0
    return round(final_percentage, 2)

# ==================== بناء واجهة المستخدم (UI Layout) ====================
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Base Team Data (بيانات المنتخب)")
    selected_team = st.selectbox("Select National Team (اختر المنتخب):", options=list(TEAMS_DB.keys()))
    
    team_data = TEAMS_DB[selected_team]
    birth_date = team_data["date"]
    lat = team_data["lat"]
    lon = team_data["lon"]
    tz_name = team_data["tz"]
    city_name = team_data["city"]
    
    st.info(f"🏟️ **المنتخب المختار:** {selected_team}\n\n"
            f"📅 **تاريخ التأسيس المرجعي:** {birth_date.strftime('%Y-%m-%d')}\n\n"
            f"📍 **نقطة المرجعية الجغرافية:** {city_name}")

with col2:
    st.subheader("2. Target Event Details (بيانات اللقاء / الحدث المرصود)")
    event_date = st.date_input("Select Event Date (تاريخ المباراة)", value=date(2026, 7, 19), min_value=date(1800, 1, 1), max_value=date(2100, 1, 1))
    event_time = st.time_input("Select Event Time (توقيت المباراة المحلي)", value=time(20, 0)) 
    
    # القوائم المنسدلة لاختيار دولة الحدث ومدينته لتحديد الـ Timezone
    selected_country = st.selectbox("Event Country (دولة الحدث):", list(LOCATION_DB.keys()))
    cities_in_country = list(LOCATION_DB[selected_country].keys())
    selected_city = st.selectbox("Event City (مدينة الحدث):", cities_in_country)
    
    event_tz = LOCATION_DB[selected_country][selected_city]

st.markdown("---")

# ==================== زر التشغيل وعرض النتائج ====================
if st.button("Execute Predictive Analysis (بدء التحليل واستخراج التوقع)", use_container_width=True):
    if ASTRO_AVAILABLE:
        st.markdown("### 📊 Predictive Analysis Results (نتائج الخوارزمية التوقعية)")
        
        # استدعاء الحسابات الرياضية المخفية
        is_critical = is_year_critical(birth_date, event_date)
        support_percentage = calculate_support_score(birth_date, event_date, event_time, tz_name, event_tz)
        
        # عرض الإخراج بأسلوب مهني واحترافي يركز على مؤشرات الأداء الإحصائية
        if is_critical:
            if support_percentage > 0:
                st.success(f"🟢 **High Performance Indicators (مؤشرات أداء عالية ومسار إيجابي)**")
                st.write(f"تؤكد الخوارزمية الرياضية وجود مؤشرات أداء إيجابية استثنائية تدعم فرصة الفوز بنسبة: **{support_percentage}%**")
                st.progress(int(support_percentage))
            else:
                st.error(f"🔴 **Low Performance Indicators (مؤشرات أداء ضعيفة ومسار سلبي)**")
                st.write(f"تشير الخوارزمية إلى غياب عوامل الدعم الإحصائي في هذا التوقيت، مما يزيد من احتمالية التراجع. **(0%)**")
                st.progress(0)
        else:
            if support_percentage > 0:
                st.warning(f"⚠️ **Positive Momentum (زخم إيجابي داعم)**")
                st.write(f"يحمل توقيت الحدث مؤشرات أداء داعمة وزخماً إيجابياً بنسبة: **{support_percentage}%**")
                st.progress(int(support_percentage))
            else:
                st.info(f"⚪ **Neutral Baseline (مؤشرات أداء اعتيادية)**")
                st.write("الاحتمالات الإحصائية ضمن المعدل الطبيعي. نسبة المؤشرات الاستثنائية: **0%**")
                st.progress(0)
    else:
        st.error("خطأ في المحرك الرياضي: تتطلب الحسابات الدقيقة استيراد مكتبة 'libephemeris' بنجاح.")
