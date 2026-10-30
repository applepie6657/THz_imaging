##代码1：获取局域网的visa设备

## 首先获取pyvisa的地址

import pyvisa
import socket
from concurrent.futures import ThreadPoolExecutor

def scan_pyvisa_resources():
    """使用 PyVISA 默认驱动检索当前系统已识别的所有资源 (USB, GPIB, TCPIP)"""
    print("=" * 60)
    print("1. 正在通过 PyVISA 广播检索本地/网络 VISA 资源...")
    print("=" * 60)
    
    rm = pyvisa.ResourceManager('@py')
    
    # 搜索包含 TCPIP 的资源（也可以用 '?' 搜索全部）
    try:
        resources = rm.list_resources()
    except Exception as e:
        print(f"检索资源时出错: {e}")
        return []

    found_devices = []
    if not resources:
        print("未自动检索到任何 VISA 资源。")
    else:
        for res in resources:
            print(f"\n发现资源句柄: {res}")
            try:
                inst = rm.open_resource(res)
                inst.timeout = 2000  # 2秒超时
                idn = inst.query('*IDN?').strip()
                print(f"  └─ 设备响应 (*IDN?): {idn}")
                found_devices.append((res, idn))
                inst.close()
            except Exception as e:
                print(f"  └─ 无法与该资源握手: {e}")
                
    rm.close()
    return found_devices


def check_ip_scpi(ip, port=5025, timeout=0.5):
    """尝试与指定 IP 的 SCPI 端口建立 Socket 连接，判断是否有程控仪器"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            return ip
    except Exception:
        pass
    return None


def scan_subnet_for_scpi(subnet_prefix="192.168.31", start_ip=1, end_ip=254, port=5025):
    """
    多线程扫描局域网网段中的 SCPI 端口 (如 5025 / 111 / 4880)，
    并使用 PyVISA 验证 *IDN?
    """
    print("\n" + "=" * 60)
    print(f"2. 正在快速扫描网段 {subnet_prefix}.{start_ip}~{end_ip} (端口 {port})...")
    print("=" * 60)
    
    ip_list = [f"{subnet_prefix}.{i}" for i in range(start_ip, end_ip + 1)]
    active_ips = []

    # 使用线程池并发加速 IP 端口探测
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(check_ip_scpi, ip, port) for ip in ip_list]
        for future in futures:
            ip = future.result()
            if ip:
                active_ips.append(ip)

    if not active_ips:
        print("未在该网段发现开放 SCPI 端口的设备。")
        return []

    print(f"探测到开放端口 {port} 的 IP 地址: {active_ips}\n正在尝试读取设备 *IDN? 信息...")

    rm = pyvisa.ResourceManager('@py')
    found_devices = []

    for ip in active_ips:
        # 尝试两种常见的 TCPIP VISA 格式：INSTR (VXI-11/LXI) 和 SOCKET (Raw TCP)
        visa_addresses = [
            f"TCPIP0::{ip}::inst0::INSTR",
            f"TCPIP0::{ip}::{port}::SOCKET"
        ]
        
        for resource in visa_addresses:
            try:
                inst = rm.open_resource(resource)
                inst.timeout = 2000
                if "SOCKET" in resource:
                    inst.read_termination = '\n'
                    inst.write_termination = '\n'
                
                idn = inst.query('*IDN?').strip()
                print(f"✅ [成功匹配] VISA 地址: {resource}\n   设备标识: {idn}\n")
                found_devices.append((resource, idn))
                inst.close()
                break # 找到一种可用的 VISA 格式即可跳出
            except Exception:
                continue

    rm.close()
    return found_devices


# ================= 程序入口 =================
if __name__ == "__main__":
    # 步骤 1：自动广播搜寻
    pyvisa_devices = scan_pyvisa_resources()

    # 步骤 2：如果广播没搜到，或者你想扫描特定的网段（例如 192.168.1.x）
    # 请根据你实际实验室的网段修改 subnet_prefix
    TARGET_SUBNET = "192.168.31" 
    
    # 常用 SCPI 端口：5025 (Raw Socket 标准端口), 111 (VXI-11 端口)
    subnet_devices = scan_subnet_for_scpi(subnet_prefix=TARGET_SUBNET, port=5025)

    # 汇总输出
    print("\n" + "=" * 60)
    print("扫描总结 - 局域网可用设备列表:")
    print("=" * 60)
    all_devices = pyvisa_devices + subnet_devices
    if not all_devices:
        print("未找到任何可用设备，请检查：\n1. 示波器/射频源与电脑是否处于同一子网\n2. 示波器/射频源的 LAN/LXI 接口及 Remote Control 功能已开启")
    else:
        for addr, idn in set(all_devices):
            print(f"• VISA 地址: {addr}")
            print(f"  设备型号: {idn}")