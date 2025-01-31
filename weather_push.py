import requests
import os
import json
from datetime import datetime, timedelta
from urllib.parse import quote

# 环境变量配置
PUSHDEER_KEY = os.getenv('PUSHDEER_KEY', '')
CAIYUN_API_KEY = os.getenv('CAIYUN_API_KEY', '')
QUOTE_API_KEY = os.getenv('QUOTE_API_KEY', '')
CHP_API_KEY = os.getenv('CHP_API_KEY', '')

def push_message(message):
    """安全推送消息"""
    if not PUSHDEER_KEY:
        print("未配置PUSHDEER_KEY")
        return

    for key in PUSHDEER_KEY.split(','):
        key = key.strip()
        if not key:
            continue

        try:
            push_url = "https://api2.pushdeer.com/message/push"
            params = {
                'pushkey': key,
                'text': message[:500]  # 限制消息长度
            }
            response = requests.get(push_url, params=params, timeout=10)
            response.raise_for_status()
            print(f"推送成功到 {key[:3]}...")
        except Exception as e:
            print(f"推送失败到 {key[:3]}...：{str(e)}")

def translate_skycon(skycon):
    """天气现象翻译（含新发现的天气类型）"""
    skycon_map = {
        "CLEAR_DAY": "☀️晴", "CLEAR_NIGHT": "🌙晴夜",
        "PARTLY_CLOUDY_DAY": "⛅多云", "PARTLY_CLOUDY_NIGHT": "☁️多云夜",
        "CLOUDY": "☁️阴", 
        "LIGHT_RAIN": "🌦️小雨", "MODERATE_RAIN": "🌧️中雨",
        "HEAVY_RAIN": "💦大雨", "STORM_RAIN": "⛈️暴雨",
        "LIGHT_SNOW": "❄️小雪", "MODERATE_SNOW": "🌨️中雪",
        "HEAVY_SNOW": "❄️大雪", "STORM_SNOW": "❄️暴雪",
        "FOG": "🌫️雾", "LIGHT_HAZE": "😷轻霾", 
        "MODERATE_HAZE": "😷中霾", "HEAVY_HAZE": "😷重霾",
        "WIND": "🌪️大风", "DUST": "💨浮尘", "SAND": "💨沙尘"
    }
    return skycon_map.get(skycon, f"未知天气（{skycon}）")

def get_hourly_alerts(hourly_data):
    """生成重点时段提醒"""
    alerts = []
    threshold = 30  # 降水概率阈值

    for hour in hourly_data[:24]:  # 只处理未来24小时数据
        dt = datetime.fromisoformat(hour['datetime'].replace('+08:00', ''))
        prob = hour.get('probability', 0)
        skycon = translate_skycon(hour.get('value', ''))
        if prob >= threshold:
            alerts.append(f"▫️ {dt.strftime('%H:%M')} {skycon}（降水概率{prob}%）")

    return alerts

def generate_weather_report(location):
    """生成天气报告"""
    try:
        # 获取天气数据
        api_url = f"https://api.caiyunapp.com/v2.6/{CAIYUN_API_KEY}/{location['coords']}/weather.json"
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get('status') != 'ok':
            return f"⚠️ {location['name']}天气数据获取失败"

        result = data['result']
        realtime = result.get('realtime', {})
        daily = result.get('daily', {})
        hourly = result.get('hourly', {})

        # 构建报告
        report = []

        # 实时天气
        temp = round(realtime.get('temperature', 0))
        feels_like = round(realtime.get('apparent_temperature', 0))
        wind_speed = realtime.get('wind', {}).get('speed', 0)
        precipitation = realtime.get('precipitation', {}).get('local', {}).get('intensity', 0)
        
        report.extend([
            f"🌡️{location['name']} 实时气候速览",
            f"\n"
            f"   ▸气温：{temp}°C → 体感{feels_like}°C",
            f"\n"
            f"   ▸风力：{get_wind_level(wind_speed)}",
            f"\n"
            f"   ▸湿度：{get_humidity_desc(realtime.get('humidity', 0))}",
            f"\n"
            f"   ▸降水：{'无降水' if precipitation < 0.1 else f'{precipitation:.1f}mm/h'}",
            f"\n"
        ])

        # 重点时段提醒
        hourly_alerts = get_hourly_alerts(hourly.get('precipitation', []))
        if hourly_alerts:
            report.append("⏰ 重点时段提醒")
            report.append("")
            report.extend(hourly_alerts)
            report.append("")

        # 三日预报
        report.append("📅 三日天气走势")
        report.append("")
        for i in range(3):
            date_str = format_date(daily['skycon'][i]['date'])
            skycon = translate_skycon(daily['skycon'][i]['value'])
            temp_min = round(daily['temperature'][i]['min'])
            temp_max = round(daily['temperature'][i]['max'])
            prob_rain = daily['precipitation'][i]['probability']
            desc = f"{prob_rain}%降水概率"
            
            report.append(
                f"[{date_str}] {skycon}\n"
                f"\n"
                f"  ▸ 气温：{temp_min}~{temp_max}°C\n"
                f"\n"
                f"  ▸ 湿度：{get_humidity_desc(daily['humidity'][i]['avg'])}\n"
                f"\n"
                f"  ▸ {desc}"
                f"\n"
            )
        report.append("")

        # 每日一句和彩虹屁
        report.extend([
            "📜 每日一句",
            "\n",
            get_quote(),
            "\n",
            "🌈 彩虹屁",
            "\n",
            get_chp()
        ])

        return "\n".join(report)

    except requests.exceptions.RequestException as e:
        return f"🌐 {location['name']}网络请求异常：{str(e)}"
    except Exception as e:
        return f"❌ {location['name']}数据处理失败：{str(e)}"

def get_locations():
    """获取地区配置"""
    try:
        locations = json.loads(os.getenv('WEATHER_LOCATIONS', '[]'))
        return [loc for loc in locations if 'name' in loc and 'coords' in loc]
    except Exception as e:
        push_message(f"❌ 配置解析失败：{str(e)}")
        return []

def format_date(date_str):
    """格式化日期为 MM-DD 周x"""
    try:
        dt = datetime.fromisoformat(date_str.replace('+08:00', ''))
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return f"{dt.month:02d}-{dt.day:02d} {weekdays[dt.weekday()]}"
    except:
        return date_str.split('T')[0][5:]

def get_quote():
    """获取每日一句"""
    try:
        res = requests.get(QUOTE_API_KEY, timeout=3)
        data = res.json()
        return f"{data['hitokoto']}\n—— {data.get('from', '未知')}"
    except Exception:
        return "每日一句接口异常"

def get_chp():
    """获取彩虹屁"""
    try:
        res = requests.get(CHP_API_KEY, timeout=3)
        return res.json()['data']['text']
    except Exception:
        return "彩虹屁接口异常"

if __name__ == "__main__":
    locations = get_locations()
    if not locations:
        print("未配置有效地区信息")
        exit()
        
    for loc in locations:
        report = generate_weather_report(loc)
        if report:
            push_message(report)
