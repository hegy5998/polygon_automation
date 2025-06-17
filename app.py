import streamlit as st
import pandas as pd
import requests
import json
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components

HEADERS = {
    'User-Agent': ua.random,
    'Referer': 'https://polygonautomation-cm9hhicmdvkxc6maiyqpsp.streamlit.app/'
}

def fetch_osm_geojson(query):
    url = f"https://nominatim.openstreetmap.org/search?polygon_geojson=1&q={query}&format=json"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        if data and 'geojson' in data[0]:
            return data[0]['geojson'], data[0].get('display_name', '')
    return None, None

def draw_map(geojson, lat, lon):
    m = folium.Map(zoom_start=13)
    if geojson:
        gj = folium.GeoJson(geojson, name="OSM Polygon")
        gj.add_to(m)
        m.fit_bounds(gj.get_bounds())
    else:
        m.location = [lat, lon]
    folium.Marker([lat, lon], popup="Google Maps 點位").add_to(m)
    return m

st.title("🌍 Polygon 比對工具 v1")

uploaded_file = st.file_uploader("請上傳包含 EngName、Latitude、Longitude 欄位的 CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df = df.dropna(subset=['EngName', 'Latitude', 'Longitude'])

    if 'index' not in st.session_state:
        st.session_state.index = 0
        st.session_state.correct = []
        st.session_state.incorrect = []

    if st.session_state.index < len(df):
        row = df.iloc[st.session_state.index]
        st.subheader(f"🔹 當前地區：{row['EngName']}")

        osm_geojson, display_name = fetch_osm_geojson(row['EngName'])
        if osm_geojson:
            st.markdown(f"**OSM 顯示名稱：** {display_name}")
            google_maps_url = f"https://www.google.com/maps/search/?api=1&query={row['EngName'].replace(' ', '+')}+{row['Latitude']},{row['Longitude']}"
            st.markdown(f"🔗 [在 Google Maps 中檢查新分頁開啟]({google_maps_url})")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🌐 OSM 地圖")
                map_ = draw_map(osm_geojson, row['Latitude'], row['Longitude'])
                st_data = st_folium(map_, width=350, height=400)

            with col2:
                st.markdown("### 🗺️ Google 地圖")
                gmaps_embed_url = f"https://maps.google.com/maps?q={row['Latitude']},{row['Longitude']}&z=13&output=embed"
                components.iframe(gmaps_embed_url, width=350, height=400)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 正確，儲存 GeoJSON"):
                    geojson_data = {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "geometry": osm_geojson,
                                "properties": {
                                    "name": row['EngName'],
                                    "display_name": display_name
                                }
                            }
                        ]
                    }
                    filename = f"{row['EngName'].replace(' ', '_')}.geojson"
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(geojson_data, f, ensure_ascii=False, indent=4)
                    st.success(f"已儲存 {filename}")
                    st.session_state.correct.append(row['EngName'])
                    st.session_state.index += 1
                    st.rerun()

            with col2:
                if st.button("❌ 不一致，加入檢查清單"):
                    st.session_state.incorrect.append(row['EngName'])
                    st.session_state.index += 1
                    st.rerun()
        else:
            st.error("❗ 無法從 OSM 抓到 Polygon，請人工確認")
            if st.button("跳過此筆"):
                st.session_state.incorrect.append(row['EngName'])
                st.session_state.index += 1
                st.rerun()
    else:
        st.success("🎉 全部地區已處理完畢！")
        st.write("✅ 正確清單：", st.session_state.correct)
        st.write("❌ 有問題的清單：", st.session_state.incorrect)
        st.download_button("下載錯誤清單 CSV", pd.DataFrame(st.session_state.incorrect, columns=['EngName']).to_csv(index=False), file_name="需要人工確認.csv")
