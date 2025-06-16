import streamlit as st
import pandas as pd
import requests
import json
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; YourAppName/1.0)',
    'Referer': 'https://polygonautomation-cm9hhicmdvkxc6maiyqpsp.streamlit.app/'
}

@st.cache_data(show_spinner=False)
def fetch_osm_geojson(query):
    st.error(f"fetch_osm_geojson")
    try:
        url = f"https://nominatim.openstreetmap.org/search?polygon_geojson=1&q={query}&format=json"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # 若非200會丟例外
        data = response.json()
        if data and 'geojson' in data[0]:
            return data[0]['geojson'], data[0].get('display_name', '')
        else:
            return None, None
    except requests.RequestException as e:
        st.error(f"Error fetching data from Nominatim: {e}")
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

uploaded_file = st.file_uploader("請上傳包含 EngName、Latitude、Longitude 欄位的 xlsx", type=["xlsx"])

if uploaded_file:
    # 讀取所有工作表成一個 dict
    sheet_dict = pd.read_excel(uploaded_file, sheet_name=None, engine="openpyxl")

    # 讓使用者用 selectbox 選擇要使用的 Sheet
    sheet_names = list(sheet_dict.keys())
    selected_sheet = st.selectbox("📄 請選擇要載入的工作表", sheet_names)

    # 讀取該 sheet 對應的 DataFrame
    df = sheet_dict[selected_sheet]
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
