import os
import time
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import requests

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
CORS(app)

# 定義北京/台灣時區 (UTC+8)
CST_TZ = timezone(timedelta(hours=8))

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
    rem_seconds = None

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

    # 2. 抓取最新一期與精準開獎倒數秒數
    try:
        latest_res = requests.get(latest_url, headers=headers, timeout=5)
        if latest_res.status_code == 200:
            latest_json = latest_res.json()
            latest_item = latest_json.get("result", {}).get("data", {})
            
            latest_period = str(latest_item.get("preDrawIssue", ""))
            latest_number = str(latest_item.get("preDrawCode", ""))
            
            # 優先嘗試讀取 drawTimeRem
            if "drawTimeRem" in latest_item and str(latest_item["drawTimeRem"]).isdigit():
                rem_seconds = int(latest_item["drawTimeRem"])
            else:
                draw_time_str = latest_item.get("drawTime") or latest_item.get("drawDate") or latest_item.get("nextDrawTime") or ""
                if draw_time_str:
                    try:
                        # 將字串轉為指定 UTC+8 時區的時間物件
                        target_dt = datetime.strptime(draw_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST_TZ)
                        now_dt = datetime.now(CST_TZ)
                        diff = int((target_dt - now_dt).total_seconds())
                        
                        # 極速飛艇(10035) 75秒一期，上限設90秒；幸運飛艇(10057) 5分鐘一期，上限設310秒
                        max_allowed = 90 if lot_code == '10035' else 310
                        if 0 <= diff <= max_allowed:
                            rem_seconds = diff
                        elif diff > max_allowed:
                            rem_seconds = max_allowed
                    except Exception as e_p:
                        print(f"[{lot_code}] 時間計算例外：", e_p)

            if latest_period and latest_number and formatted_data:
                if formatted_data[0]["period"] != latest_period:
                    formatted_data.insert(0, {"period": latest_period, "number": latest_number})
    except Exception as e_latest:
        print(f"[{lot_code}] 即時 API 略過：", e_latest)

    return jsonify({
        "errorCode": 0,
        "remSeconds": rem_seconds,
        "result": {
            "data": formatted_data
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
