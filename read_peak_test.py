
import pyvisa

# ==============================
# 1. 连接 R&S FSW-50
# ==============================

ADDRESS = "TCPIP0::192.168.31.14::inst0::INSTR"

rm = pyvisa.ResourceManager("@py")
inst = None

try:
    inst = rm.open_resource(ADDRESS)
    inst.timeout = 10000

    print("=" * 50)
    print("R&S FSW-50 Peak Search")
    print("=" * 50)

    # 读取设备信息
    print("仪器信息：", inst.query("*IDN?").strip())

    # ==============================
    # 2. 指定 Trace 1
    # ==============================

    inst.write("CALC:MARK1:TRAC 1")

    # ==============================
    # 3. 执行最大峰值搜索
    # ==============================

    inst.write("CALC:MARK1:MAX:PEAK")

    # 等待仪器完成指令
    inst.query("*OPC?")

    # ==============================
    # 4. 读取 Peak Marker 数据
    # ==============================

    peak_frequency = float(
        inst.query("CALC:MARK1:X?").strip()
    )

    peak_power = float(
        inst.query("CALC:MARK1:Y?").strip()
    )

    # ==============================
    # 5. 输出结果
    # ==============================

    print("\n========== Peak Search 结果 ==========")

    print(f"Peak Frequency: {peak_frequency / 1e9:.6f} GHz")
    print(f"Peak Power:     {peak_power:.4f} dBm")

    print("======================================")

    # 查询仪器错误信息
    print("仪器状态：", inst.query("SYST:ERR?").strip())

except Exception as e:
    print("读取失败：", e)

finally:
    if inst is not None:
        inst.close()

    rm.close()
