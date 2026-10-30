# THz_imaging

太赫兹成像实验相关的 Python 脚本，包含仪器发现、频谱峰值读取和机械运动控制。

## 操作说明【必读】
*revision:2026.10.30 14：00，宋品逢*
- 如需要手动控制机械台移动，用于找初始位置。直接云心manual_stage_control.py.
- 如需要自行规定初始位置，只需要修改return_origin.py中的`ORIGIN_X`和`ORIGIN_Y`参数。
- 如需要运行扫描，修改scan_top.py文件中的`X_POINTS`、`VELOCITY `、`X_STEP_DISTANCE`等参数,然后运行scan_top.py进行扫描，扫描结果保存在img_output文件夹下，以csv格式保存。
- 如需对扫描结果进行绘图，运行plot_scan.py，注意修改运行时参数为所需要绘图的csv文件。

## 目前仍存在的问题
*revision:2026.10.30 14：00，宋品逢*
- 由于扫描顺序和绘图顺序的问题，扫描出来的图像是倒置的。
- 扫描出的图像与显示差异较大，扫描时各项参数仍需调整。
- 目前只对小圆柱进行了扫描，扫描结果见img_output文件夹，可供参考。目前项目中的各参数均适配小圆柱，其他物体参数还不确定。



# 以下为AI自动生成内容
## 文件说明

| 文件 | 功能 |
| --- | --- |
| `scan_devices.py` | 通过 PyVISA 发现仪器，并扫描指定局域网网段的 SCPI 端口。 |
| `read_peak_test.py` | 连接 R&S FSW-50，执行峰值搜索并读取频率和功率。 |
| `scan_top.py` | 每次移动机械台后读取一次频谱峰值，并将位置、频率和功率保存为 CSV。 |
| `pyMcc.py` | 提供 `MoCtrlCard` 运动控制接口，包括串口/网络连接、位置和状态查询、单轴/轴组运动等。 |
| `test_move.py` | 交互式单轴相对运动测试：选择串口和轴号，输入距离和速度，确认后执行并监测运动。 |
| `return_origin.py` | 检测前将机械台依次移动到本次实验的 X、Y 中心绝对位置，支持直接运行或导入函数调用。 |
| `requirements.txt` | Python 第三方依赖清单。 |

`__pycache__` 是 Python 自动生成的缓存目录，已通过 `.gitignore` 排除，无需下载或提交。

## 环境与依赖

需要 Python 3，以及相应的实验仪器或运动控制器。串口连接需要系统能够识别控制器的 COM 端口，必要时先安装设备对应的驱动。

```powershell
git clone https://github.com/applepie6657/THz_imaging.git
cd THz_imaging
python -m pip install -r requirements.txt
```

依赖包括：

- `pyvisa`、`pyvisa-py`：仪器通信，使用 `@py` 后端。
- `pyserial`：运动控制器串口通信，代码中的导入名称为 `serial`。

部分 VISA 资源发现功能可能需要额外的网络依赖或系统配置。

## 仪器发现与峰值读取

1. 将电脑和仪器连接到可互通的实验局域网。
2. 按实验环境修改 `scan_devices.py` 中的目标 IP/端口，以及 `read_peak_test.py` 中的 `ADDRESS`。
3. 根据需要分别运行：

```powershell
python scan_devices.py
python read_peak_test.py
```

默认 IP 和网段是实验配置示例。请仅在有权访问的网络和仪器上扫描。峰值读取脚本会更改仪器的 Marker 设置。

## 机械台单轴运动测试

确保 `test_move.py` 与 `pyMcc.py` 位于同一目录，然后运行：

```powershell
python test_move.py
```

按照提示选择控制器的 COM 端口、轴号（脚本标注为 `0-X`、`1-Y`、`2-Z`、`3-T`），输入带正负号的相对距离和正数速度。核对参数后输入 `YES`，程序才会发送运动指令。

移动距离的数值单位为毫米（mm）：输入 `1` 对应实际移动 `1 mm`，输入 `10` 对应 `10 mm`；正负号表示移动方向，例如 `-1` 表示沿负方向移动 `1 mm`。此说明仅针对移动距离，速度单位需另行确认。

运行前须确认实际轴映射、速度的物理单位、行程和运动方向，并保持运动区域空旷。脚本在等待超过 60 秒或收到 `Ctrl+C` 时会尝试发送急停指令；通信失败时软件急停可能无法送达，操作时应能使用设备的硬件急停。

## WASD 手动控制机械台

运行 `manual_stage_control.py` 后选择已检测到的控制器串口，并输入 `YES` 确认。程序只在控制台窗口有焦点时读取按键；每按一次键执行一个相对步进，运动完成后再接受下一次按键：

- `W` / `S`：Y 轴正向 / 负向移动。
- `A` / `D`：X 轴负向 / 正向移动。
- `Q`：退出控制。
- `Ctrl+C`：尝试停止 X、Y 两轴并退出。

步距和速度可在脚本顶部的 `X_STEP_DISTANCE`、`Y_STEP_DISTANCE`、`VELOCITY` 中修改；默认步距为 `0.1`，默认速度为 `1.0`，加速度 `0.0` 表示使用控制器参数。每次按键是有限距离运动，不是按住持续点动。启动前确认步距、轴方向、速度、行程和硬件急停可用；软件急停无法替代硬件急停。

