import os
import requests
import json
import re
import socket
import ssl
import concurrent.futures
from collections import defaultdict

# ==============================================================================
# 获取 GitHub Secrets 密钥
# ==============================================================================
GIST_ID = os.environ.get('GIST_ID')
GIST_PAT = os.environ.get('GIST_PAT')

# ==============================================================================
# 核心配置区
# ==============================================================================
# 🎯 你的专属暗号 (作为试金石)
YOUR_SNI = "hk.lingqiu.eu.org"

# 🌟 官方优选 IP 数据源
SOURCES = [
    "https://gist.githubusercontent.com/shiyikeji/3ce1217fe686b8d8525719086bae5312/raw/my_best_cf_ips.txt",
    "https://raw.githubusercontent.com/cmliu/WorkerVless2sub/main/addressesapi.txt",
    "https://raw.githubusercontent.com/cmliu/WorkerVless2sub/main/addressesipv6api.txt",
    "https://ip.164746.xyz/ipTop10.html"  
]

WETEST_URLS = [
    "https://www.wetest.vip/page/cloudflare/address_v4.html",
    "https://www.wetest.vip/page/cloudflare/address_v6.html"
]

# 🕵️‍♂️ 终极“熟肉”大厂矿源
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestproxy.txt",
    "https://raw.githubusercontent.com/ymyuuu/IPDB/main/proxy.txt"
]

COLO_MAP = {
    "HKG": "🇭🇰 HK", "SIN": "🇸🇬 SG", "NRT": "🇯🇵 JP", "KIX": "🇯🇵 JP",
    "SJC": "🇺🇸 US", "LAX": "🇺🇸 US", "SEA": "🇺🇸 US", "FRA": "🇩🇪 DE",
    "LHR": "🇬🇧 GB", "TPE": "🇹🇼 TW", "ICN": "🇰🇷 KR",
    "SG": "🇸🇬 SG", "HK": "🇭🇰 HK", "TW": "🇹🇼 TW", "JP": "🇯🇵 JP", "US": "🇺🇸 US"
}

# ==============================================================================
# 核心功能组件
# ==============================================================================

# 🚀 黑科技：TLS 狙击器 (底层握手检验 SNI 暗号)
def check_proxy_sni(ip_port):
    try:
        ip, port_raw = ip_port.split(':')
        port = int(port_raw.split('#')[0])
    except ValueError:
        return None
        
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE 
        with socket.create_connection((ip, port), timeout=2.5) as sock:
            with ctx.wrap_socket(sock, server_hostname=YOUR_SNI) as ssock:
                req = f"GET / HTTP/1.1\r\nHost: {YOUR_SNI}\r\nUser-Agent: Mozilla/5.0\r\n\r\n"
                ssock.sendall(req.encode())
                res = ssock.recv(512).decode('utf-8', 'ignore')
                if "HTTP/1." in res:
                    return f"{ip}:{port}" 
    except Exception:
        pass
    return None

