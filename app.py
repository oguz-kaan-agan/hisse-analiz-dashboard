import matplotlib
matplotlib.use('Agg')

from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        ticker = request.form.get("ticker", "AAPL").upper()
        rsi_period = int(request.form.get("rsi_period", 14))
        ma1_period = int(request.form.get("ma1_period", 20))
        ma2_period = int(request.form.get("ma2_period", 50))
        
        try:
            # 6 aylık veri çek
            df = yf.download(ticker, period="6mo", progress=False)
            if df.empty:
                return render_template("index.html", error="Hisse verisi bulunamadı.")

            # Close kolonunu güvenli şekilde al
            if 'Close' in df.columns:
                close_col = df['Close']
            else:
                # yfinance MultiIndex dönebiliyor, ilk seviyede 'Close' olanı bul
                close_col = df.iloc[:, df.columns.get_level_values(0) == 'Close']

            # Eğer close_col MultiIndex ise veya DataFrame ise bir şekilde Series'e çevir
            if isinstance(close_col, pd.DataFrame):
                close_col = close_col.iloc[:, 0]

            # MA Hesaplamaları
            df["MA1"] = close_col.rolling(window=ma1_period).mean()
            df["MA2"] = close_col.rolling(window=ma2_period).mean()
            
            # RSI Hesaplama
            delta = close_col.diff()
            gain = delta.where(delta > 0, 0.0).rolling(window=rsi_period).mean()
            loss = -delta.where(delta < 0, 0.0).rolling(window=rsi_period).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))
            
            # Son Değerleri Al
            try:
                son_fiyat = float(close_col.iloc[-1].item())
            except AttributeError:
                son_fiyat = float(close_col.iloc[-1])

            try:
                son_rsi = float(df["RSI"].iloc[-1].item())
            except AttributeError:
                son_rsi = float(df["RSI"].iloc[-1])

            # Sinyal Üretimi
            if son_rsi < 30:
                signal = "AŞIRI SATILMIŞ 📈"
            elif son_rsi > 70:
                signal = "AŞIRI ALINMIŞ 📉"
            else:
                signal = "NÖTR ➡️"
                
            # Grafik Oluşturma
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})
            fig.patch.set_facecolor('#0d1117')
            ax1.set_facecolor('#161b22')
            ax2.set_facecolor('#161b22')
            
            # Üst Grafik (Fiyat ve MA'lar)
            ax1.plot(df.index, close_col, label='Fiyat', color='#e6edf3')
            ax1.plot(df.index, df["MA1"], label=f'MA {ma1_period}', color='#00aaff')
            ax1.plot(df.index, df["MA2"], label=f'MA {ma2_period}', color='#00ff88')
            ax1.set_title(f"{ticker} Fiyat Grafiği", color='#e6edf3')
            ax1.tick_params(colors='#e6edf3')
            ax1.legend()
            ax1.grid(color='#30363d', linestyle='--', alpha=0.5)
            
            # Alt Grafik (RSI)
            ax2.plot(df.index, df["RSI"], color='#00ff88')
            ax2.axhline(70, color='red', linestyle='--', alpha=0.7)
            ax2.axhline(30, color='green', linestyle='--', alpha=0.7)
            ax2.set_title("RSI", color='#e6edf3')
            ax2.tick_params(colors='#e6edf3')
            ax2.grid(color='#30363d', linestyle='--', alpha=0.5)
            
            plt.tight_layout()
            
            # Grafiği base64 string'e çevir
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close()
            
            return render_template("index.html", 
                                   ticker=ticker, 
                                   son_fiyat=son_fiyat, 
                                   son_rsi=son_rsi, 
                                   signal=signal, 
                                   grafik=plot_base64,
                                   rsi_period=rsi_period,
                                   ma1_period=ma1_period,
                                   ma2_period=ma2_period)
            
        except Exception as e:
            return render_template("index.html", error=f"Hata oluştu: {str(e)}")
            
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=False, threaded=True)
