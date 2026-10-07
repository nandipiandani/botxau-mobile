import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
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
TELEGRAM_BOT_TOKEN = st.sidebar.text_input(
    "Telegram Bot Token (Opsional)", type="password"
)
TELEGRAM_CHAT_ID = st.sidebar.text_input("Telegram Chat ID (Opsional)")


def send_telegram_alert(message):
  if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    import requests

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


# --- SIDEBAR KONTROL & COUNTDOWN TIMER AUTO-REFRESH ---
st.sidebar.header("Pengaturan Sinyal")
timeframe_input = st.sidebar.selectbox(
    "Timeframe Eksekusi", ["1m", "5m", "15m", "1h"], index=2
)
lot_size = st.sidebar.number_input(
    "Ukuran Lot", value=0.01, step=0.01, format="%.2f"
)

auto_refresh = st.sidebar.checkbox(
    "Aktifkan Auto-Refresh (Setiap 2 Menit)", value=True
)

if auto_refresh:
  # Komponen JavaScript untuk Countdown Timer yang berjalan nyata di sidebar
  countdown_html = """
    <div style="font-family: sans-serif; font-size: 14px; color: #31333F; background-color: #F0F2F6; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
        🔄 Refresh otomatis dalam: <span id="timer" style="font-weight: bold; color: #FF4B4B;">120</span> detik
    </div>
    <script>
        var timeLeft = 120;
        var timerId = setInterval(function() {
            if(timeLeft <= 0) {
                clearInterval(timerId);
                location.reload();
            } else {
                document.getElementById('timer').innerHTML = timeLeft;
                timeLeft -= 1;
            }
        }, 1000);
    </script>
    """
  components.html(countdown_html, height=50)

if st.sidebar.button("Perbarui Analisis Pasar Sekarang", type="primary"):
  st.rerun()


# Fungsi Ambil Data Presisi Tinggi
@st.cache_data(ttl=30)
def fetch_cloud_data(symbol="GC=F", interval="15m", period="2d"):
  data = yf.download(symbol, period=period, interval=interval, progress=False)
  if data.empty:
    return None
  if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
  data = data.reset_index()
  return data


with st.spinner("Menarik data pasar emas global terbaru..."):
  df_exec = fetch_cloud_data("GC=F", interval=timeframe_input, period="2d")
  df_macro = fetch_cloud_data("GC=F", interval="1h", period="5d")

  if df_exec is not None and df_macro is not None:
    # Perhitungan Indikator Teknikal Manual
    df_exec["EMA_50"] = df_exec["Close"].ewm(span=50, adjust=False).mean()
    df_exec["EMA_200"] = df_exec["Close"].ewm(span=200, adjust=False).mean()

    delta = df_exec["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df_exec["RSI"] = 100 - (100 / (1 + rs))

    high_low = df_exec["High"] - df_exec["Low"]
    high_close = (df_exec["High"] - df_exec["Close"].shift()).abs()
    low_close = (df_exec["Low"] - df_exec["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df_exec["ATR"] = tr.rolling(window=14).mean()

    df_macro["EMA_200"] = df_macro["Close"].ewm(span=200, adjust=False).mean()

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

      # Logika Sinyal Buy / Sell
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
