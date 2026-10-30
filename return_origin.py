
import time
from pyMcc import MoCtrlCard

# ==========================================
# 用户定义的机械台原点
# ==========================================

# 实验室常用运动速度参数
X_SPEED = 10
Y_SPEED = 10

ORIGIN_X = -3.7460
ORIGIN_Y = -52.2690

AXIS_X = 0
AXIS_Y = 1

# ==========================================
# 原点复位函数
# ==========================================

def return_to_origin(
    com_port,
    x_speed,
    y_speed,
    timeout=120,
    confirm=True
):
    """
    将机械台移动到用户定义的 XY 原点。

    参数：
        com_port : 控制器串口，例如 COM3
        x_speed  : X轴运动速度
        y_speed  : Y轴运动速度
        timeout  : 单轴运动超时时间，单位秒
        confirm  : 是否要求人工确认

    返回：
        True  : 复位成功
        False : 复位失败
    """

    mcc = MoCtrlCard()

    try:
        # 1. 初始化控制器
        print("=" * 45)
        print("开始执行机械台原点复位")
        print("=" * 45)

        ret = mcc.MoCtrCard_Initial(com_port)

        if ret != mcc.FUNRESOK:
            print("控制器初始化失败！")
            return False

        print("控制器连接成功！")

        # 2. 读取当前 XY 位置
        ret_x, pos_x = mcc.MoCtrCard_GetAxisPos(AXIS_X)
        ret_y, pos_y = mcc.MoCtrCard_GetAxisPos(AXIS_Y)

        if ret_x != mcc.FUNRESOK or ret_y != mcc.FUNRESOK:
            print("读取机械台当前位置失败！")
            return False

        current_x = pos_x[0]
        current_y = pos_y[0]

        print(f"\n当前 X 位置：{current_x:.4f}")
        print(f"当前 Y 位置：{current_y:.4f}")

        print("\n目标原点：")
        print(f"X = {ORIGIN_X:.4f}")
        print(f"Y = {ORIGIN_Y:.4f}")

        # 3. 计算移动距离
        dx = ORIGIN_X - current_x
        dy = ORIGIN_Y - current_y

        print("\n预计移动距离：")
        print(f"X 轴：{dx:.4f}")
        print(f"Y 轴：{dy:.4f}")

        if confirm:
            answer = input(
                "\n请确认运动范围安全，输入 YES 开始复位："
            )

            if answer != "YES":
                print("已取消复位。")
                return False

        # 4. 定义单轴绝对运动函数
        def move_axis(axis, target, speed, name):

            print(f"\n正在复位 {name} 轴...")

            # 发送绝对位置运动指令
            ret = mcc.MoCtrCard_MCrlAxisAbsMove(
                axis,
                target,
                speed,
                0.0
            )

            if ret != mcc.FUNRESOK:
                print(f"{name} 轴运动指令发送失败！")
                return False

            time.sleep(0.2)

            # 等待运动结束
            start_time = time.time()

            while True:

                ret, running = mcc.MoCtrCard_IsAxisRunning(axis)

                if ret != mcc.FUNRESOK:
                    print(f"{name} 轴状态读取失败！")
                    mcc.MoCtrCard_EmergencyStopAxisMov(axis)
                    return False

                ret, pos = mcc.MoCtrCard_GetAxisPos(axis)

                if ret != mcc.FUNRESOK:
                    print(f"{name} 轴位置读取失败！")
                    mcc.MoCtrCard_EmergencyStopAxisMov(axis)
                    return False

                print(f"{name} 轴当前位置：{pos[0]:.4f}")

                if running == 0:
                    break

                if time.time() - start_time > timeout:
                    print(f"{name} 轴运动超时！")
                    mcc.MoCtrCard_EmergencyStopAxisMov(axis)
                    return False

                time.sleep(0.2)

            # 检查最终位置
            ret, final_pos = mcc.MoCtrCard_GetAxisPos(axis)

            if ret != mcc.FUNRESOK:
                return False

            error = abs(final_pos[0] - target)

            print(f"{name} 轴最终位置：{final_pos[0]:.4f}")

            if error > 0.01:
                print(f"{name} 轴未到达目标位置，误差：{error:.4f}")
                return False

            print(f"{name} 轴复位成功！")
            return True

        # 5. 依次复位 X、Y 轴
        # 先移动 X，再移动 Y，避免未经确认的双轴联动

        if not move_axis(AXIS_X, ORIGIN_X, x_speed, "X"):
            return False

        if not move_axis(AXIS_Y, ORIGIN_Y, y_speed, "Y"):
            return False

        # 6. 复位完成
        print("\n" + "=" * 45)
        print("机械台原点复位完成！")
        print(f"X = {ORIGIN_X:.4f}")
        print(f"Y = {ORIGIN_Y:.4f}")
        print("=" * 45)

        return True

    except KeyboardInterrupt:
        print("\n用户中断操作！")
        return False

    except Exception as e:
        print("发生异常：", e)
        return False

    finally:
        # 关闭底层串口连接。
        # 不调用参考库中存在实现问题的 MoCtrCard_UnLoad()
        port = getattr(mcc, "_MoCtrlCard__comPort", None)

        if port is not None and port.is_open:
            port.close()


# ==========================================
# 独立运行入口
# ==========================================

if __name__ == "__main__":

    print("机械台原点复位程序")

    com = input("请输入控制器 COM 端口：").strip()

    success = return_to_origin(
        com_port=com,
        x_speed=X_SPEED,
        y_speed=Y_SPEED
    )

    if success:
        print("\n复位程序执行成功。")
    else:
        print("\n复位程序未能完成。")
