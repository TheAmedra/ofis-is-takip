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
        
    if df.empty: return []
    
    if "Sira" not in df.columns:
        df["Sira"] = 0
    
    # Sıralama işlemini yap (Sayıya çevir ve sırala)
    df["Sira"] = pd.to_numeric(df["Sira"], errors='coerce').fillna(0)
    df = df.sort_values(by="Sira", ascending=False)
    
    k_listesi = []
    for _, row in df.iterrows():
        if row["Durum"] == "Aktif":
            k_listesi.append(f"{row['Ad']} ({row['Rol']})")
    return k_listesi

# --- YÖNETİM SAYFASI ---
def yonetim_sayfasi():
    st.header("👥 Kullanıcı Yönetimi")
    
    # Veriyi Hafızaya Al (Optimistic UI)
    if 'local_df_kul' not in st.session_state:
        st.session_state['local_df_kul'] = veri_getir()
    
    df = st.session_state['local_df_kul']

    if df.empty:
        df = pd.DataFrame(columns=["Ad", "Rol", "Durum", "ID", "Sira"])
    
    if "Sira" not in df.columns: df["Sira"] = 0

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
                    "Sira": int(time.time()) # En üste ekle
                }
                st.session_state['local_df_kul'] = pd.concat([df, pd.DataFrame([yeni])], ignore_index=True)
                
                # Arka planda kaydet
                thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_kul'],))
                thread.start()
                
                # Cache temizle ki Sidebar güncellensin
                st.cache_data.clear()
                
                st.success(f"{yeni_ad} eklendi!")
                time.sleep(0.5)
                st.rerun()

    st.markdown("---")
    
    # --- LİSTELEME VE SIRALAMA ---
    st.session_state['local_df_kul']["Sira"] = pd.to_numeric(st.session_state['local_df_kul']["Sira"], errors='coerce').fillna(0)
    
    # Aktif kullanıcıları çek ve SIRA'ya göre diz
    aktif_kullanicilar = st.session_state['local_df_kul'][st.session_state['local_df_kul']["Durum"] == "Aktif"].sort_values(by="Sira", ascending=False)
    
    for idx, row in aktif_kullanicilar.iterrows():
        with st.container(border=True):
            # Mobilde de güzel gözüksün diye oranlar: [Oklar, İsim, Rol, Sil]
            c_yon, c_ad, c_rol, c_sil = st.columns([1, 3, 2, 1], vertical_alignment="center")
            
            # 1. OK İŞARETLERİ
            with c_yon:
                y1, y2 = st.columns(2)
                with y1:
                    # YUKARI TAŞIMA
                    if st.button("⬆️", key=f"ku_{row['ID']}"):
                        st.session_state['local_df_kul'].loc[st.session_state['local_df_kul']["ID"] == row["ID"], "Sira"] = time.time() + 100
                        
                        # Arka planda kaydet
                        thread = threading.Thread(target=veri_gonder_arkaplan, args=(st.session_state['local_df_kul'],))
                        thread.start()
                        
                        # Sidebar listesini güncellemek için cache temizle
                        st.cache_data.clear()
                        st.rerun()
                        
                with y2:
                    # AŞAĞI TAŞIMA
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
