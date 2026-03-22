import os
import requests
import json
import re
import socket
import ssl
import concurrent.futures
import time
import random
from collections import defaultdict
from curl_cffi import requests as cffi_requests # ✨ 终极破盾核武器

# ==============================================================================
# 核心配置区
# ==============================================================================
# 从系统环境变量获取 GitHub Secrets (部署到 Actions 时会自动读取)
GIST_ID = os.environ.get('GIST_ID')
GIST_PAT = os.environ.get('GIST_PAT')

# 🎯 你的专属暗号 (必填！脚本会用它去检验反代 IP 的纯度)
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

# 🕸️ 终极破盾版：QZZ 全站爬虫 (curl_cffi 伪装指纹 + 随机延迟)
def fetch_qzz_page(page):
    try:
        url = f"https://proxyip.chatkg.qzz.io/?page={page}" if page > 1 else "https://proxyip.chatkg.qzz.io/"
        
        # 随机停顿，防止触发高频拦截
        time.sleep(random.uniform(1.0, 2.5))
        
        # ✨ 核心保护：impersonate="chrome110" 完美伪装真实浏览器指纹，破解 403！
        r = cffi_requests.get(url, impersonate="chrome110", timeout=15)
        
        if r.status_code == 200:
            matches = re.findall(r'<td>\s*(\d{1,3}(?:\.\d{1,3}){3})\s*</td>\s*<td>\s*(\d+)\s*</td>', r.text)
            return [f"{ip}:{port}" for ip, port in matches]
        elif r.status_code in [403, 429]:
            print(f"⚠️ 第 {page} 页触发了反爬拦截 (状态码: {r.status_code})")
    except Exception as e:
        pass
    return []

# 主逻辑抓取整合
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

    # ================== 3. 💥 究极淘金：防拦截指纹伪装爬虫 ==================
    proxy_candidates = set()
    print("\n🕸️ 启动 QZZ 全站反代爬虫 (启用 curl_cffi 浏览器指纹欺骗，限速 3 线程)...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        pages_results = executor.map(fetch_qzz_page, range(1, 134))
        for page_ips in pages_results:
            if page_ips:
                proxy_candidates.update(page_ips)
                
    print(f"✅ QZZ 全站抓取完毕！共吸入 {len(proxy_candidates)} 个待测矿渣 IP。")

    valid_proxies = []
    if proxy_candidates:
        print(f"🔍 开启 50 线程疯狂质检暗号中，淘汰死节点和自私节点...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            results = executor.map(check_proxy_sni, proxy_candidates)
            for result in results:
                if result:
                    valid_proxies.append(result)
        print(f"💎 淘金完毕！共有 {len(valid_proxies)} 个绝品 IP 暗号正确！")

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

    # 5.1 处理不需要受限的官方库和 WeTest 数据
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

    # 5.2 处理反代数据，每个国家严格限制只保留 5 个
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
