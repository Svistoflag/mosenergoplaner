import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from config import YANDEX_API_KEY, YANDEX_GEOCODER_ENDPOINT, OSRM_SERVER_URL
import re

st.set_page_config(layout="wide")
st.title("МОСЭНЕРГОСБЫТ — Построение маршрута по адресам должников")

def is_address(text):
    keywords = ["ул", "улица", "город", "г.", "просп", "переул", "д.", "р-н", "шоссе"]
    return isinstance(text, str) and any(k in text.lower() for k in keywords)

def geocode_yandex(address):
    url = f"{YANDEX_GEOCODER_ENDPOINT}?apikey={YANDEX_API_KEY}&geocode={address}&format=json"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        pos = r.json()["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["Point"]["pos"]
        lon, lat = map(float, pos.split())
        return lat, lon
    except:
        return None, None

def build_osrm_route(coords):
    coord_str = ";".join([f"{lon},{lat}" for lat, lon in coords])
    url = f"{OSRM_SERVER_URL}/route/v1/driving/{coord_str}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()["routes"][0]["geometry"]["coordinates"]
    except:
        return []

from kadastr_processor import KadastrProcessor

uploaded_file = st.file_uploader("📥 Загрузите Excel-файл с адресами", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("🔍 Предварительный просмотр")
    st.dataframe(df.head())

    # Поиск столбца с адресами
    address_col = None
    for col in df.columns:
        if df[col].dropna().astype(str).apply(is_address).mean() > 0.3:
            address_col = col
            break

    manual_col = st.selectbox("📌 Уточните столбец с адресами:", options=df.columns, index=df.columns.get_loc(address_col) if address_col else 0)

    addresses = df[manual_col].dropna().unique().tolist()
    geocoded = []
    for addr in addresses:
        lat, lon = geocode_yandex(addr)
        if lat and lon:
            geocoded.append((addr, lat, lon))

    st.success(f"✅ Геокодировано {len(geocoded)} из {len(addresses)} адресов")

    if geocoded:
        coords = [(lat, lon) for _, lat, lon in geocoded]
        route = build_osrm_route(coords)

        st.subheader("🗺️ Маршрут на карте")
        m = folium.Map(location=coords[0], zoom_start=12)
        for i, (addr, lat, lon) in enumerate(geocoded):
            folium.Marker([lat, lon], tooltip=f"{i+1}. {addr}").add_to(m)
        if route:
            folium.PolyLine([(lat, lon) for lon, lat in route], color="blue").add_to(m)
        st_folium(m, height=600, width=1000)