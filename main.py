import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import db_baglanti as db
import kullanicilar_yonetimi as ky 
# Otomatik yenileme kütüphanesini çağırıyoruz
from streamlit_autorefresh import st_autorefresh

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Ofis İş Takip", page_icon="🏢", layout="wide")

# --- OTOMATİK YENİLEME AYARI (GÜNCELLENDİ) ---
# 10 saniye çok agresif olduğu için kotayı doldurdu. 
# Bunu 30 saniye (30000 ms) yapıyoruz. Bu en güvenli sınırdır.
st_autorefresh(interval=30000, limit=None, key="ofis_takip_auto_refresh")

# --- CSS: TASARIM VE MOBİL HİZALAMA ---
st.markdown("""
    <style>
    /* Dosya Yükleyici */
    [data-testid="stFileUploader"] { padding: 0 !important; margin: 0 !important; height: 38px !important; }
    [data-testid="stFileUploaderDropzone"] { min-height: 0px !important; height: 38px !important; border: 1px dashed #aaa !important; background-color: #f9f9f9; display: flex; align-items: center; justify-content: center; }
    [data-testid="stFileUploaderDropzone"]::before { content: '📷 Foto Ekle'; font-size: 13px; font-weight: bold; color: #555;}
    [data-testid="stFileUploaderDropzone"] div div, [data-testid="stFileUploaderDropzone"] span, [data-testid="stFileUploaderDropzone"] small { display: none !important; }
    
    /* YÜKLENEN DOSYA LİSTESİNİ GİZLEME */
    [data-testid="stFileUploader"] ul { display: none !important; }
    [data-testid="stFileUploader"] section { display: none !important; } 
    .uploadedFile { display: none !important; }

    /* Butonlar */
    div.stButton > button { width: 100%; border-radius: 6px; height: 38px; font-weight: bold; padding: 0px !important;}
    
    /* Expander Ayarları */
    .streamlit-expanderHeader { 
        font-size: 13px; color: #333; padding: 0px !important; 
        background-color: transparent !important; border: none !important;
    }
    .streamlit-expanderContent { padding-top: 5px !important; padding-bottom: 5px !important; }

    /* --- MOBİL İÇİN KESİN ÇÖZÜM CSS --- */
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
        div.stButton > button {
            padding-left: 0px !important;
            padding-right: 0px !important;
        }
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

# CACHE AYARI (ÖNEMLİ DEĞİŞİKLİK)
# ttl=30 yaptık. Yani veri 30 saniye boyunca hafızada kalsın, Google'a sormasın.
# 30 saniye dolunca otomatik gidip Google'dan yenisini alacak.
# Bu sayede "clear()" komutuna gerek kalmadan sistem kendini güncelleyecek.
@st.cache_data(ttl=30, show_spinner=False)
def veri_getir(sayfa): 
    return db.veri_cek(sayfa)

def veri_gonder(df, sayfa): 
    db.veri_yaz(df, sayfa)
    # Yazma işlemi yapınca (Ekle/Sil/Düzenle) cache'i temizliyoruz ki değişiklik hemen görünsün.
    veri_getir.clear()
    st.cache_data.clear()

@st.cache_data(ttl=600, show_spinner=False)
def kullanici_listesi_getir():
    return ky.get_kullanici_listesi_formatli()

# --- YAN MENÜ ---
with st.sidebar:
    st.title("🏢 Ofis Takip")
    kullanici_listesi = kullanici_listesi_getir()
    secili_kullanici = st.selectbox("👤 Kullanıcı Seç", ["Seçiniz..."] + kullanici_listesi)
    
    st.markdown("---")
    # Manuel yenileme butonu
    if st.button("🔄 Verileri Yenile", help="Anlık yenile"):
        st.cache_data.clear()
        st.rerun()
    
    st.caption("⏳ Veriler 30 saniyede bir güncellenir.")
        
    st.markdown("---")
    sayfa_secimi = st.radio("Menü", ["İş Panosu", "Kullanıcılar", "Kategoriler", "Çöp Kutusu"])

if secili_kullanici == "Seçiniz...":
    st.warning("Lütfen işlem yapmak için sol menüden isminizi seçin.")
    st.stop()

# --- VERİLERİ YÜKLE ---
# BURADAKİ "veri_getir.clear()" KODUNU KALDIRDIK 🛑
# Artık her 30 saniyede bir @st.cache_data(ttl=30) sayesinde otomatik güncelleyecek.
# Bu sayede kotayı patlatmayacağız.

try:
    df_gorev = veri_getir(SAYFA_GOREVLER)
    df_sekme = veri_getir(SAYFA_SEKMELER)
except Exception as e:
    # Eğer kota hatası verirse kullanıcıya kibarca beklemesini söyleyelim
    st.error("⚠️ Google Hız Sınırı: Sistem çok hızlı yenilendiği için kısa bir mola verdi. 1 dakika içinde düzelecektir.")
    df_gorev = pd.DataFrame(columns=["Gorev","Durum","Aciliyet","Tarih","IslemZamani","ID","Kategori","Atananlar","ResimYolu","Ekleyen","Sira"])
    df_sekme = pd.DataFrame([{"Ad": "GENEL", "Durum": "Aktif", "ID": 1001}])


if df_gorev.empty:
    df_gorev = pd.DataFrame(columns=["Gorev","Durum","Aciliyet","Tarih","IslemZamani","ID","Kategori","Atananlar","ResimYolu","Ekleyen","Sira"])
if "Sira" not in df_gorev.columns: df_gorev["Sira"] = 0

if df_sekme.empty:
    df_sekme = pd.DataFrame([{"Ad": "GENEL", "Durum": "Aktif", "ID": 1001}])
    veri_gonder(df_sekme, SAYFA_SEKMELER)

# --- SAYFA: İŞ PANOSU ---
if sayfa_secimi == "İş Panosu":
    aktif_sekmeler = df_sekme[df_sekme["Durum"] == "Aktif"]["Ad"].tolist()
    sekmeler = st.tabs(aktif_sekmeler)
    
    for i, sekme_adi in enumerate(aktif_sekmeler):
        with sekmeler[i]:
            # --- EKLEME ALANI ---
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 1, 1.2, 2, 1], vertical_alignment="bottom")
                with c1:
                    is_metni = st.text_input("Gorev", key=f"t_{sekme_adi}", placeholder="Görev yaz...", label_visibility="collapsed")
                with c2:
                    resim = st.file_uploader("Resim", type=["jpg","png"], key=f"f_{sekme_adi}", label_visibility="collapsed")
                with c3:
                    aciliyet = st.selectbox("Öncelik", ["NORMAL", "ACİL", "YARIN"], key=f"a_{sekme_adi}", label_visibility="collapsed")
                with c4:
                    kime = st.multiselect("Atanan", kullanici_listesi, default=[], key=f"w_{sekme_adi}", placeholder="Kişi", label_visibility="collapsed")
                with c5:
                    ekle = st.button("EKLE", key=f"b_{sekme_adi}", type="primary")

                if ekle and is_metni:
                    r_yolu = ""
                    if resim:
                        r_ad = f"{int(time.time())}_{resim.name}"
                        r_yolu = os.path.join(KLASOR_RESIMLER, r_ad)
                        with open(r_yolu, "wb") as f: f.write(resim.getbuffer())

                    atanan_str = ", ".join(kime) if kime else "Herkes"
                    yeni = {
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
                    df_gorev = pd.concat([df_gorev, pd.DataFrame([yeni])], ignore_index=True)
                    veri_gonder(df_gorev, SAYFA_GOREVLER)
                    st.toast("✅ Eklendi!"); time.sleep(1); st.rerun()

            st.write("")
            
            # --- LİSTELEME ---
            filtre = (df_gorev["Kategori"] == sekme_adi) & (df_gorev["Durum"] != "Silindi")
            df_gorev["Sira"] = pd.to_numeric(df_gorev["Sira"], errors='coerce').fillna(0)
            isler = df_gorev[filtre].sort_values(by="Sira", ascending=False)

            if isler.empty:
                st.info("📂 İş listesi boş.")
            else:
                for idx, row in isler.iterrows():
                    edit_key = f"edit_mode_{row['ID']}"
                    
                    if st.session_state.get(edit_key, False):
                        # --- DÜZENLEME MODU ---
                        with st.container(border=True):
                            st.caption(f"✏️ Düzenleniyor: {row['Gorev']}")
                            with st.form(key=f"form_edit_{row['ID']}"):
                                c_edit_1, c_edit_2 = st.columns([3, 1])
                                with c_edit_1:
                                    new_gorev = st.text_input("Görev Adı", value=row["Gorev"])
                                with c_edit_2:
                                    new_acil = st.selectbox("Öncelik", ["NORMAL", "ACİL", "YARIN"], index=["NORMAL", "ACİL", "YARIN"].index(row["Aciliyet"]) if row["Aciliyet"] in ["NORMAL", "ACİL", "YARIN"] else 0)
                                
                                st.markdown("---")
                                c_res_1, c_res_2 = st.columns(2)
                                with c_res_1:
                                    if row["ResimYolu"] and row["ResimYolu"] != "nan" and os.path.exists(row["ResimYolu"]):
                                        st.image(row["ResimYolu"], width=100)
                                    else:
                                        st.caption("Resim Yok")
                                    resim_sil = st.checkbox("Mevcut Resmi Sil", key=f"rs_{row['ID']}")
                                
                                with c_res_2:
                                    yeni_resim_yukle = st.file_uploader("Resmi Değiştir", type=["jpg", "png"], key=f"new_img_{row['ID']}")

                                st.markdown("---")
                                c_save, c_cancel = st.columns(2)
                                if c_save.form_submit_button("💾 Kaydet", type="primary"):
                                    df_gorev.loc[df_gorev["ID"] == row["ID"], "Gorev"] = new_gorev
                                    df_gorev.loc[df_gorev["ID"] == row["ID"], "Aciliyet"] = new_acil
                                    if resim_sil:
                                        df_gorev.loc[df_gorev["ID"] == row["ID"], "ResimYolu"] = ""
                                    if yeni_resim_yukle:
                                        r_ad = f"{int(time.time())}_{yeni_resim_yukle.name}"
                                        r_yolu = os.path.join(KLASOR_RESIMLER, r_ad)
                                        with open(r_yolu, "wb") as f: f.write(yeni_resim_yukle.getbuffer())
                                        df_gorev.loc[df_gorev["ID"] == row["ID"], "ResimYolu"] = r_yolu

                                    veri_gonder(df_gorev, SAYFA_GOREVLER)
                                    st.session_state[edit_key] = False
                                    st.rerun()
                                
                                if c_cancel.form_submit_button("İptal"):
                                    st.session_state[edit_key] = False
                                    st.rerun()
                    
                    else:
                        # --- NORMAL GÖRÜNÜM ---
                        bg_col = "white"
                        if row["Durum"] == "Tamamlandı": bg_col = "#eaffea" 
                        elif row["Aciliyet"] == "ACİL": bg_col = "#fffde7" 

                        with st.container(border=True):
                            # MOBİL İÇİN HİZALAMA
                            c_yon, c_icerik, c_btn = st.columns([0.6, 6.4, 1.8], vertical_alignment="center")
                            
                            # 1. YÖN
                            with c_yon:
                                y1, y2 = st.columns(2)
                                with y1:
                                    if st.button("⬆️", key=f"u_{row['ID']}"):
                                        df_gorev.loc[df_gorev["ID"] == row["ID"], "Sira"] = time.time() + 100
                                        veri_gonder(df_gorev, SAYFA_GOREVLER); st.rerun()
                                with y2:
                                    if st.button("⬇️", key=f"d_{row['ID']}"):
                                        df_gorev.loc[df_gorev["ID"] == row["ID"], "Sira"] = time.time() - 100
                                        veri_gonder(df_gorev, SAYFA_GOREVLER); st.rerun()

                            # 2. İÇERİK
                            with c_icerik:
                                stil = f"~~**{row['Gorev']}**~~" if row["Durum"] == "Tamamlandı" else f"**{row['Gorev']}**"
                                st.markdown(stil)
                                if row["ResimYolu"] and row["ResimYolu"] != "nan" and os.path.exists(row["ResimYolu"]):
                                    with st.expander("📷 Fotoğraf"):
                                        st.image(row["ResimYolu"], use_container_width=True)
                                atanan_kisa = isim_sadelestir(row["Atananlar"])
                                ekleyen_kisa = isim_sadelestir(row["Ekleyen"])
                                st.caption(f"📅 {row['Tarih']} | {atanan_kisa}")

                            # 3. BUTONLAR
                            with c_btn:
                                b1, b2, b3 = st.columns(3)
                                with b1:
                                    if row["Durum"] == "Bekliyor":
                                        if st.button("✅", key=f"ok_{row['ID']}", help="Tamamla"):
                                            df_gorev.loc[df_gorev["ID"] == row["ID"], "Durum"] = "Tamamlandı"
                                            veri_gonder(df_gorev, SAYFA_GOREVLER); st.rerun()
                                    else:
                                        if st.button("↩️", key=f"back_{row['ID']}", help="Geri Al"):
                                            df_gorev.loc[df_gorev["ID"] == row["ID"], "Durum"] = "Bekliyor"
                                            veri_gonder(df_gorev, SAYFA_GOREVLER); st.rerun()
                                with b2:
                                    if st.button("❌", key=f"del_{row['ID']}", help="Sil"):
                                        df_gorev.loc[df_gorev["ID"] == row["ID"], "Durum"] = "Silindi"
                                        veri_gonder(df_gorev, SAYFA_GOREVLER); st.rerun()
                                with b3:
                                    if st.button("✏️", key=f"ed_btn_{row['ID']}", help="Düzenle"):
                                        st.session_state[edit_key] = True
                                        st.rerun()

# --- DİĞER SAYFALAR ---
elif sayfa_secimi == "Kullanıcılar":
    ky.yonetim_sayfasi()

elif sayfa_secimi == "Kategoriler":
    st.header("📂 Kategoriler")
    with st.form("k_form"):
        yeni_kat = st.text_input("Kategori Adı")
        if st.form_submit_button("Ekle"):
            df_sekme = pd.concat([df_sekme, pd.DataFrame([{"Ad":yeni_kat.upper(), "Durum":"Aktif", "ID":int(time.time())}])], ignore_index=True)
            veri_gonder(df_sekme, SAYFA_SEKMELER); st.rerun()
    for idx, row in df_sekme[df_sekme["Durum"]=="Aktif"].iterrows():
        c1, c2 = st.columns([4,1])
        c1.write(f"📂 {row['Ad']}")
        if c2.button("Sil", key=f"ks_{row['ID']}"):
            df_sekme.loc[df_sekme["ID"]==row["ID"], "Durum"]="Silindi"
            veri_gonder(df_sekme, SAYFA_SEKMELER); st.rerun()

elif sayfa_secimi == "Çöp Kutusu":
    st.title("🗑️ Çöp Kutusu")
    if st.button("🔥 Hepsini Kalıcı Sil"):
        df_gorev = df_gorev[df_gorev["Durum"]!="Silindi"]
        veri_gonder(df_gorev, SAYFA_GOREVLER); st.rerun()
    silinenler = df_gorev[df_gorev["Durum"]=="Silindi"]
    for idx, row in silinenler.iterrows():
        c1, c2 = st.columns([4,1])
        c1.write(f"❌ {row['Gorev']}")
        if c2.button("Geri Al", key=f"r_{row['ID']}"):
            df_gorev.loc[df_gorev["ID"]==row["ID"], "Durum"]="Bekliyor"
            veri_gonder(df_gorev, SAYFA_GOREVLER); st.rerun()
