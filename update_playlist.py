import os
import requests

PORTAL_URL = "http://91.208.115.23:80/c/"
MAC_ADDRESS = "00:1A:79:47:36:F9"
OUTPUT_M3U = "stalker_playlist.m3u"

# กำหนดรหัสหมวดหมู่ที่ต้องการดึง (อ้างอิงจากรายชื่อ ID ใน Server ล่าสุด)
CATEGORY_MAPPING = {
    "3362": "┃UK┃ TNT SPORTS RAW DOLBY",
    "3402": "┃UK| SKY SPORTS SPORTS RAW DOLBY",
    "2686": "┃UK┃ HUB PREMIER PPV"
}

headers = {
    "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
    "Cookie": f"mac={MAC_ADDRESS}; stb_lang=en; timezone=Asia/Bangkok"
}

def generate_stalker_m3u():
    print(f"[1] กำลังเชื่อมต่อ Stalker Server ({PORTAL_URL})...")
    session = requests.Session()
    session.headers.update(headers)

    try:
        # 1. Handshake ขอ Token
        handshake_url = f"{PORTAL_URL}/server/load.php?type=stb&action=handshake&mac={MAC_ADDRESS}"
        res = session.get(handshake_url, timeout=15)
        res_json = res.json()
        token = res_json.get('js', {}).get('token')

        if not token:
            print("[-] ไม่สามารถขอ Token ได้ (MAC อาจไม่ถูกต้องหรือถูกบล็อก)")
            return

        print(f"[+] Token สำเร็จ: {token[:10]}...")
        session.headers.update({"Authorization": f"Bearer {token}"})

        # 2. ดึงรายชื่อช่องทั้งหมด
        print("[2] กำลังดึงรายชื่อช่องรายการทั้งหมด...")
        channels_url = f"{PORTAL_URL}/server/load.php?type=itv&action=get_all_channels&JsHttpRequest=1-xml"
        res_ch = session.get(channels_url, timeout=30)
        channels = res_ch.json().get('js', {}).get('data', [])

        if not channels:
            print("[-] ไม่พบรายการช่องสดในระบบ")
            return

        print(f"[+] กำลังกรองช่องและสร้างลิงก์สตรีม (มีช่องทั้งหมดในระบบ {len(channels)} ช่อง)...")

        success_count = 0
        with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for item in channels:
                # แปลงค่า genre ให้เป็น string และตัดช่องว่าง เพื่อป้องกันปัญหาประเภทข้อมูลไม่ตรงกัน
                genre_id = str(item.get("genre", "0")).strip()
                
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
                    create_link_url = f"{PORTAL_URL}/server/load.php?type=itv&action=create_link&cmd={ch_cmd}&series_id=0&forced_storage=0&disable_neondrm=0&JsHttpRequest=1-xml"
                    link_res = session.get(create_link_url, timeout=10)
                    link_data = link_res.json().get('js', {})
                    raw_url = link_data.get('cmd', '')
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
