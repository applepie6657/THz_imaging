
import time
from pyMcc import MoCtrlCard

# =====================================
# 1. 初始化运动控制卡
# =====================================

mccard = MoCtrlCard()

print("=" * 45)
print("太赫兹成像实验 - 机械台单轴运动测试")
print("=" * 45)

# 显示可用串口
ports = mccard.MoCtrCard_GetAvailablePorts()

if len(ports) == 0:
    print("没有发现可用串口，请检查 USB/串口连接！")
    raise SystemExit

print("\n检测到以下串口：")
for port in ports:
    print(port)

com_port = input("\n请输入机械控制器对应的 COM 端口：").strip()

ret = mccard.MoCtrCard_Initial(com_port)

if ret != mccard.FUNRESOK:
    print("控制器初始化失败！")
    raise SystemExit

print("\n控制器初始化成功！")

# =====================================
# 2. 选择运动轴
# =====================================

print("\n轴号：0-X，1-Y，2-Z，3-T")

axis_id = int(input("请输入测试轴号："))

if axis_id not in [0, 1, 2, 3]:
    print("轴号错误！")
    raise SystemExit

# =====================================
# 3. 获取初始位置
# =====================================

ret, pos = mccard.MoCtrCard_GetAxisPos(axis_id)

if ret != mccard.FUNRESOK:
    print("无法读取当前位置！")
    raise SystemExit

initial_pos = pos[0]

print(f"\n当前轴 {axis_id} 位置：{initial_pos:.4f}")

# =====================================
# 4. 设置运动参数
# =====================================

print("\n请输入经过实验室确认的安全运动参数。")
print("注意：距离和速度的物理单位需要先向老师确认。")

distance = float(input("相对移动距离（带正负号）："))
velocity = float(input("运动速度（正数）："))

if distance == 0 or velocity <= 0:
    print("运动参数无效！")
    raise SystemExit

acceleration = 0.0

print("\n即将执行以下运动：")
print(f"运动轴：{axis_id}")
print(f"初始位置：{initial_pos:.4f}")
print(f"移动距离：{distance}")
print(f"运动速度：{velocity}")
print(f"目标位置：{initial_pos + distance:.4f}")

confirm = input(
    "\n请确认机械台行程、方向及运动区域安全，输入 YES 开始："
)

if confirm != "YES":
    print("已取消运动。")
    raise SystemExit

# =====================================
# 5. 发送单轴相对运动指令
# =====================================

print("\n正在发送运动指令...")

ret = mccard.MoCtrCard_MCrlAxisRelMove(
    axis_id,
    distance,
    velocity,
    acceleration
)

if ret != mccard.FUNRESOK:
    print("运动指令发送失败！")
    raise SystemExit

print("运动指令发送成功！")

# =====================================
# 6. 实时监测运动状态
# =====================================

start_time = time.time()
timeout = 60

try:
    while True:

        ret, running = mccard.MoCtrCard_IsAxisRunning(axis_id)

        if ret != mccard.FUNRESOK:
            print("读取运动状态失败！")
            break

        ret, pos = mccard.MoCtrCard_GetAxisPos(axis_id)

        if ret == mccard.FUNRESOK:
            print(f"当前位置：{pos[0]:.4f}")

        if running == 0:
            print("\n机械台运动结束！")
            break

        if time.time() - start_time > timeout:
            print("\n等待超时，执行急停！")
            mccard.MoCtrCard_EmergencyStopAxisMov(axis_id)
            break

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n用户中断，执行急停！")
    mccard.MoCtrCard_EmergencyStopAxisMov(axis_id)

# =====================================
# 7. 输出最终位置
# =====================================

ret, final_pos = mccard.MoCtrCard_GetAxisPos(axis_id)

if ret == mccard.FUNRESOK:
    print("\n========== 测试结果 ==========")
    print(f"初始位置：{initial_pos:.4f}")
    print(f"最终位置：{final_pos[0]:.4f}")
    print(f"实际位移：{final_pos[0] - initial_pos:.4f}")
    print("==============================")

print("\n测试程序结束。")