## 电机移动与频谱数据扫描

`scan_top.py` 默认在扫描前调用 `return_origin.py` 的 `return_to_origin()`，依次将 X、Y 轴移动到配置的实验默认位置，然后按蛇形路径扫描 X/Y 矩形网格并读取每个测点的频谱仪 Marker 1 峰值。此操作不清零坐标、不执行硬件回零。运行前确认 `return_origin.py` 中的原点坐标和速度适用于当前机械台及坐标系，并确认运动区域和行程安全。若不需要扫描前回到原点，可在 `scan_top.py` 将 `RETURN_TO_ORIGIN` 设为 `False`。

直接编辑 `scan_top.py` 文件顶部的配置参数（串口、X/Y 点数、X/Y 步距、速度、加速度、超时和 VISA 地址），然后运行：

```powershell
python scan_top.py
```

扫描从开始时的当前位置（若启用回原点，则为配置的原点）作为网格首点。每轴的覆盖长度为 `(点数 - 1) × 步距绝对值`，因此点数设为 `1` 时该轴不移动；步距正负号设置方向。扫描数据自动以带时间戳的 CSV 文件保存到项目内的 `img_output` 文件夹，每行包含网格行列、X/Y 位置、步距、峰值频率和功率；程序只在控制台报告执行进度和错误。加速度设为 `0` 时使用控制器保存的参数。所有运动参数应先以低速、小步距验证，并确认行程、方向和硬件急停可用。

### 绘制扫描图像

`plot_scan.py` 根据 CSV 中的 `x_position`、`y_position` 和 `power_dbm` 绘制功率分布图。坐标轴范围和网格间距由文件中的实际坐标推导，支持不同扫描范围和步距；缺失的测点保持空白，不进行插值。图中白色线条按 CSV 写入顺序连接测点，并以绿色、青色标出起点和终点，因此能显示蛇形扫描的往返方向；底图仍按实际坐标放置每个测点，不会因蛇形往返而镜像或错位。默认使用第 2 至第 98 百分位设置颜色范围，降低少数异常值对整体对比度的影响；颜色条仍以测量值 dBm 标注。可指定其他百分位范围：

```powershell
python plot_scan.py img_output\scan_top_20261030_125706.csv
python plot_scan.py img_output\scan_top_20261030_125706.csv --percentiles 0 100 -o scan.png
```

默认图片保存在 CSV 同目录并使用相同文件名的 `.png` 后缀。功率字段是对数单位 dBm，应直接按 dBm 展示，不要把负 dBm 值当作线性强度；百分位仅用于颜色映射的显示范围，CSV 原始数据不会被修改。运行前安装 `requirements.txt` 中新增的 NumPy 和 Matplotlib 依赖。
## 检测前恢复机械台中心位置

`return_origin.py` 用于在检测前将机械台恢复到本次实验的检测中心。当前设定的中心为控制器坐标系中的绝对位置，长度单位为毫米（mm）：

| 轴 | 轴号 | 中心绝对位置 |
| --- | --- | --- |
| X | 0 | -3.7460 mm |
| Y | 1 | -52.2690 mm |

该操作先移动 X 轴，再移动 Y 轴，使用绝对位置运动指令；不会将当前坐标清零，也不执行硬件回零。运行前应确认控制器当前坐标系与记录中心位置时一致。实验中心变更时，请修改文件中的 `ORIGIN_X` 和 `ORIGIN_Y`。

### 直接运行

确保 `return_origin.py` 与 `pyMcc.py` 位于同一目录：

```powershell
python return_origin.py
```

按提示输入控制器串口（例如 `COM3`），核对当前位置、目标位置和运动范围后输入 `YES`。直接运行默认采用 `X_SPEED = 10`、`Y_SPEED = 10`；速度的物理单位需结合控制器配置确认。

### 在其他文件中调用

在同一目录的 Python 文件中导入并调用：

```python
from return_origin import return_to_origin

return_to_origin(
    com_port="COM3",
    x_speed=10,
    y_speed=10
)
```

函数签名为 `return_to_origin(com_port, x_speed, y_speed, timeout=120, confirm=True, verbose=True)`：`timeout` 为单轴运动超时时间（秒）；默认 `confirm=True`，通过函数调用时也会要求输入 `YES`。`verbose=False` 可关闭详细过程打印。返回 `True` 表示复位成功，返回 `False` 表示取消或失败。`scan_top.py` 会在启动扫描前调用该函数，关闭交互确认和详细打印，并在复位失败时停止扫描。

程序按每轴最终位置误差不超过 `0.01 mm` 判断到位。运行期间应保持运动区域空旷；不要将关闭串口连接视为停止运动，必要时使用设备硬件急停。

## 其他运动控制示例

- `pyMcc.py`：通常通过 `from pyMcc import MoCtrlCard` 导入。直接运行此文件会进入内置硬件测试，默认使用 `COM3`，并包含轴组相对运动指令；请先检查文件末尾的端口、测试分支和运动参数。

当前脚本仍需结合实际硬件验证，上传仓库不代表已经完成设备联调。

## 许可

本项目采用 MIT 许可证，具体见 `LICENSE`。外部来源代码如有单独的许可或版权要求，应同时遵守其原始条款。
