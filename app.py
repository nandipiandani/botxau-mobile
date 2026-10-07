import pandas as pd
import pandas_ta as ta
import requests
import streamlit as st
import yfinance as yf

# Konfigurasi Tampilan Web Dashboard
st.set_page_config(
    page_title="XAUUSDm Pro Decision Support", page_icon="🥇", layout="wide"
)

st.title("🥇 XAUUSDm Pro Decision Support (Cloud 24/7)")
st.markdown(
    "Sistem analisis tren multi-timeframe, manajemen risiko **0.01 Lot**, &"
    " Target Detail."
)

# --- KONFIGURASI NOTIFIKASI TELEGRAM (OPSIONAL) ---
# Biar bisa kirim notifikasi ke HP, masukkan Bot Token dan Chat ID Telegram kamu di sini
TELEGRAM_BOT_TOKEN = st.sidebar.text_input(
    "Telegram Bot Token (Opsional)", type="password"
)
TELEGRAM_CHAT_ID = st.sidebar.text_input("Telegram Chat ID (Opsional)")


def send_telegram_alert(message):
  if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
      requests.post(url, json=payload, timeout=5)
    except Exception:
      pass


# Fungsi Ambil Data via yfinance
@st.cache_data(ttl=60)
def fetch_cloud_data(symbol="GC=F", interval="15m", period="5d"):
  data = yf.download(symbol, period=period, interval=interval, progress=False)
  if data.empty:
    return None
  if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
  data = data.reset_index()
  return data


# --- SIDEBAR KONTROL ---
st.sidebar.header("Pengaturan Sinyal")
timeframe_input = st.sidebar.selectbox(
    "Timeframe Eksekusi", ["5m", "15m", "1h"], index=1
)
lot_size = st.sidebar.number_input(
    "Ukuran Lot", value=0.01, step=0.01, format="%.2f"
)

if st.sidebar.button("Perbarui Analisis Pasar", type="primary"):
  st.rerun()

tf_map = {"5m": "5m", "15m": "15m", "1h": "1h"}
yf_interval = tf_map.get(timeframe_input, "15m")

with st.spinner("Menganalisis pasar emas global..."):
  df_exec = fetch_cloud_data("GC=F", interval=yf_interval, period="5d")
  df_macro = fetch_cloud_data("GC=F", interval="1h", period="7d")

  if df_exec is not None and df_macro is not None:
    df_exec["EMA_50"] = ta.ema(df_exec["Close"], length=50)
    df_exec["EMA_200"] = ta.ema(df_exec["Close"], length=200)
    df_exec["RSI"] = ta.rsi(df_exec["Close"], length=14)
    df_exec["ATR"] = ta.atr(
        df_exec["High"], df_exec["Low"], df_exec["Close"], length=14
    )

    df_macro["EMA_200"] = ta.ema(df_macro["Close"], length=200)

    df_exec = df_exec.dropna()
    df_macro = df_macro.dropna()

    if not df_exec.empty and not df_macro.empty:
      last_exec = df_exec.iloc[-1]
      last_macro = df_macro.iloc[-1]

      current_price = float(last_exec["Close"])
      rsi_val = float(last_exec["RSI"])
      atr_val = float(last_exec["ATR"])

      macro_trend = (
          "BULLISH (Naik)"
          if float(last_macro["Close"]) > float(last_macro["EMA_200"])
          else "BEARISH (Turun)"
      )

      # Metrik Utama
      col1, col2 = st.columns(2)
      col1.metric("Harga Emas Terkini", f"${current_price:,.2f}")
      col2.metric("Tren Makro (1H)", macro_trend)

      col3, col4 = st.columns(2)
      col3.metric("RSI (14)", f"{rsi_val:.2f}")
      col4.metric("ATR (Volatilitas)", f"{atr_val:.2f}")

      st.divider()

      st.subheader("💡 Evaluasi Sinyal & Rencana Eksekusi 0.01 Lot")
      is_macro_bullish = float(last_macro["Close"]) > float(
          last_macro["EMA_200"]
      )
      is_macro_bearish = float(last_macro["Close"]) < float(
          last_macro["EMA_200"]
      )

      # Logika Sinyal Buy / Sell dengan Detail Harga Lengkap
      if is_macro_bullish and rsi_val < 40:
        sl_price = current_price - (1.5 * atr_val)
        tp_price = current_price + (2.5 * atr_val)

        st.success("🟢 **PELUANG BUY VALID TERDETEKSI!**")
        st.markdown(f"""
                * **Rekomendasi Aksi:** Buka Posisi **BUY** ({lot_size} Lot)
                * **Harga Entry (Market):** **${current_price:,.2f}**
                * **Stop Loss (SL):** **${sl_price:,.2f}** (Risiko terukur)
                * **Take Profit (TP):** **${tp_price:,.2f}** (Target profit)
                """)

        # Kirim Notifikasi Telegram otomatis (jika token diisi)
        alert_msg = (
            f"🟢 *XAUUSDm BUY SIGNAL*\n- Entry: ${current_price:,.2f}\n- SL:"
            f" ${sl_price:,.2f}\n- TP: ${tp_price:,.2f}"
        )
        send_telegram_alert(alert_msg)

      elif is_macro_bearish and rsi_val > 60:
        sl_price = current_price + (1.5 * atr_val)
        tp_price = current_price - (2.5 * atr_val)

        st.error("🔴 **PELUANG SELL VALID TERDETEKSI!**")
        st.markdown(f"""
                * **Rekomendasi Aksi:** Buka Posisi **SELL** ({lot_size} Lot)
                * **Harga Entry (Market):** **${current_price:,.2f}**
                * **Stop Loss (SL):** **${sl_price:,.2f}** (Risiko terukur)
                * **Take Profit (TP):** **${tp_price:,.2f}** (Target profit)
                """)

        # Kirim Notifikasi Telegram otomatis (jika token diisi)
        alert_msg = (
            f"🔴 *XAUUSDm SELL SIGNAL*\n- Entry: ${current_price:,.2f}\n- SL:"
            f" ${sl_price:,.2f}\n- TP: ${tp_price:,.2f}"
        )
        send_telegram_alert(alert_msg)

      else:
        st.warning(
            "⏳ **WAIT / NO ACTION** (Belum ada konfluensi selaras. Jaga modal"
            " 0.01 lot dan tunggu setup matang)."
        )

      st.divider()
      st.subheader("Grafik Pergerakan")
      chart_data = df_exec.set_index("Datetime")[["Close", "EMA_50", "EMA_200"]]
      st.line_chart(chart_data)

    else:
      st.error("Data indikator tidak mencukupi.")
  else:
    st.error("Gagal menarik data pasar dari server.")