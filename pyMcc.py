import serial.tools.list_ports
import serial
import time
import threading
import struct
import sys
import socket

class MoCtrlCard:
    '''Summaty

    Python libary for 6 Axes Motion Controller

    Attributes:
        FUNRESOK:  A Const stand for Operation is operated successfully
        FUNRESERR: A Const stand for Operation is operated failed

    '''
    #__slots__(self, FUNRESOK, FUNRESERR, __VERSION__, )
    FUNRESOK = 1
    FUNRESERR = 2
    __VERSION__ = 0x20220319    # pthon modular version
    __PortType = 0      # 0: Invalid Port; 1: RS232 2: NetPort
    __DataRevLen = 0    # the receive data lenth
    __SemCom = threading.Semaphore(1)       # comunicate semaphore
    __SemTimeOut = 1    # time for semaphore acquire action

    MAX_AXIS_NUM = 4        # max axis count
    PARA_NUM_PER_AXIS = 10  # parameter count per axis
    PARA_SUM = MAX_AXIS_NUM * PARA_NUM_PER_AXIS     # parameter sum count

    def __init__(self, timeOut = 1):
        self.__comPort = serial.Serial()
        self.__SemTimeOut = timeOut
        self.__netHandle = 0

    def __MoCtrCard_GetManOpCmndBytes(self, cmndCode, subCmnd, axisId, spdDir, posCmnd, velCmnd, accCmnd):
        # https://segmentfault.com/a/1190000013959213?utm_source=channel-hottest
        ret = self.FUNRESOK
        BA = bytearray(b"")

        try:
            frameLen = 20
            str = struct.pack('8B4B3f', 0xAA, frameLen, 0x00, ~frameLen & 0xFF, \
                0x00, cmndCode & 0xFF, frameLen, 0x00, \
                subCmnd, axisId, spdDir, 0x00, posCmnd, velCmnd, accCmnd)

            BA = bytearray(str)
            #caculate the check sum
            tmpCheckSum = 0
            for i in range(4, frameLen + 4, 1):
                tmpCheckSum += BA[i]

            BA[4] = tmpCheckSum & 0xFF
        except Exception as e:
            ret = self.FUNRESERR
            print ("GetManOpCmndBytes Exception! ", e)

        return ret, BA

    # get reset position command bytes array
    def __MoCtrCard_GetResetPositionCmndBytes(self, cmndCode, subCmnd, axisId, posCmnd):
        # https://segmentfault.com/a/1190000013959213?utm_source=channel-hottest
        ret = self.FUNRESOK
        BA = bytearray(b"")

        try:
            frameLen = 12
            str = struct.pack('8B4B1f', 0xAA, frameLen, 0x00, ~frameLen & 0xFF, \
                0x00, cmndCode & 0xFF, frameLen, 0x00, \
                subCmnd, axisId, 0x00, 0x00, posCmnd)

            BA = bytearray(str)
            #caculate the check sum
            tmpCheckSum = 0
            for i in range(4, frameLen + 4, 1):
                tmpCheckSum += BA[i]

            BA[4] = tmpCheckSum & 0xFF
        except Exception as e:
            ret = self.FUNRESERR
            print ("GetResetPositionCmndBytes Exception! ", e)

        return ret, BA

    def __MoCtrCard_GetSetOutputCmndBytes(self, cmndCode, subCmnd, outputIndex):
        ret = self.FUNRESOK
        BA = bytearray(b"")

        try:
            frameLen = 8
            str = struct.pack('8B4B', 0xAA, frameLen, 0x00, ~frameLen & 0xFF, \
                0x00, cmndCode & 0xFF, frameLen, 0x00, \
                subCmnd, outputIndex, 0x00, 0x00)

            BA = bytearray(str)
            #caculate the check sum
            tmpCheckSum = 0
            for i in range(4, frameLen + 4, 1):
                tmpCheckSum += BA[i]

            BA[4] = tmpCheckSum & 0xFF
        except Exception as e:
            ret = self.FUNRESERR
            print ("GetSetOutputCmndBytes Exception! ", e)

        return ret, BA

    def __MoCtrCard_GetSendParameterCmndBytes(self, cmndCode, AxisId, ParaIndex, ParaVal, ValMod):
        ret = self.FUNRESOK
        BA = bytearray(b"")

        try:
            frameLen = 12
            # parameter type is float
            if(0 == ValMod):
                str = struct.pack('8B4B1f', 0xAA, frameLen, 0x00, ~frameLen & 0xFF, \
                    0x00, cmndCode & 0xFF, frameLen, 0x00, \
                    AxisId, ParaIndex, 0x00, 0x00, ParaVal)
            # parameter type is Int32
            else:
                str = struct.pack('8B4B1l', 0xAA, frameLen, 0x00, ~frameLen & 0xFF, \
                    0x00, cmndCode & 0xFF, frameLen, 0x00, \
                    AxisId, ParaIndex, 0x00, 0x00, ParaVal)

            BA = bytearray(str)
            #caculate the check sum
            tmpCheckSum = 0
            for i in range(4, frameLen + 4, 1):
                tmpCheckSum += BA[i]

            BA[4] = tmpCheckSum & 0xFF
        except Exception as e:
            ret = self.FUNRESERR
            print ("__MoCtrCard_GetSendParameterCmndBytes Exception! ", e)

        return ret, BA

    def __MoCtrCard_GetSetFunEnableCmndBytes(self, cmndCode, axisId, funType, enable):
        ret = self.FUNRESOK
        BA = bytearray(b"")

        try:
            frameLen = 8
            str = struct.pack('8B4B', 0xAA, frameLen, 0x00, ~frameLen & 0xFF, \
                0x00, cmndCode & 0xFF, frameLen, 0x00, \
                axisId, funType, enable, 0x00)

            BA = bytearray(str)
            #caculate the check sum
            tmpCheckSum = 0
            for i in range(4, frameLen + 4, 1):
                tmpCheckSum += BA[i]

            BA[4] = tmpCheckSum & 0xFF
        except Exception as e:
            ret = self.FUNRESERR
            print ("GetSetFunEnableCmndBytes Exception! ", e)

        return ret, BA

    def __MoCtrCard_GetGroupMoveCmndBytes(self, cmndCode, GCode, AxisEn, CmndPos, CmndVel, CmndAcc, Radius, DelayTime):
        ret = self.FUNRESOK
        BA = bytearray(b"")

        try:
            # check if Axis is Checked
            AxisEnBit = 0
            for indx in range(0, 4, 1):
                if(AxisEn[indx] > 0):
                    AxisEnBit |= (1 << indx)
            
            frameLen = 64
            str = struct.pack('8B2H14f', 0xAA, frameLen, 0x00, ~frameLen & 0xFF, \
                0x00, cmndCode & 0xFF, frameLen, 0x00, \
                GCode, AxisEnBit, \
                CmndPos[0], CmndPos[1], CmndPos[2], CmndPos[3], \
                CmndVel[0], CmndVel[1], CmndVel[2], CmndVel[3], \
                CmndAcc[0], CmndAcc[1], CmndAcc[2], CmndAcc[3], \
                Radius, DelayTime)

            BA = bytearray(str)
            #caculate the check sum
            tmpCheckSum = 0
            for i in range(4, frameLen + 4, 1):
                tmpCheckSum += BA[i]

            BA[4] = tmpCheckSum & 0xFF
        except Exception as e:
            ret = self.FUNRESERR
            print ("GetGroupMoveCmndBytes Exception! ", e)

        return ret, BA

    def __MoCtrCard_GetNoSubCmndBytes(self, cmndCode):
        ret = self.FUNRESOK
        BA = bytearray(b"")

        try:
            frameLen = 4
            str = struct.pack('8B', 0xAA, frameLen, 0x00, ~frameLen & 0xFF, \
                0x00, cmndCode & 0xFF, frameLen, 0x00)

            BA = bytearray(str)
            #caculate the check sum
            tmpCheckSum = 0
            for i in range(4, frameLen + 4, 1):
                tmpCheckSum += BA[i]

            BA[4] = tmpCheckSum & 0xFF

        except Exception as e:
            ret = self.FUNRESERR
            print ("GetManOpCmndBytes Exception! ", e)

        return ret, BA

    def __MoCtrCard_GetAskInfoCmndBytes(self, cmndCode, axisId, paraIndex):
        ret = self.FUNRESOK
        BA = bytearray(b"")

        try:
            frameLen = 6
            str = struct.pack('8B2B', 0xAA, frameLen, 0x00, ~frameLen & 0xFF, \
                0x00, cmndCode & 0xFF, frameLen, 0x00, \
                axisId, paraIndex)

            BA = bytearray(str)
            #caculate the check sum
            tmpCheckSum = 0
            for i in range(4, frameLen + 4, 1):
                tmpCheckSum += BA[i]

            BA[4] = tmpCheckSum & 0xFF
        except Exception as e:
            ret = self.FUNRESERR
            print ("__MoCtrCard_GetAskInfoCmndBytes Exception! ", e)

        return ret, BA

    def __MoCtrCard_GetBytesFunResAndFrame(self, cmndBuff, nDtWanted):
        ret = self.FUNRESERR
        DATA = ""

        if(True == self.__SemCom.acquire(timeout=1)):

            if (1 == self.__PortType):
                try:
                    #self.DATA = ser.read(ser.in_waiting).decode("gbk")
                    self.__comPort.flush()          # clear Input and Output Buffer
                    self.__comPort.write(cmndBuff)  # send command buffer
                    tmpDtWanted = nDtWanted + 4     # +4 is the Frame Head
                    DATA = self.__comPort.read(tmpDtWanted + 1) #+1 is the check sum
                    #print(len(self.DATA))
                    if(len(DATA) == (tmpDtWanted + 1)):
                        #caclute the check sum, and decode the command state
                        tmpCheckSum = 0
                        for i in range(0, tmpDtWanted, 1):
                            tmpCheckSum += DATA[i]
                        
                        #check the check sum
                        if(DATA[tmpDtWanted] == (tmpCheckSum & 0xFF)):
                            self.__DataRevLen = DATA[2]
                            ret = self.FUNRESOK if (0 == DATA[3]) else self.FUNRESERR
                except Exception as e:
                    print ("RS232 Exception! ", e)

            elif(2 == self.__PortType):
                try:
                    #self.__netHandle.send(bytes(cmndBuff, encoding='utf-8'))
                    self.__netHandle.send(cmndBuff)
                    tmpDtWanted = nDtWanted + 4
                    DATA = self.__netHandle.recv(tmpDtWanted + 1)
                    if(len(DATA) == (tmpDtWanted + 1)):
                        #caclute the check sum, and decode the command state
                        tmpCheckSum = 0
                        for i in range(0, tmpDtWanted, 1):
                            tmpCheckSum += DATA[i]
                        
                        #check the check sum
                        if(DATA[tmpDtWanted] == (tmpCheckSum & 0xFF)):
                            self.__DataRevLen = DATA[2]
                            ret = self.FUNRESOK if (0 == DATA[3]) else self.FUNRESERR

                except Exception as e:
                    print ("Net Socket Exception! ", e)
                
            else:
                pass

            self.__SemCom.release()
        return ret, DATA

    def __MoCtrCard_GetBytesDecodeFunRes(self, cmndBuff, nDtWanted):
        ret = self.FUNRESERR
        DATA = ""

        if(True == self.__SemCom.acquire(timeout=1)):

            if (1 == self.__PortType):
                try:
                    #self.DATA = ser.read(ser.in_waiting).decode("gbk")
                    self.__comPort.flush()          # clear Input and Output Buffer
                    self.__comPort.write(cmndBuff)  # send command buffer
                    tmpDtWanted = nDtWanted + 4     # +4 is the Frame Head
                    DATA = self.__comPort.read(tmpDtWanted + 1) #+1 is the check sum
                    #print(len(self.DATA))
                    if(len(DATA) == (tmpDtWanted + 1)):
                        #caclute the check sum, and decode the command state
                        tmpCheckSum = 0
                        for i in range(0, tmpDtWanted, 1):
                            tmpCheckSum += DATA[i]
                        
                        #check the check sum
                        if(DATA[tmpDtWanted] == (tmpCheckSum & 0xFF)):
                            self.__DataRevLen = DATA[2]
                            ret = self.FUNRESOK if (0 == DATA[3]) else self.FUNRESERR
                except Exception as e:
                    print ("RS232 Exception! ", e)

            elif(2 == self.__PortType):
                try:
                    #self.__netHandle.send(bytes(cmndBuff, encoding='utf-8'))
                    self.__netHandle.send(cmndBuff)
                    tmpDtWanted = nDtWanted + 4
                    DATA = self.__netHandle.recv(tmpDtWanted + 1)
                    if(len(DATA) == (tmpDtWanted + 1)):
                        #caclute the check sum, and decode the command state
                        tmpCheckSum = 0
                        for i in range(0, tmpDtWanted, 1):
                            tmpCheckSum += DATA[i]
                        
                        #check the check sum
                        if(DATA[tmpDtWanted] == (tmpCheckSum & 0xFF)):
                            self.__DataRevLen = DATA[2]
                            ret = self.FUNRESOK if (0 == DATA[3]) else self.FUNRESERR

                except Exception as e:
                    print ("Net Socket Exception! ", e)

            else:
                pass

            self.__SemCom.release()
        return ret

    def __MoCtrCard_GetFloatValue(self, RevBuff, nCnt):
        ret = self.FUNRESOK
        retPos = [0.0, 0.0, 0.0, 0.0]
        try:
            if(1 == nCnt):
                unPackVal = struct.unpack("4B1f1B", RevBuff)
                retPos[0] = unPackVal[4]
            elif(2 == nCnt):
                unPackVal = struct.unpack("4B2f1B", RevBuff)
                retPos[0] = unPackVal[4]
                retPos[1] = unPackVal[5]
            elif(3 == nCnt):
                unPackVal = struct.unpack("4B3f1B", RevBuff)
                retPos[0] = unPackVal[4]
                retPos[1] = unPackVal[5]
                retPos[2] = unPackVal[6]
            elif(4 == nCnt):
                unPackVal = struct.unpack("4B4f1B", RevBuff)
                retPos[0] = unPackVal[4]
                retPos[1] = unPackVal[5]
                retPos[2] = unPackVal[6]
                retPos[3] = unPackVal[7]
            else:
                ret = self.FUNRESERR
        except Exception as e: 
            ret = self.FUNRESERR
            print("error!", e)
        return ret, retPos

    def __MoCtrCard_GetIntValue(self, RevBuff, nCnt):
        ret = self.FUNRESOK
        retVal = [0, 0, 0, 0]
        try:
            if(1 == nCnt):
                unPackVal = struct.unpack("4B1i1B", RevBuff)
                retVal[0] = unPackVal[4]
            elif(2 == nCnt):
                unPackVal = struct.unpack("4B2i1B", RevBuff)
                retVal[0] = unPackVal[4]
                retVal[1] = unPackVal[5]
            elif(3 == nCnt):
                unPackVal = struct.unpack("4B3i1B", RevBuff)
                retVal[0] = unPackVal[4]
                retVal[1] = unPackVal[5]
                retVal[2] = unPackVal[6]
            elif(4 == nCnt):
                unPackVal = struct.unpack("4B4i1B", RevBuff)
                retVal[0] = unPackVal[4]
                retVal[1] = unPackVal[5]
                retVal[2] = unPackVal[6]
                retVal[3] = unPackVal[7]
            else:
                ret = self.FUNRESERR
        except Exception as e: 
            ret = self.FUNRESERR
            print("error!", e)
            
        return ret, retVal

    # 获取可用串口列表
    def MoCtrCard_GetAvailablePorts(self):
        '''Get the Avaialabe RS232 Port On PC

        Get the avaiable RS232 Port on PC, include RS232 and USBRS232. Choose the Port link to the MCC

        Args:
        None

        Returns:
        Avaiable RS232 Ports list

        '''
        port_list = list(serial.tools.list_ports.comports())
        '''
        print(port_list)
        if len(port_list) == 0:
            print("无可用串口！")
        else:
            for i in range(0, len(port_list)):
                print(port_list[i])
        '''
        return port_list

    # 卸载运动控制卡
    def MoCtrCard_UnLoad(self):
        '''Unload the MCC Lib

        Unload the Motion Control Card Libiary, close the RS232 Port or Net Port

        Args:
        None

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESOK
        if (self.__comPort.is_open()):
            self.__comPort.close()

        if (self.self.__netHandle):
            self.__netHandle.close()

        return ret

    # 初始化运动控制卡
    def MoCtrCard_Initial(self, portName):
        '''Init the MCC Lib

        Init the Motion Control Card Libiary with RS232 Name like "COM1"
        RS232 parameters is 115200 N 8 1, read timeout and write time is 300ms

        Args:
        portName(str): RS232 Port name such as "COM1"

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        try:
            # 打开串口，并得到串口对象
            if (self.__comPort.is_open):
                self.__comPort.close()
            
            self.__comPort = serial.Serial(port = portName, baudrate = 115200, timeout = 0.3)
            if(self.__comPort.is_open):
                self.__PortType = 1
                ret = self.FUNRESOK
            # 判断是否成功打开
            #if(ser.is_open):
            #   ret = True
            #   th = threading.Thread(target=read_data, args=(ser,)) # 创建一个子线程去等待读数据
            #   th.start()
        except Exception as e: 
            print("error!", e)
    
        return ret

    def MoCtrCard_InitialNet(self, ipaddr, ipport):
        '''Init the MCC Lib

        Init the Motion Control Card Libiary with TCP Socket by IP Address and IP Port
        
        Args:
        ipaddr(str): IP Address of TCP Server such as '192.168.0.1'
        ipport(int): IP Port of TCP Server

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        try:
            if(self.__netHandle):
                self.__netHandle.close()
            
            self.__netHandle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__netHandle.connect((ipaddr, ipport))
            self.__PortType = 2
            ret = self.FUNRESOK
            '''
            while 1:
                msg = input('please input')
                # 防止输入空消息
                if not msg:
                    continue
                p.send(msg.encode('utf-8'))  # 收发消息一定要二进制，记得编码
                if msg == '1':
                    break
            p.close()
            '''
        except Exception as e: 
            print("error!", e)

        return ret

    # 相对运动
    def MoCtrCard_MCrlAxisRelMove(self, AxisId, DistCmnd, VCmnd, ACmnd = 0.0):
        '''Move some axis by relative distance

        move some axis by a relative distance, the sign of the parameter distance stand for move direction

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        DistCmnd(float):Relative distance, the sign of it stands for move direction
        VCmnd(float):Command Velocity
        ACmnd(float):Command Accelerate, default value is 0.0, means used the accelerate parameter in the card

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0x03, AxisId, 0x00, DistCmnd, VCmnd, ACmnd)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 绝对运动
    def MoCtrCard_MCrlAxisAbsMove(self, AxisId, PosCmnd, VCmnd, ACmnd = 0.0):
        '''Move axis to some absolute position

        move axis to some absolute position

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        PosCmnd(float):Absolute position
        VCmnd(float):Command Velocity
        ACmnd(float):Command Accelerate, default value is 0.0, means used the accelerate parameter in the card

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0x04, AxisId, 0x00, PosCmnd, VCmnd, ACmnd)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 速度运动
    def MoCtrCard_MCrlAxisAtSpd(self, AxisId, VCmnd, ACmnd = 0.0):
        '''Move axis at some speed

        move axis at some speed

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        VCmnd(float):Command Velocity
        ACmnd(float):Command Accelerate, default value is 0.0, means used the accelerate parameter in the card

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0x06, AxisId, 0, 0.0, VCmnd, ACmnd)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 轴暂停运动
    def MoCtrCard_PauseAxisMov(self, AxisId):
        '''Pause the axis movement

        Pause the axis movement, the restart the movement by MoCtrCard_RestartAxisMov function

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0x82, AxisId, 0x00, 0.0, 0.0, 0.0)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 启动回零运动
    def MoCtrCard_SeekZero(self, AxisId, VCmnd, ACmnd = 0.0):
        '''start the axis to seek zero

        Start the axis to seek zero, the zero position is the position when HOME input signal trigged

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        VCmnd(float):Command home velocity
        ACmnd(float):Command Accelerate, default value is 0.0, means used the accelerate parameter in the card

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0xA1, AxisId, 0x00, 0.0, VCmnd, ACmnd)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 取消回零运动
    def MoCtrCard_CancelSeekZero(self, AxisId):
        '''cancle the home process

        quite the home process

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-A, 4-B, 5-C

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0xA2, AxisId, 0x00, 0.0, 0.0, 0.0)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 重置坐标系
    def MoCtrCard_ResetCoordinate(self, AxisId, PosRest):
        '''reset the axis position value to PosRest value

        reset the axis position to PosRest value without motion

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        PosRest(float):Axis reset position

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetResetPositionCmndBytes(0xF8, 0x01, AxisId, PosRest)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret
    
    # 重置编码器值
    def MoCtrCard_SetEncoderPos(self, AxisId, EncoderPos):
        '''set encoder count, not support

        set some axis's encoder count to EncoderPos

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        EncoderPos(int):Encoder count

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        return self.FUNRESERR

    # 重置Z信号
    def MoCtrCard_RstZ(self, AxisId):
        '''reset Z pulse of encoder

        not support ont 4Axis platform

        reset the encoder Z pulse signle in order to receive next one

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        EncoderPos(int):Encoder count

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''

        return self.FUNRESERR

    # 退出运动
    def MoCtrCard_QuiteMotionControl(self):
        '''quite the motion movement

        quite the motion movement and reset the motion card state

        Args:
        null

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0x91, 0, 0x00, 0.0, 0.0, 0.0)
        if(self.FUNRESOK == ret):
            ret =  self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 恢复暂停的轴运动
    def MoCtrCard_ReStartAxisMov(self, AxisId):
        '''restart axis movement paused

        restart axis movement paused by MoctrCard_PauseAxisMov function

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0x90, AxisId, 0x00, 0.0, 0.0, 0.0)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 急停止轴运动
    def MoCtrCard_EmergencyStopAxisMov(self, AxisId):
        '''emergency stop the axis movement

        emergency stop the axis movement by reset the axis interplate FIFO

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0x80, AxisId, 0x00, 0.0, 0.0, 0.0)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 停止运动
    def MoCtrCard_StopAxisMov(self, AxisId, fAcc = 0.0):
        '''parameter stop the axis movement with the decelerate

        stop the axis movement with decelerate

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        fAcc(float):Delecerate parameter

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0x81, AxisId, 0x00, 0.0, 0.0, fAcc)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 动态改变运动参数
    def MoCtrCard_ChangeAxisMovPara(self, AxisId, VCmnd, ACmnd):
        '''change axis motion parameters dynamic

        change the axis motion parameters during the movement

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        fAcc(float):Delecerate parameter

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetManOpCmndBytes(0xF4, 0x05, AxisId, 0x00, 0.0, VCmnd, ACmnd)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 保存参数至控制器的 ROM 区
    def MoCtrCard_SaveSystemParaToROM(self):
        '''save the paramter to rom in the MCU

        save the parameter to rom in case of lost by losing power

        Args:
        None

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetNoSubCmndBytes(0xFE)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 设置输出
    def MoCtrCard_SetOutput(self, OutputIndex, OutputVal):
        '''set output state

        set some output to state OutputVal 

        Args:
        OutputIndex(byte):Output index, 0 - 31
        OutputVal(byte):1 - turn on the output; 0 - turn off the output
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        tmpSubCmnd = 0x01 if(OutputVal > 0) else 0x02
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetSetOutputCmndBytes(0xF9, tmpSubCmnd, OutputIndex)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 设置某个功能是否使能
    def MoCtrCard_EnableSomeFunction(self, AxisId, FunType, bEnable):
        '''enable or disable some function defined by FunType parameter

        enable or disable some function, such as input trig level

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        FunType(byte):Function Index
        bEnable(byte):0 - disable some function; 1 - enable some function
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetSetFunEnableCmndBytes(0xFB, AxisId, FunType, bEnable)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 设置摇杆始能
    def MoCtrCard_SetJoyStickEnable(self, AxisId, bEnable):
        '''enable or disable JoyStick

        enable or disable the JoyStick Function

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        bEnable(byte):0 - disable Joystick function; 1 - enable Joystick function
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        return self.MoCtrCard_EnableSomeFunction(AxisId, 5, bEnable)

    # 设置软件限位功能
    def MoCtrCard_EnableSoftLimitFunction(self, AxisId, bEnable):
        '''enable or disable soft limit function

        enable or disable soft limit function

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        bEnable(byte):0 - disable software limit function; 1 - enable software limit function
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        return self.MoCtrCard_EnableSomeFunction(AxisId, 0x20, bEnable)

    # 设置硬件限位功能
    def MoCtrCard_EnableHardLimitFunction(self, AxisId, bEnable):
        '''enable or disable hard limit function

        enable or disable hard limit function

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        bEnable(byte):0 - disable Hard limit function; 1 - enable Hard limit function
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        return self.MoCtrCard_EnableSomeFunction(AxisId, 0x40, bEnable)

    # 设置补偿功能
    def MoCtrCard_EnableCompensateFunction(self, AxisId, bEnable):
        '''enable or disable compensate function

        enable or disable compensate function

        not support on 4Axis platform

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        bEnable(byte):0 - disable compensate function; 1 - enable compensate function
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        return self.FUNRESERR

    # 设限位信号级性
    def MoCtrCard_SetHardLimitSigTrigLev(self, AxisId, OpenOrClose):
        '''set limit signal trig level function

        set limit signal trig level function

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        bEnable(byte):0 - open; 1 - close
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        return self.MoCtrCard_EnableSomeFunction(AxisId, 0x02, OpenOrClose)

    # 设原点信号级性
    def MoCtrCard_SetHomeSigTrigLev(self, AxisId, OpenOrClose):
        '''set original signal trig level function

        set original signal trig level function

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        bEnable(byte):0 - open; 1 - close
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        return self.MoCtrCard_EnableSomeFunction(AxisId, 0x03, OpenOrClose)

    # 设置急停止功有
    def MoCtrCard_SetEmergencyStopEnable(self, AxisId, bEnable):
        '''enable or disable external EStop function

        enable or disable external EStop function

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        bEnable(byte):0 - disable; 1 - enable
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        return self.MoCtrCard_EnableSomeFunction(AxisId, 0x04, bEnable)

    
    # 测试
    def MoCtrCard_Test(self):
        '''test function

        test function used for python application

        Args:
        AxisId(byte):None
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        value(INT):test value is {1,2,3,4) for value[0/1/2/3]
        '''

        testValue = [0, 0, 0, 0]

        testValue[0] = 1
        testValue[1] = 2
        testValue[2] = 3
        testValue[3] = 4

        return self.FUNRESSOK, testValue

    # 轴组绝对运动
    def MoCtrCard_MCrlGroupAbsMove(self, bAxisEn, fPos, fSpd, fAcc, Delay = 0.0):
        '''move group axes to some absolute position

        move group axes to some absolute position, the axes of the group stop and move simultaneously

        Args:
        bAxisEn(list):Axes choose byte, 0 - not choose, 1 - choose; bAxisEn[0] = 0, X Axis not choose, = 1, X Axis choose
        fPos(list):Axes command position for each axis
        fSpd(list):Axes movement command speed for each axis
        fAcc(list):Axis movement command acceletate for each axis
        Delay(float):Delay time
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetGroupMoveCmndBytes(0xF3, 0x01, bAxisEn, fPos, fSpd, fAcc, 0.0, Delay)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 轴组相对运动
    def MoCtrCard_MCrlGroupRelMove(self, bAxisEn, fDist, fSpd, fAcc, Delay = 0.0):
        '''move group axes by a relative distance

        move group axes by a relative distance, the axes of the group stop and move simultaneously

        Args:
        bAxisEn(list):Axes choose byte, 0 - not choose, 1 - choose; bAxisEn[0] = 0, X Axis not choose, = 1, X Axis choose
        fDist(list):Axes command distance for each axis
        fSpd(list):Axes movement command speed for each axis
        fAcc(list):Axis movement command acceletate for each axis
        Delay(float):Delay time
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetGroupMoveCmndBytes(0xF3, 0x81, bAxisEn, fDist, fSpd, fAcc, 0.0, Delay)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 轴组绝对 PTP 运动
    # MoCtrCard_MCrlGroupAbsMovePTP(McCard_UINT8 bAxisEn[MAX_AXIS_NUM], McCard_FP32 fPos[MAX_AXIS_NUM], McCard_FP32 fSpd[MAX_AXIS_NUM])
    def MoCtrCard_MCrlGroupAbsMovePTP(self, bAxisEn, fPos, fSpd, fAcc, Delay = 0.0):
        '''move group axes to some absolute position

        move group axes to some absolute position, the axes of the group stop and move respectively

        Args:
        bAxisEn(list):Axes choose byte, 0 - not choose, 1 - choose; bAxisEn[0] = 0, X Axis not choose, = 1, X Axis choose
        fPos(list):Axes command position for each axis
        fSpd(list):Axes movement command speed for each axis
        fAcc(list):Axis movement command acceletate for each axis
        Delay(float):Delay time
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetGroupMoveCmndBytes(0xF3, 0x00, bAxisEn, fPos, fSpd, fAcc, 0.0, Delay)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    # 轴组相对 PTP 运动
    def MoCtrCard_MCrlGroupRelMovePTP(self, bAxisEn, fDist, fSpd, fAcc, Delay = 0.0):
        '''move group axes by some relative distance

        move group axes by some  relative distance, the axes of the group stop and move respectively

        Args:
        bAxisEn(list):Axes choose byte, 0 - not choose, 1 - choose; bAxisEn[0] = 0, X Axis not choose, = 1, X Axis choose
        fPos(list):Axes command position for each axis
        fSpd(list):Axes movement command speed for each axis
        fAcc(list):Axis movement command acceletate for each axis
        Delay(float):Delay time
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetGroupMoveCmndBytes(0xF3, 0x80, bAxisEn, fDist, fSpd, fAcc, 0.0, Delay)
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    def MoCtrCard_SendPara(self, AxisId, ParaIndex, Val):
        '''write MCC parameters

        set MCC parameters by AxisId and ParaIndex. Val type is float or int according to the AxisId and ParaIndex

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        ParaIndex(byte):Parameter Index, judge the Val type according to ParaIndex
        Val(float\int):Parameter value
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        '''
        ret = self.FUNRESERR
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetSendParameterCmndBytes(0xF2, AxisId, ParaIndex, Val, 0)

        # read the value
        if(self.FUNRESOK == ret):
            ret = self.__MoCtrCard_GetBytesDecodeFunRes(tmpCmndBuf, 0)

        return ret

    def MoCtrCard_ReadPara(self, AxisId, ParaIndex):
        '''read MCC parameters

        read MCC parameters by AxisId and ParaIndex. Val type is float or int according to the AxisId and ParaIndex

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-A, 4-B, 5-C
        ParaIndex(byte):Parameter Index, judge the Val type according to ParaIndex
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        val(float\int): Value of the parameter
        '''
        ret = self.FUNRESERR
        tmpPos = []

        (ret, tmpCmndBuf) = self.__MoCtrCard_GetAskInfoCmndBytes(0xF5, AxisId, ParaIndex)
        if(self.FUNRESOK == ret):
            (ret, tmpRevBuf) = self.__MoCtrCard_GetBytesFunResAndFrame(tmpCmndBuf, 4)
            if(self.FUNRESOK == ret):
                (ret, tmpPos) = self.__MoCtrCard_GetFloatValue(tmpRevBuf, 1)

        return ret, tmpPos[0]

    # 内部函数，查询与轴相关的信息
    def __MoCtrCard_GetAxisInfomation(self, AxisId, InfoIndex):
        ret = self.FUNRESERR
        tmpPos = []

        # ask all axis position
        if(0xFF == AxisId):
            tmpParaIndx = InfoIndex + 0x80
            tmpParaCnt = 4
        else:
            tmpParaIndx = InfoIndex
            tmpParaCnt = 1

        # ask one axis position
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetAskInfoCmndBytes(0xF6, AxisId, tmpParaIndx)
        if(self.FUNRESOK == ret):
            (ret, tmpRevBuf) = self.__MoCtrCard_GetBytesFunResAndFrame(tmpCmndBuf, tmpParaCnt * 4)
            if(self.FUNRESOK == ret):
                (ret, tmpPos) = self.__MoCtrCard_GetFloatValue(tmpRevBuf, tmpParaCnt)

        return ret, tmpPos

    def __MoCtrCard_GetAxisInfomationInt(self, AxisId, InfoIndex):
        ret = self.FUNRESERR
        tmpValue = []

        # ask all axis position
        if(0xFF == AxisId):
            tmpParaIndx = InfoIndex + 0x80
            tmpParaCnt = 4
        else:
            tmpParaIndx = InfoIndex
            tmpParaCnt = 1

        # ask one axis position
        (ret, tmpCmndBuf) = self.__MoCtrCard_GetAskInfoCmndBytes(0xF6, AxisId, tmpParaIndx)
        if(self.FUNRESOK == ret):
            (ret, tmpRevBuf) = self.__MoCtrCard_GetBytesFunResAndFrame(tmpCmndBuf, tmpParaCnt * 4)
            if(self.FUNRESOK == ret):
                (ret, tmpValue) = self.__MoCtrCard_GetIntValue(tmpRevBuf, tmpParaCnt)

        return ret, tmpValue

    # 查询轴位置
    def MoCtrCard_GetAxisPos(self, AxisId):
        '''get axis current position

        get axis current position, if AxisId = 0/1/2/3/, then return the axis position at list[0]
        if AxisId = 0xFF, then return the axis position by list[0:3]

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        pos(list):pos[0:3] is axis position, if AxisId = 0/1/2/3/4/5, only pos[0] is valid, else pos[0:3] is the position array
        '''
        (ret, pos) = self.__MoCtrCard_GetAxisInfomation(AxisId, 0x00)
        return ret, pos

    # 查询轴速度
    def MoCtrCard_GetAxisSpeed(self, AxisId):
        '''get axis current speed

        get axis current speed, if AxisId = 0/1/2/3, then return the axis speed at list[0]
        if AxisId = 0xFF, then return the axis speed by list[0:3]

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        spd(list):spd[0:3] is axis speed, if AxisId = 0/1/2/3, only spd[0] is valid, else spd[0:3] is the speed array
        '''
        (ret, spd) = self.__MoCtrCard_GetAxisInfomation(AxisId, 0x01)
        return ret, spd

    # 查询轴模拟量
    def MoCtrCard_GetADValue(self, AxisId):
        '''get analog input

        get analog input which is in [0, 3.3], if AxisId = 0/1/2/3, then return just one analog input at adVal[0]
        return all the six channel analog inputs when AxisId = 0xFF, 

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        adVal(list):adVal[0:3] is analog input, if AxisId = 0/1/2/3, only adVal[0] is valid, else adVal[0:3] is the analog array
        '''
        (ret, adVal) = self.__MoCtrCard_GetAxisInfomationInt(AxisId, 0x02)
        return ret, adVal

    # 查询轴编码器值
    def MoCtrCard_GetAxisEncoder(self, AxisId):
        '''get encoder count

        not support on Axis4 platform

        get the encoder current count, if AxisId = 0/1/2/3, then return just one encoder count at encoderVal[0]
        return all the six encoder count when AxisId = 0xFF, 

        Args:
        AxisId(byte):Axis Index, 0-X, 1-Y, 2-Z, 3-T
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        encoderVal(list):encoderVal[0:3] is encoder count, if AxisId = 0/1/2/3, only encoderVal[0] is valid, else encoderVal[0:3] is the encoder array
        '''

        '''
            (ret, encoderVal) = self.__MoCtrCard_GetAxisInfomationInt(AxisId, 0x03)
        return ret, encoderVal
        '''

        return self.FUNRESERR
    # 查询NC系统状态
    def MoCtrCard_GetRunState(self):
        '''get NC runtime state

        get the NC runtime state which stand for each axes and group

        Args:
        None
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        runState(LIST INT):NC run State
        '''
        (ret, runState) = self.__MoCtrCard_GetAxisInfomationInt(0x00, 0x0B)
        return ret, runState

    # 查询输入值
    def MoCtrCard_GetInputState(self):
        '''get Inputs

        get inputs

        Args:
        None
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        inputs(INT): inputs state
        '''
        (ret, inputs) = self.__MoCtrCard_GetAxisInfomationInt(0x00, 0x05)
        return ret, inputs

    # 查询输出值
    def MoCtrCard_GetOutputState(self):
        '''get Outputs

        get outputs

        Args:
        None
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        outputs(INT): outputs state
        '''
        (ret, outputs) = self.__MoCtrCard_GetAxisInfomationInt(0x00, 0x07)
        return ret, outputs

    # 查询控制器版本号
    def MoCtrCard_GetDLLVersion(self):
        '''get python lib version
        
        get python lib version 

        Args:
        None

        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        outputs(INT): lib version
        '''
        return self.__VERSION__

    # 查询Python库版本号
    def MoCtrCard_GetCardVersion(self):
        '''get Mcc Controller version

        get Mcc Controller version

        Args:
        None
        
        Returns:
        ret(INT):1 - stand for OK; 2 - stand for ERROR
        outputs(INT): Mcc Controller version
        '''
        (ret, outputs) = self.__MoCtrCard_GetAxisInfomationInt(0x00, 0xFF)
        return ret, outputs

    # 查询轴当前是否处于运动状态
    def MoCtrCard_IsAxisRunning(self, AxisdId):
        (ret, tmpRunState) = self.MoCtrCard_GetRunState()
        tmpRunningFlag = 0

        if(self.FUNRESOK == ret):
            if (0 == AxisdId):
                tmpRunningFlag = 1 if (0x80 == (tmpRunState[0] & 0x80)) else 0
            elif (1 == AxisdId):
                tmpRunningFlag = 1 if (0x40 == (tmpRunState[0] & 0x40)) else 0
            elif (2 == AxisdId):
                tmpRunningFlag = 1 if (0x20 == (tmpRunState[0] & 0x20)) else 0
            elif (3 == AxisdId):
                tmpRunningFlag = 1 if (0x10 == (tmpRunState[0] & 0x10)) else 0
            elif (0xFF == AxisdId):
                tmpRunningFlag = 1 if (0x01 == (tmpRunState[0] & 0x01)) else 0
            
        return ret, tmpRunningFlag

if __name__ == "__main__":
    print("Python version: ", sys.version)
    mccard = MoCtrlCard()
    mccard.MoCtrCard_GetAvailablePorts()
    print ("Input the COM PORT, example 'COM1'")
    
    # mccard.MoCtrCard_InitialNet('192.168.1.200', 4196)
    # mccard.MoCtrCard_InitialNet('127.0.0.2', 6001)
    # comPort = input()
    comPort = 'COM3'
    mccard.MoCtrCard_Initial(comPort)
    nRelRunOk = 0
    nRelRunErr = 0
    nTimeOut = 0
    fPos = 10
    tmpLastRunState = 0

    nOutputIndex = 0
    nOutputVal = 0
    nAxisIndx = 0
    nSpdMovCnt = 0

    nTestRoutineIndx = 5

    print("dll version = %x" % mccard.MoCtrCard_GetDLLVersion())
    (ret, tmpRunState) = mccard.MoCtrCard_GetCardVersion()
    if(mccard.FUNRESOK == ret):
        print("card version = %x" % tmpRunState[0])

    while(True):
        time.sleep(1)
        (ret, tmpRunState) = mccard.MoCtrCard_IsAxisRunning(nAxisIndx)
        if(mccard.FUNRESOK == ret):
            if(0 == tmpRunState):
                # 测试相对运动
                if (0 == nTestRoutineIndx):
                    tmpRet = mccard.MoCtrCard_MCrlAxisRelMove(nAxisIndx, -fPos, 10, 0.0)
                    nTestRoutineIndx = -1
                # 测试绝对运动
                elif (1 == nTestRoutineIndx):
                    tmpRet = mccard.MoCtrCard_MCrlAxisAbsMove(nAxisIndx, -fPos, 10, 0.0)
                    nTestRoutineIndx = -1
                # 测速运动方式运动
                elif (2 == nTestRoutineIndx):
                    if(0 == nSpdMovCnt):
                        tmpRet = mccard.MoCtrCard_MCrlAxisAtSpd(nAxisIndx, 10.0)
                        nSpdMovCnt = 0
                # 测试回零
                elif (3 == nTestRoutineIndx):
                    mccard.MoCtrCard_SeekZero(nAxisIndx, 5.0)
                    nTestRoutineIndx = -1
                # 测试重置从标系
                elif (4 == nTestRoutineIndx):
                    mccard.MoCtrCard_ResetCoordinate(nAxisIndx, 100.0)
                    nTestRoutineIndx = -1

                # 设置轴组相对运动
                elif (5 == nTestRoutineIndx):
                    bAxisEn = [1,1,1,1]
                    fCmndDist = [10.0, 20.0, 30.0, 400.0]
                    fCmndSpd = [10.0, 10.0, 10.0, 10.0]
                    fCmndAcc = [10.0, 10.0, 10.0, 10.0]

                    mccard.MoCtrCard_MCrlGroupRelMove(bAxisEn, fCmndDist, fCmndSpd, fCmndAcc, 0)
                    nTestRoutineIndx = -1
                '''
                if(mccard.FUNRESOK == tmpRet):
                    nAxisIndx = nAxisIndx + 1 if (nAxisIndx < 3) else 0
                    fPos = -fPos
                    nRelRunOk += 1
                else:
                    nRelRunErr += 1
                
                print ("Move Err [", nRelRunErr, "] Move OK [", nRelRunOk, "]")
                '''
            else:
                if (2 == nTestRoutineIndx):
                    nSpdMovCnt += 1
                    if(nSpdMovCnt > 5):
                        nSpdMovCnt = 0
                        # 停止轴
                        # tmpRet = mccard.MoCtrCard_StopAxisMov(nAxisIndx)

                        # 改变轴运动参数
                        # tmpRet = mccard.MoCtrCard_ChangeAxisMovPara(nAxisIndx, 1.0, 10.0)
                        
                        # 退出
                        tmpRet = mccard.MoCtrCard_QuiteMotionControl()
                        print("stop axis spd move")
                        nTestRoutineIndx = -1

        # 读取位置
        (res, tmpPos) = mccard.MoCtrCard_GetAxisPos(0xFF)
        if(res == mccard.FUNRESOK):
            print("pos = \t", '%.3f' % tmpPos[0], '%.3f' % tmpPos[1], '%.3f' % tmpPos[2], '%.3f' % tmpPos[3])

        # 读取速度
        (res, tmpPos) = mccard.MoCtrCard_GetAxisSpeed(0xFF)
        if(res == mccard.FUNRESOK):
            print("spd = \t", '%.3f' % tmpPos[0], '%.3f' % tmpPos[1], '%.3f' % tmpPos[2], '%.3f' % tmpPos[3])

        '''
        # 读取 AD 数据
        (res, tmpPos) = mccard.MoCtrCard_GetADValue(0xFF)
        if(res == mccard.FUNRESOK):
            print("joystick = ", '%d' % tmpPos[0], '%d' % tmpPos[1], '%d' % tmpPos[2], '%d' % tmpPos[3])

        # 读输入
        (res, tmpPos) = mccard.MoCtrCard_GetInputState()
        if(res == mccard.FUNRESOK):
            print("input = ", '0x%x' % tmpPos[0])
            # 设输出
            res = mccard.MoCtrCard_SetOutput(nOutputIndex, nOutputVal)
            if(res == mccard.FUNRESOK):
                nOutputIndex = nOutputIndex + 1
                if (nOutputIndex > 15):
                    nOutputVal = 1 if (0 == nOutputVal) else 0
                    nOutputIndex = 0
                    print("write output = ", '0x%x' % nOutputVal)

            # 读输出
            (res, tmpPos) = mccard.MoCtrCard_GetOutputState()
            if(res == mccard.FUNRESOK):
                print("read output = ", '0x%x' % tmpPos[0])
        '''