def fetch_ips():
    all_ips = set()
    ip_pattern = re.compile(r'^(\[[0-9a-fA-F:]+\]|\d{1,3}(?:\.\d{1,3}){3})(?::(\d+))?(?:#(.*))?$')

    # ================== 1. 抓取官方优选源 ==================
    for url in SOURCES:
        try:
            print(f"正在读取官方源: {url}")
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if res.status_code == 200:
                text = res.text.replace(',', '\n').replace(';', '\n')
                for line in text.splitlines():
                    line = re.sub(r'<[^>]+>', '', line).strip()
                    if not line or line.startswith('#'): continue
                    
                    match = ip_pattern.match(line)
                    if match:
                        ip = match.group(1)
                        port = match.group(2) or "443"
                        remark = (match.group(3) or "").strip()
                        
                        general_new_remark = COLO_MAP.get(remark.upper(), remark) if remark else ""
                        if "ipTop10.html" in url:
                            final_remark = f"{COLO_MAP[remark.upper()]}-冷库" if (remark and remark.upper() in COLO_MAP) else "❄️冷库"
                        else:
                            final_remark = general_new_remark if general_new_remark else "Auto"
                            if "3ce1217fe686b8d8525719086bae5312" in url:
                                final_remark = f"{final_remark}-QD"
                        all_ips.add(f"{ip}:{port}#{final_remark}")
        except Exception as e:
            print(f"跳过失效源: {url} , 错误: {e}")

    # ================== 2. WeTest 抓取 ==================
    for url in WETEST_URLS:
        try:
            print(f"正在破解 WeTest 网页: {url}")
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if res.status_code == 200:
                text = res.text
                ips = re.findall(r'<td data-label="优选地址">([\d\.:a-fA-F]+)</td>', text)
                isps = re.findall(r'<td data-label="线路名称">(.+?)</td>', text)
                colos = re.findall(r'<td data-label="数据中心">(.+?)</td>', text)

                for i in range(len(ips)):
                    raw_ip = ips[i].strip()
                    colo = colos[i].strip() if i < len(colos) else "WT"
                    isp = re.sub(r'<[^>]+>|\s+', '', isps[i].strip()) if i < len(isps) else ""
                    alias = f"{COLO_MAP.get(colo, colo)}-{isp}".strip('-')
                    ip_core = f"[{raw_ip}]" if ':' in raw_ip else raw_ip
                    all_ips.add(f"{ip_core}:443#{alias}")
                    all_ips.add(f"{ip_core}:80#{alias}-极速")
        except Exception:
            pass

    # ================== 3. 💥 究极淘金：拉取生肉矿源 + 并发对暗号 ==================
    proxy_candidates = set()
    for url in PROXY_SOURCES:
        try:
            print(f"\n🕸️ 正在拉取全网反代大厂生肉矿渣: {url}")
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if res.status_code == 200:
                # ✨ 核心修复：兼容纯 IP 格式，没端口的自动补齐 443 端口！
                raw_matches = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b', res.text)
                for match in raw_matches:
                    if ':' not in match:
                        proxy_candidates.add(f"{match}:443")
                    else:
                        proxy_candidates.add(match)
        except Exception as e:
            print(f"拉取反代源失败: {e}")

    valid_proxies = []
    if proxy_candidates:
        print(f"🔍 成功吸入 {len(proxy_candidates)} 个矿渣！开启 50 线程疯狂质检暗号中...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            results = executor.map(check_proxy_sni, proxy_candidates)
            for result in results:
                if result:
                    valid_proxies.append(result)
        print(f"💎 淘金完毕！共有 {len(valid_proxies)} 个大厂绝品 IP 对上了你的暗号！")

    # ================== 4. 🌍 户口查验：为未知 IP 分配国旗 ==================
    temp_valid_proxy_list = set()
    for vp in valid_proxies:
        temp_valid_proxy_list.add(f"{vp}#Auto-反代") 

    all_need_geo_ips = set()
    for item in all_ips:
        ip_port, remark = item.split('#', 1)
        if remark in ["❄️冷库", "Auto", "Auto-QD"]:
            ip = ip_port.rsplit(':', 1)[0].strip('[]')
            all_need_geo_ips.add(ip)
    
    for item in temp_valid_proxy_list:
        ip_port, remark = item.split('#', 1)
        ip = ip_port.rsplit(':', 1)[0].strip('[]')
        all_need_geo_ips.add(ip)

    all_need_geo_ips = list(all_need_geo_ips)
    ip_geo_map = {}
    if all_need_geo_ips:
        print("\n🌍 正在调用 API 识别未知 IP 归属地...")
        for i in range(0, len(all_need_geo_ips), 100):
            chunk = all_need_geo_ips[i:i+100]
            try:
                res = requests.post("http://ip-api.com/batch?fields=query,countryCode", json=chunk, timeout=10)
                if res.status_code == 200:
                    for data in res.json():
                        if 'countryCode' in data:
                            ip_geo_map[data['query']] = data['countryCode']
            except Exception:
                pass

    # ================== 5. 👑 终极组装 + 强迫症精简 ==================
    final_ips = set()
    country_proxy_counter = defaultdict(int)

    for item in all_ips:
        ip_port, remark = item.split('#', 1)
        if remark in ["❄️冷库", "Auto", "Auto-QD"]:
            ip = ip_port.rsplit(':', 1)[0].strip('[]')
            country_code = ip_geo_map.get(ip)
            if country_code and len(country_code) == 2:
                emoji = chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397)
                flag = f"{emoji} {country_code}"
                if "冷库" in remark:
                    new_remark = f"{flag}-冷库"
                elif "QD" in remark:
                    new_remark = f"{flag}-QD"
                else:
                    new_remark = flag
                final_ips.add(f"{ip_port}#{new_remark}")
            else:
                final_ips.add(item)
        else:
            final_ips.add(item)

    for item in sorted(list(temp_valid_proxy_list)): 
        ip_port, remark = item.split('#', 1)
        ip = ip_port.rsplit(':', 1)[0].strip('[]')
        country_code = ip_geo_map.get(ip)
        
        if country_code and len(country_code) == 2:
            emoji = chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397)
            if country_proxy_counter[country_code] < 5:
                country_proxy_counter[country_code] += 1
                final_remark = f"{emoji} {country_code}-反代"
                final_ips.add(f"{ip_port}#{final_remark}")
                
    # ================== 6. 排序 ==================
    def sort_by_name(item):
        parts = item.split('#')
        ip_port = parts[0]
        name = parts[1] if len(parts) > 1 else ""
        is_v6 = 1 if '[' in ip_port else 0
        return (is_v6, name, ip_port)

    return sorted(list(final_ips), key=sort_by_name)

# ==============================================================================
# 推送模块
# ==============================================================================
def update_gist(content):
    if not GIST_ID or not GIST_PAT:
        print("⚠️ 警告: 缺少 GIST_ID 或 GIST_PAT 环境变量，生成的结果将只会在本地输出。")
        return

    headers = {"Authorization": f"token {GIST_PAT}", "Accept": "application/vnd.github.v3+json"}
    data = {"files": {"my_best_ips.txt": {"content": content if content else "1.0.0.1:443#抓取彻底失败兜底"}}}
    url = f"https://api.github.com/gists/{GIST_ID}"
    
    try:
        res = requests.patch(url, headers=headers, data=json.dumps(data))
        if res.status_code == 200:
            print("✅ 全网聚合极简精简版库已成功推送到 Gist！")
        else:
            print(f"❌ 推送失败: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ 请求 Gist API 失败: {e}")

# ==============================================================================
# 启动器
# ==============================================================================
if __name__ == "__main__":
    ips = fetch_ips()
    unique_ips = sorted(list(set(ips)), key=lambda x: x.split('#')[1] if len(x.split('#')) > 1 else "")
    
    print("\n" + "="*50)
    print(f"✨ 运行完毕！汇总质检+强迫症精简后，共获得 {len(unique_ips)} 个极品 IP！")
    print("="*50)
    
    final_content = "\n".join(unique_ips)
    update_gist(final_content)
