# THz_imaging

太赫兹成像实验相关的仪器发现与频谱峰值读取脚本。

## 文件

- `scan_devices.py`：通过 PyVISA 发现仪器，并扫描指定局域网网段的 SCPI 端口。
- `read_peak_test.py`：连接 R&S FSW-50，执行峰值搜索并读取频率和功率。

## 使用方法

需要 Python 3 和可通过局域网访问的实验仪器。

```powershell
python -m pip install -r requirements.txt
python scan_devices.py
python read_peak_test.py
```

运行前，请按实验环境修改 `scan_devices.py` 中的 `TARGET_SUBNET` 和 `read_peak_test.py` 中的 `ADDRESS`。默认值为实验局域网示例地址。请仅在有权访问的网络和仪器上运行扫描；峰值读取脚本会更改仪器的 Marker 设置。

使用 `pyvisa-py` 后端；部分资源发现功能可能需要额外的网络依赖或系统配置。当前代码需在实际仪器上验证。

## 许可

本项目采用 MIT 许可证，允许使用、修改和再分发，具体见 `LICENSE`。
