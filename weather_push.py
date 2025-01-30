import requests
import os
import json
from datetime import datetime

def push_message(message):
    """推送到多个设备"""
    keys = os.getenv('PUSHDEER_KEY', '').split(',')
    if not keys:
        print("未配置PUSHDEER_KEY")
        return

    for key in keys:
        key = key.strip()
        if not key:
            continue
            
        try:
            push_url = f"https://api2.pushdeer.com/message/push?pushkey={key}&text={message}"
            response = requests.get(push_url, timeout=5)
            response.raise_for_status()
            print(f"推送到 {key[:3]}... 成功")
        except Exception as e:
            print(f"推送到 {key[:3]}... 失败：{str(e)}")

def translate_skycon(skycon):
    """天气现象中英对照（含Emoji）"""
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
    return skycon_map.get(skycon, skycon)

def format_date(date_str):
    """格式化日期字符串"""
    try:
        return datetime.fromisoformat(date_str.replace('+08:00', '')).strftime('%Y-%m-%d')
    except:
        return date_str.split('T')[0]

def get_locations():
    """从Secrets获取地区配置"""
    try:
        locations_json = os.getenv('WEATHER_LOCATIONS', '[{"name": "上海", "coords": "121.4737,31.2304"}]')
        return json.loads(locations_json)
    except Exception as e:
        push_message(f"❌ 地区配置解析失败：{str(e)}")
        return []

def get_weather_info():
    """主处理函数（修改后）"""
    locations = get_locations()
    
    for loc in locations:
        try:
            # 为每个地区生成独立报告
            weather_info = generate_weather_report(loc)
            if weather_info:
                push_message(weather_info)
        except Exception as e:
            push_message(f"⚠️ {loc.get('name','未知地区')}数据处理失败：{str(e)}")

def generate_weather_report(location):
    """生成单个地区的完整天气报告（原逻辑封装）"""
    try:
        api_url = f"https://api.caiyunapp.com/v2.6/{os.getenv('CAIYUN_API_KEY')}/{location['coords']}/weather.json"
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        weather_data = response.json()

        if weather_data.get('status') != 'ok':
            return f"⚠️ {location['name']}天气API状态异常"

        result = weather_data['result']
        realtime = result['realtime']
        daily = result['daily']

        # 生成与原始格式完全相同的报告
        weather_info = f"🌤️ {location['name']}实时天气概况\n"
        weather_info += "\n"
        weather_info += f"{translate_skycon(realtime['skycon'])}\n"
        weather_info += "\n"
        weather_info += f"温度：{round(realtime['temperature'])}°C（体感{round(realtime['apparent_temperature'])}°C）\n"
        weather_info += "\n"
        weather_info += f"风速：{round(realtime['wind']['speed'])}m/s 💨 湿度：{realtime['humidity']*100}%\n"
        weather_info += "\n"
        weather_info += f"降水：{realtime['precipitation']['local']['intensity']}mm/h 🌧️ 空气质量：{realtime['air_quality']['aqi']['chn']}（{realtime['air_quality']['description']['chn']}）\n"

        # 三日预报
        weather_info += "\n📅 三日天气预报\n"
        weather_info += "\n"
        for i in range(3):
            date = format_date(daily['skycon'][i]['date'])
            skycon = translate_skycon(daily['skycon'][i]['value'])
            temp = f"{round(daily['temperature'][i]['min'])}~{round(daily['temperature'][i]['max'])}°C"
            prob_rain = daily['precipitation'][i]['probability']
            weather_info += f"{date} | {skycon}\n"
            weather_info += f"气温：{temp} | 降水概率：{prob_rain}%\n\n"

        # 生活指数
        weather_info += "📊 生活指数参考\n"
        weather_info += "\n"
        for i in range(3):
            date = format_date(daily['life_index']['ultraviolet'][i]['date'])
            uv = daily['life_index']['ultraviolet'][i]['index']
            dress = daily['life_index']['dressing'][i]['desc']
            comfort = daily['life_index']['comfort'][i]['desc']
            weather_info += f"{date} | 紫外线：{uv}级 | 穿衣：{dress}\n"
            weather_info += "\n"
            weather_info += f"舒适度：{comfort}\n\n"

        # 预警信息
        if 'alert' in result and result['alert']['content']:
            weather_info += "⚠️ 气象预警\n"
            weather_info += "\n"
            weather_info += result['alert']['content'] + "\n"

        # 关键提示
        weather_info += "\n🔍 天气提示\n"
        weather_info += "\n"
        weather_info += result.get('forecast_keypoint', '无特别提示') + "\n"

        return weather_info

    except requests.exceptions.RequestException as e:
        return f"🌐 {location['name']}网络请求异常：{str(e)}"
    except KeyError as e:
        return f"🔑 {location['name']}数据字段缺失：{str(e)}"
    except Exception as e:
        return f"❌ {location['name']}未知错误：{str(e)}"

if __name__ == "__main__":
    get_weather_info()
