import os
import time
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import requests

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/get-lottery', methods=['GET'])
def get_lottery():
    lot_code = request.args.get('lotCode', '10035')
    timestamp = int(time.time() * 1000)
    
    history_url = f"https://api.api68.com/pks/getPksHistoryList.do?lotCode={lot_code}&t={timestamp}"
    latest_url = f"https://api.api68.com/pks/getLotteryPksInfo.do?lotCode={lot_code}&t={timestamp}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Referer": "https://www.228168d.com/",
        "Origin": "https://www.228168d.com"
    }
    
    formatted_data = []
    rem_seconds = None  # 伺服器直接計算出的精準剩餘秒數

    # 1. 抓取歷史列表
    try:
        history_res = requests.get(history_url, headers=headers, timeout=8)
        if history_res.status_code == 200:
            history_data = history_res.json()
            raw_list = history_data.get("result", {}).get("data", [])
            for item in raw_list:
                period = item.get("preDrawIssue") or item.get("period") or ""
                number = item.get("preDrawCode") or item.get("number") or ""
                if number:
                    formatted_data.append({"period": str(period), "number": str(number)})
    except Exception as e_hist:
        print(f"[{lot_code}] 歷史 API 失敗：", e_hist)

    # 2. 抓取最新一期與精準開獎剩餘秒數
    try:
        latest_res = requests.get(latest_url, headers=headers, timeout=5)
        if latest_res.status_code == 200:
            latest_json = latest_res.json()
            latest_item = latest_json.get("result", {}).get("data", {})
            
            latest_period = str(latest_item.get("preDrawIssue", ""))
            latest_number = str(latest_item.get("preDrawCode", ""))
            
            # 多重兼容抓取下期開獎時間欄位
            draw_time_str = latest_item.get("drawTime") or latest_item.get("drawDate") or latest_item.get("nextDrawTime") or ""
            
            if draw_time_str:
                try:
                    # 解析開獎時間並計算相差秒數
                    target_dt = datetime.strptime(draw_time_str, "%Y-%m-%d %H:%M:%S")
                    now_dt = datetime.now()
                    diff = (target_dt - now_dt).total_seconds()
                    rem_seconds = int(diff)
                except Exception as e_parse:
                    print(f"[{lot_code}] 時間解析失敗：", e_parse)

            if latest_period and latest_number and formatted_data:
                if formatted_data[0]["period"] != latest_period:
                    formatted_data.insert(0, {"period": latest_period, "number": latest_number})
    except Exception as e_latest:
        print(f"[{lot_code}] 即時 API 略過：", e_latest)

    return jsonify({
        "errorCode": 0,
        "remSeconds": rem_seconds,  # 精準秒數直接交給前端
        "result": {
            "data": formatted_data
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
