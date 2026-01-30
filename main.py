import streamlit as st
import pandas as pd
import os
import time
import threading # Arka plan işlemleri için kütüphane
from datetime import datetime
import db_baglanti as db
import kullanicilar_yonetimi as ky 
from streamlit_autorefresh import st_autorefresh

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Ofis İş Takip", page_icon="🏢", layout="wide")

# --- OTOMATİK YENİLEME (60 SANİYE) ---
# Arka planda veriler işlendiği için burayı sıkıştırmaya gerek yok.
st_autorefresh(interval=60000, limit=None, key="ofis_takip_auto_refresh")

# --- CSS: TASARIM ---
st.markdown("""
    <style>
    [data-testid="stStatusWidget"] { visibility: hidden; height: 0%; position: fixed; }
    .stApp { opacity: 1 !important; }
    .element-container { opacity: 1 !important; }
    div[data-stale="true"] { opacity: 1 !important; }
    
    [data-testid="stFileUploader"] { padding: 0 !important; margin: 0 !important; height: 38px !important; }
    [data-testid="stFileUploaderDropzone"] { min-height: 0px !important; height: 38px !important; border: 1px dashed #aaa !important; background-color: #f9f9f9; display: flex; align-items: center; justify-content: center; }
    [data-testid="stFileUploaderDropzone"]::before { content: '📷 Foto Ekle'; font-size: 13px; font-weight: bold; color: #555;}
    [data-testid="stFileUploaderDropzone"] div div, [data-testid="stFileUploaderDropzone"] span, [data-testid="stFileUploaderDropzone"] small { display: none !important; }
    [data-testid="stFileUploader"] ul { display: none !important; }
    [data-testid="stFileUploader"] section { display: none !important; } 
    .uploadedFile { display: none !important; }

    div.stButton > button { width: 100%; border-radius: 6px; height: 38px; font-weight: bold; padding: 0px !important;}
    
    .streamlit-expanderHeader { 
        font-size: 13px; color: #333; padding: 0px !important; 
        background-color: transparent !important; border: none !important;
    }
    .streamlit-expanderContent { padding-top: 5px !important; padding-bottom: 5px !important; }

    @media (max-width: 768px) {
        [data-testid="column"] [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
        }
        [data-testid="column"] [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            width: auto !important;
            flex: 1 1 auto !important;
            min-width: 0px !important;
        }
        div.stButton > button { padding-left: 0px !important; padding-right: 0px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- AYARLAR ---
SAYFA_GOREVLER = 'gorevler'
SAYFA_SEKMELER = 'sekmeler'
KLASOR_RESIMLER = "uploads"
if not os.path.exists(KLASOR_RESIMLER): os.makedirs(KLASOR_RESIMLER)

# --- YARDIMCI FONKSİYONLAR ---
def isim_sadelestir(metin):
    if not isinstance(metin, str) or metin == "": return ""
    temiz_isimler = []
    kisiler = metin.split(",") 
    for kisi in kisiler:
        kisi_no_rol = kisi.split("(")[0].strip()
        ilk_isim = kisi_no_rol.split(" ")[0]
        temiz_isimler.append(ilk_isim)
    return ", ".join(temiz_isimler)

# --- GOOGLE İŞLEMLERİ (ARKA PLAN) ---
# Bu fonksiyon normal çalışıyor ama biz bunu Thread içinde çağıracağız.
def veri_gonder_arkaplan(df, sayfa):
    try:
        db.veri_yaz(df, sayfa)
    except Exception as e:
        print(f"Arka plan kayıt hatası: {e}") 
        # Arka planda hata olsa bile kullanıcıya yansıtma, bir sonraki seferde düzelir.

# Verileri Google'dan çeken ana fonksiyon
@st.cache_data(ttl=60, show_spinner=False)
def veri_getir_google(sayfa):
    return db.veri_cek(sayfa)

@st.cache_data(ttl=600, show_spinner=False)
def kullanici_listesi_getir():
    return ky.get_kullanici_listesi_formatli()

# --- YAN MENÜ ---
with st.sidebar:
    st.title("🏢 Ofis Takip")
    kullanici_listesi = kullanici_listesi_getir()
    secili_kullanici = st.selectbox("👤 Kullanıcı Seç", ["Seçiniz..."] + kullanici_listesi)
    
    st.markdown("---")
    if st.button("🔄 Verileri Yenile", help="Google'dan en güncel veriyi çeker"):
        st.cache_data.clear()
        if 'local_df_gorev' in st.session_state:
            del st.session_state['local_df_gorev'] # Yerel hafızayı da sıfırla
        st.rerun()
    
    st.markdown("---")
    sayfa_secimi = st.radio("Menü", ["İş Panosu", "Kullanıcılar", "Kategoriler", "Çöp Kutusu"])

if secili_kullanici == "Seçiniz...":
    st.warning("Lütfen işlem yapmak için sol menüden isminizi seçin.")
    st.stop()

# --- VERİ YÖNETİMİ (HIZLANDIRILMIŞ) ---
# Mantık şu: Google'dan bir kere çek, Session State'e at.
# Tüm ekleme/silme işlemlerini Session State üzerinde yap (ANLIK HIZ).
# Sonra Session State'in kopyasını arka planda Google'a gönder.

# 1. Görevler Tablosu Hazırlığı
if 'local_df_gorev' not in st.session_state:
    # İlk açılışta veya yenilemede Google'dan çek
    try:
        st.session_state['local_df_gorev'] = veri_getir_google(SAYFA_GOREVLER)
    except:
        st.session_state['local_df_gorev'] = pd.DataFrame(columns=["Gorev","Durum","Aciliyet","Tarih","IslemZamani","ID","Kategori","Atananlar","ResimYolu","Ekleyen","Sira"])

# 2. Sekmeler Tablosu Hazırlığı
if 'local_df_sekme' not in st.session_state:
    try:
        st.session_state['local_df_sekme'] = veri_getir_google(SAYFA_SEKMELER)
    except:
         st.session_state['local_df_sekme'] = pd.DataFrame([{"Ad": "GENEL", "Durum": "Aktif", "ID": 1001}])

# Kısa isimler atayalım
df_gorev = st.session_state['local_df_gorev']
df_sekme = st.session_state['local_df_sekme']

# Boş veri kontrolü ve onarımı
if df_gorev.empty and "Gorev" not in df_gorev.columns:
    df_gorev = pd.DataFrame(columns=["Gorev","Durum","Aciliyet","Tarih","IslemZamani","ID","Kategori","Atananlar","ResimYolu","Ekleyen","Sira"])
if "Sira" not in df_gorev.columns: df_gorev["Sira"] = 0

if df_sekme.empty:
    df_sekme = pd.DataFrame([{"Ad": "GENEL", "Durum": "Aktif", "ID": 1001}])

# --- SAYFA: İŞ PANOSU ---
if sayfa_secimi == "İş Panosu":
    aktif_sekmeler = df_sekme[df_sekme["Durum"] == "Aktif"]["Ad"].tolist()
    sekmeler = st.tabs(aktif_sekmeler)
    
    for i, sekme_adi in enumerate(aktif_sekmeler):
        with sekmeler[i]:
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 1, 1.2, 2, 1], vertical_alignment="bottom")
                with c1: is_metni = st.text_input("Gorev", key=f"t_{sekme_adi}", placeholder="Görev yaz...", label_visibility="collapsed")
                with c2: resim = st.file_uploader("Resim", type=["jpg","png"], key=f"f_{sekme_adi}", label_visibility="collapsed")
                with c3: aciliyet = st.selectbox("Öncelik", ["NORMAL", "ACİL", "YARIN"], key=f"a_{sekme_adi}", label_visibility="collapsed")
                with c4: kime = st.multiselect("Atanan", kullanici_listesi, default=[], key=f"w_{sekme_adi}", placeholder="Kişi", label_visibility="collapsed")
                with c5: ekle = st.button("EKLE", key=f"b_{sekme_adi}", type="primary")

                if ekle and is_metni:
                    # 1. Resmi hemen kaydet (Lokal)
                    r_yolu = ""
                    if resim:
                        r_ad = f"{int(time.time())}_{resim.name}"
                        r_yolu = os.path.join(KLASOR_RESIMLER, r_ad)
                        with open(r_yolu, "wb") as f: f.write(resim.getbuffer())

                    # 2. Yeni satırı oluştur
                    atanan_str = ", ".join(kime) if kime else "Herkes"
                    yeni_veri = {
                        "Gorev": str(is_metni),
                        "Durum": "Bekliyor",
                        "Aciliyet": str(aciliyet),
                        "Tarih": datetime.now().strftime("%d-%m %H:%M"),
                        "IslemZamani": time.time(),
                        "ID": str(int(time.time() * 1000)),
                        "Kategori": str(sekme_adi),
                        "Atananlar": atanan_str,
                        "ResimYolu": str(r_yolu),
                        "Ekleyen": str(secili_kullanici),
                        "Sira": int(time.time())
                    }
                    
                    # 3. ANINDA GÜNCELLEME (Local Session State)
                    st.session_state['local_df_gorev'] = pd.concat([st.session_state['local_df_gorev'], pd.DataFrame([yeni_veri])], ignore_index=True)
                    
                    # 4. ARKA PLANDA GOOGLE'A GÖNDER (Threading)
                    # Kullanıcı bunu beklemez, işlem arkada devam eder.
                    thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_gorev'], SAYFA_GOREVLER))
                    thread.start()
                    
                    # 5. Sayfayı yenile (Anlık tepki için)
                    st.toast("🚀 Hızlıca eklendi!")
                    time.sleep(0.1) 
                    st.rerun()

            st.write("")
            
            # Tabloyu Session State'den (Hafızadan) okuduğumuz için şimşek hızında gelir
            filtre = (st.session_state['local_df_gorev']["Kategori"] == sekme_adi) & (st.session_state['local_df_gorev']["Durum"] != "Silindi")
            st.session_state['local_df_gorev']["Sira"] = pd.to_numeric(st.session_state['local_df_gorev']["Sira"], errors='coerce').fillna(0)
            isler = st.session_state['local_df_gorev'][filtre].sort_values(by="Sira", ascending=False)

            if isler.empty:
                st.info("📂 İş listesi boş.")
            else:
                for idx, row in isler.iterrows():
                    edit_key = f"edit_mode_{row['ID']}"
                    
                    if st.session_state.get(edit_key, False):
                        with st.container(border=True):
                            st.caption(f"✏️ Düzenleniyor: {row['Gorev']}")
                            with st.form(key=f"form_edit_{row['ID']}"):
                                c_edit_1, c_edit_2 = st.columns([3, 1])
                                with c_edit_1: new_gorev = st.text_input("Görev Adı", value=row["Gorev"])
                                with c_edit_2: new_acil = st.selectbox("Öncelik", ["NORMAL", "ACİL", "YARIN"], index=["NORMAL", "ACİL", "YARIN"].index(row["Aciliyet"]) if row["Aciliyet"] in ["NORMAL", "ACİL", "YARIN"] else 0)
                                
                                st.markdown("---")
                                c_res_1, c_res_2 = st.columns(2)
                                with c_res_1:
                                    if row["ResimYolu"] and row["ResimYolu"] != "nan" and os.path.exists(row["ResimYolu"]):
                                        st.image(row["ResimYolu"], width=100)
                                    resim_sil = st.checkbox("Mevcut Resmi Sil", key=f"rs_{row['ID']}")
                                with c_res_2:
                                    yeni_resim_yukle = st.file_uploader("Resmi Değiştir", type=["jpg", "png"], key=f"new_img_{row['ID']}")

                                st.markdown("---")
                                c_save, c_cancel = st.columns(2)
                                if c_save.form_submit_button("💾 Kaydet", type="primary"):
                                    # Önce Hafızayı Güncelle
                                    mask = st.session_state['local_df_gorev']["ID"] == row["ID"]
                                    st.session_state['local_df_gorev'].loc[mask, "Gorev"] = new_gorev
                                    st.session_state['local_df_gorev'].loc[mask, "Aciliyet"] = new_acil
                                    
                                    if resim_sil: st.session_state['local_df_gorev'].loc[mask, "ResimYolu"] = ""
                                    if yeni_resim_yukle:
                                        r_ad = f"{int(time.time())}_{yeni_resim_yukle.name}"
                                        r_yolu = os.path.join(KLASOR_RESIMLER, r_ad)
                                        with open(r_yolu, "wb") as f: f.write(yeni_resim_yukle.getbuffer())
                                        st.session_state['local_df_gorev'].loc[mask, "ResimYolu"] = r_yolu
                                    
                                    # Arkada Gönder
                                    thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_gorev'], SAYFA_GOREVLER))
                                    thread.start()
                                    
                                    st.session_state[edit_key] = False
                                    st.rerun()
                                if c_cancel.form_submit_button("İptal"):
                                    st.session_state[edit_key] = False
                                    st.rerun()
                    else:
                        with st.container(border=True):
                            c_yon, c_icerik, c_btn = st.columns([0.6, 6.4, 1.8], vertical_alignment="center")
                            with c_yon:
                                y1, y2 = st.columns(2)
                                with y1:
                                    if st.button("⬆️", key=f"u_{row['ID']}"):
                                        st.session_state['local_df_gorev'].loc[st.session_state['local_df_gorev']["ID"] == row["ID"], "Sira"] = time.time() + 100
                                        thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_gorev'], SAYFA_GOREVLER))
                                        thread.start()
                                        st.rerun()
                                with y2:
                                    if st.button("⬇️", key=f"d_{row['ID']}"):
                                        st.session_state['local_df_gorev'].loc[st.session_state['local_df_gorev']["ID"] == row["ID"], "Sira"] = time.time() - 100
                                        thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_gorev'], SAYFA_GOREVLER))
                                        thread.start()
                                        st.rerun()

                            with c_icerik:
                                stil = f"~~**{row['Gorev']}**~~" if row["Durum"] == "Tamamlandı" else f"**{row['Gorev']}**"
                                st.markdown(stil)
                                if row["ResimYolu"] and row["ResimYolu"] != "nan" and os.path.exists(row["ResimYolu"]):
                                    with st.expander("📷 Fotoğraf"): st.image(row["ResimYolu"], use_container_width=True)
                                st.caption(f"📅 {row['Tarih']} | {isim_sadelestir(row['Atananlar'])}")

                            with c_btn:
                                b1, b2, b3 = st.columns(3)
                                with b1:
                                    if row["Durum"] == "Bekliyor":
                                        if st.button("✅", key=f"ok_{row['ID']}", help="Tamamla"):
                                            # Hafızada anında güncelle
                                            st.session_state['local_df_gorev'].loc[st.session_state['local_df_gorev']["ID"] == row["ID"], "Durum"] = "Tamamlandı"
                                            # Arka planda gönder
                                            thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_gorev'], SAYFA_GOREVLER))
                                            thread.start()
                                            st.rerun()
                                    else:
                                        if st.button("↩️", key=f"back_{row['ID']}", help="Geri Al"):
                                            st.session_state['local_df_gorev'].loc[st.session_state['local_df_gorev']["ID"] == row["ID"], "Durum"] = "Bekliyor"
                                            thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_gorev'], SAYFA_GOREVLER))
                                            thread.start()
                                            st.rerun()
                                with b2:
                                    if st.button("❌", key=f"del_{row['ID']}", help="Sil"):
                                        st.session_state['local_df_gorev'].loc[st.session_state['local_df_gorev']["ID"] == row["ID"], "Durum"] = "Silindi"
                                        thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_gorev'], SAYFA_GOREVLER))
                                        thread.start()
                                        st.rerun()
                                with b3:
                                    if st.button("✏️", key=f"ed_btn_{row['ID']}", help="Düzenle"):
                                        st.session_state[edit_key] = True
                                        st.rerun()

# --- DİĞER SAYFALAR ---
elif sayfa_secimi == "Kullanıcılar": ky.yonetim_sayfasi()
elif sayfa_secimi == "Kategoriler":
    st.header("📂 Kategoriler")
    with st.form("k_form"):
        yeni_kat = st.text_input("Kategori Adı")
        if st.form_submit_button("Ekle"):
            st.session_state['local_df_sekme'] = pd.concat([st.session_state['local_df_sekme'], pd.DataFrame([{"Ad":yeni_kat.upper(), "Durum":"Aktif", "ID":int(time.time())}])], ignore_index=True)
            thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_sekme'], SAYFA_SEKMELER))
            thread.start()
            st.rerun()
    for idx, row in df_sekme[df_sekme["Durum"]=="Aktif"].iterrows():
        c1, c2 = st.columns([4,1])
        c1.write(f"📂 {row['Ad']}")
        if c2.button("Sil", key=f"ks_{row['ID']}"):
            st.session_state['local_df_sekme'].loc[st.session_state['local_df_sekme']["ID"] == row["ID"], "Durum"] = "Silindi"
            thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_sekme'], SAYFA_SEKMELER))
            thread.start()
            st.rerun()
elif sayfa_secimi == "Çöp Kutusu":
    st.title("🗑️ Çöp Kutusu")
    if st.button("🔥 Hepsini Kalıcı Sil"):
        # Hafızada temizle
        st.session_state['local_df_gorev'] = st.session_state['local_df_gorev'][st.session_state['local_df_gorev']["Durum"] != "Silindi"]
        # Arkada gönder
        thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_gorev'], SAYFA_GOREVLER))
        thread.start()
        st.rerun()
        
    silinenler = df_gorev[df_gorev["Durum"]=="Silindi"]
    for idx, row in silinenler.iterrows():
        c1, c2 = st.columns([4,1])
        c1.write(f"❌ {row['Gorev']}")
        if c2.button("Geri Al", key=f"r_{row['ID']}"):
            st.session_state['local_df_gorev'].loc[st.session_state['local_df_gorev']["ID"] == row["ID"], "Durum"] = "Bekliyor"
            thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_gorev'], SAYFA_GOREVLER))
            thread.start()
            st.rerun()
