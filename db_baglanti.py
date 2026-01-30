import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# --- AYARLAR ---
SHEET_NAME = "OfisVeritabani"  # Google Drive'daki dosya adınız
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_client():
    """Google API bağlantısını kurar (Hem PC hem Cloud uyumlu)."""
    try:
        # 1. Önce Bilgisayardaki (Local) 'secrets.json' dosyasına bakar
        if os.path.exists("secrets.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", SCOPE)
        # 2. Dosya yoksa Streamlit Cloud (Online) 'Secrets' ayarlarına bakar
        elif "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        else:
            st.error("HATA: 'secrets.json' dosyası bulunamadı! Lütfen Google'dan indirdiğiniz dosyayı proje klasörüne atın.")
            return None
        
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

def veri_cek(sayfa_adi):
    """Google Sheet'ten veriyi okur ve DataFrame'e çevirir."""
    client = get_client()
    if not client: return pd.DataFrame()

    try:
        sheet = client.open(SHEET_NAME).worksheet(sayfa_adi)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Sayısal sütunları (ID gibi) korumak için boş verileri temizle
        if not df.empty and "ID" in df.columns:
            df["ID"] = pd.to_numeric(df["ID"], errors='coerce')
            
        return df
    except Exception as e:
        # Sayfa boşsa veya henüz oluşturulmadıysa boş DataFrame döndürür
        return pd.DataFrame()

def veri_yaz(df, sayfa_adi):
    """DataFrame'i Google Sheet'e yazar."""
    client = get_client()
    if not client: return

    try:
        sheet = client.open(SHEET_NAME).worksheet(sayfa_adi)
        
        # DataFrame'i temizleyelim
        df_clean = df.copy()
        # NaN veya None olan her şeyi boş metne çevir
        df_clean = df_clean.fillna("")
        # Tüm verileri metne (string) çevir (Google'da hata almamak için en güvenli yol)
        df_clean = df_clean.astype(str)

        # Başlıkları ve verileri hazırla
        veriler = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
        
        # Sayfayı temizle ve yeni veriyi yaz
        sheet.clear()
        sheet.update(range_name='A1', values=veriler)
        
    except Exception as e:
        if "200" not in str(e):
            st.error(f"Kayıt Hatası: {e}")