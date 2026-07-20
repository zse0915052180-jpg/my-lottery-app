import time
from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# 1. 首頁路由：自動讀取 templates/index.html 並顯示網頁
@app.route('/')
def home():
    return render_template('index.html')

# 2. API 路由：供前端抓取即時與歷史開獎數據
@app.route('/api/get-lottery', methods=['GET'])
def get_lottery():
    # 取得當前毫秒時間戳記，避免 API 被伺服器快取
    timestamp = int(time.time() * 1000)
    
    # API 網址 (加上防快取參數 &t=...)
    latest_url = f"https://api.api68.com/pks/getLotteryPksInfo.do?lotCode=10035&t={timestamp}"
    history_url = f"https://api.api68.com/pks/getPksHistoryList.do?lotCode=10035&t={timestamp}"
    
    # 請求標頭（完整偽裝成真實瀏覽器）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Referer": "https://www.228168d.com/",
        "Origin": "https://www.228168d.com"
    }
    
    try:
        # 步驟 A: 先抓取歷史列表數據
        history_res = requests.get(history_url, headers=headers, timeout=5)
        history_data = history_res.json()
        raw_list = history_data.get("result", {}).get("data", [])
        
        formatted_data = []
        for item in raw_list:
            period = item.get("preDrawIssue") or item.get("period") or ""
            number = item.get("preDrawCode") or item.get("number") or ""
            if number:
                formatted_data.append({"period": str(period), "number": str(number)})
        
        # 步驟 B: 抓取最新一期，若最新一期比歷史列表第一筆還新，則自動置頂插入
        try:
            latest_res = requests.get(latest_url, headers=headers, timeout=4)
            latest_json = latest_res.json()
            latest_item = latest_json.get("result", {}).get("data", {})
            
            latest_period = str(latest_item.get("preDrawIssue", ""))
            latest_number = str(latest_item.get("preDrawCode", ""))
            
            if latest_period and latest_number:
                if not formatted_data or formatted_data[0]["period"] != latest_period:
                    formatted_data.insert(0, {"period": latest_period, "number": latest_number})
        except Exception as e_latest:
            print("即時 API 讀取略過，使用歷史清單：", e_latest)

        return jsonify({
            "errorCode": 0,
            "result": {
                "data": formatted_data
            }
        })
        
    except Exception as e:
        print("連線異常：", e)
        # 網路異常時的備用資料
        return jsonify({
            "errorCode": 0,
            "result": {
                "data": [
                    {"period": "54729032", "number": "06, 04, 10, 02, 08, 09, 07, 03, 05, 01"},
                    {"period": "54729031", "number": "01, 10, 05, 03, 08, 06, 04, 07, 09, 02"}
                ]
            }
        })

if __name__ == '__main__':
    print("🚀 後端伺服器已啟動：http://127.0.0.1:5000")
    # 設定 host='0.0.0.0' 方便本機區域網路連線與部署測試
    app.run(host='0.0.0.0', port=5000, debug=True)