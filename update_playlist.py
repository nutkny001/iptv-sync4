from datetime import datetime
import os
import requests
from zoneinfo import ZoneInfo

PORTAL_URL = "http://45.139.122.199:8080/c"
MAC_ADDRESS = "00:1A:79:C0:16:27"
OUTPUT_M3U = "stalker_playlist.m3u"
OUTPUT_LIVE_M3U = OUTPUT_M3U

# กำหนดรหัสหมวดหมู่ที่ต้องการดึง (อ้างอิงตาม ID ของ Server)
CATEGORY_MAPPING = {
    "111": "Australia & New Zealand",
    "761": "UK SPORTS",
}

headers = {
    "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
    "Cookie": f"mac={MAC_ADDRESS}; stb_lang=en; timezone=Asia/Bangkok",
    "Referer": f"{PORTAL_URL}/c/index.html",
}


def generate_stalker_m3u():
    print(f"[1] กำลังเชื่อมต่อ Stalker Server ({PORTAL_URL})...")
    session = requests.Session()
    session.headers.update(headers)

    try:
        # 1. Handshake เพื่อขอ Token
        handshake_url = f"{PORTAL_URL}/server/load.php?type=stb&action=handshake&mac={MAC_ADDRESS}&JsHttpRequest=1-xml"
        res = session.get(handshake_url, timeout=15)
        
        try:
            res_json = res.json()
        except Exception:
            print(f"[-] Server ไม่ได้ตอบกลับเป็น JSON: {res.text[:100]}")
            return

        token = res_json.get("js", {}).get("token")

        if not token:
            print("[-] ไม่สามารถขอ Token ได้ เซิร์ฟเวอร์อาจปฏิเสธ MAC Address นี้")
            return

        print(f"[+] Token สำเร็จ: {token[:10]}...")
        
        # เพิ่ม Token ทั้งใน Header และ Cookie เพื่อความชัวร์
        session.headers.update({"Authorization": f"Bearer {token}"})
        session.cookies.set("token", token)

        # 2. ดึงรายการช่องทั้งหมด
        print("[2] กำลังดึงรายชื่อช่องรายการทั้งหมด...")
        channels_url = f"{PORTAL_URL}/server/load.php?type=itv&action=get_all_channels&JsHttpRequest=1-xml"
        res_ch = session.get(channels_url, timeout=30)
        
        channels = res_ch.json().get("js", {}).get("data", [])

        if not channels:
            print("[-] ไม่พบรายการช่องสดในระบบ หรือรูปแบบข้อมูลเปลี่ยนไป")
            return

        print(f"[+] กำลังกรองช่องจากทั้งหมด {len(channels)} ช่อง...")

        now_str = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S")
        success_count = 0

        with open(OUTPUT_LIVE_M3U, "w", encoding="utf-8") as f:
            f.write('#EXTM3U url-tvg=""\n')
            f.write(f'#EXTINF:-1 group-title="ℹ️ SYSTEM INFO",🕒 🟢 อัปเดตล่าสุด: {now_str} 🟢\n')
            f.write("http://clients.link/updated\n")

            for item in channels:
                genre_id = str(item.get("tv_genre_id") or item.get("genre", "0")).strip()

                if genre_id not in CATEGORY_MAPPING:
                    continue

                name = item.get("name", "Unknown")
                ch_cmd = item.get("cmd", "")
                tvg_id = item.get("tvg_id", "")
                stream_icon = item.get("logo", "")
                group_title = CATEGORY_MAPPING[genre_id]

                if not ch_cmd:
                    continue

                try:
                    # 3. สร้างลิงก์สตรีมจริงของแต่ละช่อง
                    create_link_url = f"{PORTAL_URL}/server/load.php?type=itv&action=create_link&cmd={ch_cmd}&series_id=0&forced_storage=0&disable_neondrm=0&JsHttpRequest=1-xml"
                    link_res = session.get(create_link_url, timeout=10)
                    link_data = link_res.json().get("js", {})
                    raw_url = link_data.get("cmd", "")
                    
                    stream_url = raw_url.replace("ffmpeg ", "").replace("auto ", "").strip()

                    if stream_url:
                        f.write(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{stream_icon}" group-title="{group_title}",{name}\n')
                        f.write(f"{stream_url}\n")
                        success_count += 1
                except Exception:
                    continue

        print(f"[✔] บันทึกไฟล์ M3U สำเร็จ {success_count} ช่อง ไปที่: {OUTPUT_M3U}")

    except Exception as e:
        print(f"[-] เกิดข้อผิดพลาด: {e}")


if __name__ == "__main__":
    generate_stalker_m3u()
