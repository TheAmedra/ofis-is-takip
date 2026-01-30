import streamlit as st
import pandas as pd
import time
import db_baglanti as db  # <--- Yeni bağlantı dosyamız

# Google Sheet'teki sayfa adı
SAYFA_KULLANICILAR = 'kullanicilar'

# Varsayılan ilk kurulum listesi (Tablo boşsa devreye girer)
VARSAYILAN_KULLANICILAR = [
    {"Ad": "Can Okuroğlu", "Rol": "Admin"},
    {"Ad": "Selim Doğan", "Rol": "Personel"},
    {"Ad": "Verda Eskiköy", "Rol": "Muhasebe"},
    {"Ad": "Şahan Eroğlu", "Rol": "Şoför"}
]

def kullanicilari_yukle():
    """Google Sheet'ten kullanıcıları çeker."""
    df = db.veri_cek(SAYFA_KULLANICILAR)
    
    # Eğer tablo boşsa veya yeni oluşturulduysa varsayılanları ekle
    if df.empty:
        df = pd.DataFrame(VARSAYILAN_KULLANICILAR)
        df["ID"] = [int(time.time()) + i for i in range(len(df))]
        kullanici_kaydet(df) # Hemen buluta kaydet
    
    return df

def kullanici_kaydet(df):
    """Google Sheet'e kaydeder."""
    db.veri_yaz(df, SAYFA_KULLANICILAR)

def get_kullanici_listesi_formatli():
    df = kullanicilari_yukle()
    if df.empty: return []
    return [f"{row['Ad']} ({row['Rol']})" for idx, row in df.iterrows()]

def yonetim_sayfasi():
    st.header("👥 Kullanıcı Yönetimi")
    
    # --- YENİ KİŞİ EKLEME ---
    with st.expander("➕ Yeni Personel Ekle", expanded=False):
        with st.form("yeni_kisi_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                ad = st.text_input("Ad Soyad")
            with col2:
                rol = st.selectbox("Departman / Rol", ["Yönetim", "Personel", "Muhasebe", "Şoför", "Depo", "Satış", "Stajyer"])
            
            if st.form_submit_button("Kaydet"):
                if ad:
                    df = kullanicilari_yukle()
                    yeni_kisi = {
                        "Ad": ad,
                        "Rol": rol,
                        "ID": int(time.time())
                    }
                    # concat kullanırken liste içinde DataFrame veriyoruz
                    df = pd.concat([df, pd.DataFrame([yeni_kisi])], ignore_index=True)
                    kullanici_kaydet(df)
                    st.success(f"{ad} eklendi!")
                    time.sleep(1) # Senkronizasyon için minik bekleme
                    st.rerun()

    st.write("---")
    
    # --- LİSTELEME VE SİLME ---
    df = kullanicilari_yukle()
    st.subheader("Mevcut Personel Listesi")
    
    if df.empty:
        st.warning("Kayıtlı personel yok.")
    else:
        for idx, row in df.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 2, 1])
                with c1:
                    st.write(f"👤 **{row['Ad']}**")
                with c2:
                    st.info(f"🏷️ {row['Rol']}")
                with c3:
                    if st.button("Sil", key=f"sil_{row['ID']}"):
                        df = df[df["ID"] != row["ID"]]
                        kullanici_kaydet(df)
                        st.success("Silindi!")
                        time.sleep(1)
                        st.rerun()