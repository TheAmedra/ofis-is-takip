import streamlit as st
import pandas as pd
import db_baglanti as db
import time
import threading

SAYFA_KULLANICILAR = 'kullanicilar'

def veri_getir(): return db.veri_cek(SAYFA_KULLANICILAR)

# --- ARKA PLAN KAYIT ---
def veri_gonder_arkaplan(df):
    try:
        db.veri_yaz(df, SAYFA_KULLANICILAR)
    except Exception as e:
        print(f"Kullanıcı kayıt hatası: {e}")

# --- KULLANICI LİSTESİ (Sidebar için) ---
def get_kullanici_listesi_formatli():
    # Önce Session State'e bak (Anlık sıralama için)
    if 'local_df_kul' in st.session_state and not st.session_state['local_df_kul'].empty:
        df = st.session_state['local_df_kul']
    else:
        df = veri_getir()
        
    # --- HATA ÇÖZÜMÜ: EKSİK SÜTUN KONTROLÜ ---
    # Eğer veri boşsa veya sütunlar eksikse tamamla
    if df.empty:
        return []
    
    gerekli_sutunlar = ["Ad", "Rol", "Durum", "ID", "Sira"]
    for col in gerekli_sutunlar:
        if col not in df.columns:
            df[col] = "" # Eksik sütunu boş olarak ekle
            
    # Sıralama işlemini yap
    if "Sira" in df.columns:
        df["Sira"] = pd.to_numeric(df["Sira"], errors='coerce').fillna(0)
        df = df.sort_values(by="Sira", ascending=False)
    
    k_listesi = []
    for _, row in df.iterrows():
        # "Durum" sütunu artık garanti var, hata vermez.
        if str(row["Durum"]) == "Aktif":
            k_listesi.append(f"{row['Ad']} ({row['Rol']})")
    return k_listesi

# --- YÖNETİM SAYFASI ---
def yonetim_sayfasi():
    st.header("👥 Kullanıcı Yönetimi")
    
    # Veriyi Hafızaya Al
    if 'local_df_kul' not in st.session_state:
        st.session_state['local_df_kul'] = veri_getir()
    
    df = st.session_state['local_df_kul']

    # --- HATA ÇÖZÜMÜ: TABLO BOŞSA SÜTUNLARI OLUŞTUR ---
    gerekli_sutunlar = ["Ad", "Rol", "Durum", "ID", "Sira"]
    if df.empty:
        df = pd.DataFrame(columns=gerekli_sutunlar)
    else:
        # Doluysa ama sütun eksikse ekle
        for col in gerekli_sutunlar:
            if col not in df.columns:
                df[col] = ""

    # Sayısal dönüşüm
    df["Sira"] = pd.to_numeric(df["Sira"], errors='coerce').fillna(0)
    st.session_state['local_df_kul'] = df # Güncellenmiş halini kaydet

    # --- YENİ KULLANICI EKLEME ---
    with st.container(border=True):
        st.subheader("Yeni Kullanıcı Ekle")
        c1, c2, c3 = st.columns([2, 2, 1])
        yeni_ad = c1.text_input("Ad Soyad")
        yeni_rol = c2.selectbox("Rol", ["Personel", "Muhasebe", "Şoför", "Yönetim", "Admin"])
        
        if c3.button("Ekle", use_container_width=True):
            if yeni_ad:
                yeni = {
                    "Ad": yeni_ad, 
                    "Rol": yeni_rol, 
                    "Durum": "Aktif", 
                    "ID": str(int(time.time())),
                    "Sira": int(time.time()) 
                }
                # DataFrame birleştirme
                st.session_state['local_df_kul'] = pd.concat([st.session_state['local_df_kul'], pd.DataFrame([yeni])], ignore_index=True)
                
                # Arka planda kaydet
                thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_kul'],))
                thread.start()
                
                # Cache temizle
                st.cache_data.clear()
                
                st.success(f"{yeni_ad} eklendi!")
                time.sleep(0.5)
                st.rerun()

    st.markdown("---")
    
    # --- LİSTELEME VE SIRALAMA ---
    # Sadece Aktif olanları filtrele ve Sıraya göre diz
    aktif_kullanicilar = st.session_state['local_df_kul'][st.session_state['local_df_kul']["Durum"] == "Aktif"].sort_values(by="Sira", ascending=False)
    
    if aktif_kullanicilar.empty:
        st.info("Henüz ekli personel yok.")
    
    for idx, row in aktif_kullanicilar.iterrows():
        with st.container(border=True):
            c_yon, c_ad, c_rol, c_sil = st.columns([1, 3, 2, 1], vertical_alignment="center")
            
            # 1. OK İŞARETLERİ
            with c_yon:
                y1, y2 = st.columns(2)
                with y1:
                    if st.button("⬆️", key=f"ku_{row['ID']}"):
                        st.session_state['local_df_kul'].loc[st.session_state['local_df_kul']["ID"] == row["ID"], "Sira"] = time.time() + 100
                        thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_kul'],))
                        thread.start()
                        st.cache_data.clear()
                        st.rerun()
                        
                with y2:
                    if st.button("⬇️", key=f"kd_{row['ID']}"):
                        st.session_state['local_df_kul'].loc[st.session_state['local_df_kul']["ID"] == row["ID"], "Sira"] = time.time() - 100
                        thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_kul'],))
                        thread.start()
                        st.cache_data.clear()
                        st.rerun()

            # 2. İSİM
            c_ad.write(f"👤 **{row['Ad']}**")
            
            # 3. ROL
            c_rol.info(f"{row['Rol']}")
            
            # 4. SİL BUTONU
            if c_sil.button("Sil", key=f"ksil_{row['ID']}"):
                st.session_state['local_df_kul'].loc[st.session_state['local_df_kul']["ID"] == row["ID"], "Durum"] = "Silindi"
                thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_kul'],))
                thread.start()
                st.cache_data.clear()
                st.rerun()
