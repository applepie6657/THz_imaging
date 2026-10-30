import click
import sys
from pyMcc import MoCtrlCard
import time
import math
import click

mccard = MoCtrlCard()

@click.command()
@click.option('--axisen', default = [1,1,1,1,1,1], prompt = "Axis Enable Byte", help="1 Enable the axis.")
@click.option('--movemode', default = 0, prompt = "Move mode", help='Axis move mode, 0:rel, 1:abs.')
@click.option('--dist', default = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0], prompt = "Axis Move Distance", help='Move Distance.')
@click.option('--vel', default = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0], prompt = "Axis Velocity", help='Axis movement velocity.')
@click.option('--acc', default = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1], prompt='Axis Acceleration', help='Axis movement acceleration.')
@click.option('--cyclecnt', default = 1.0, prompt='Cycle Command Count', help='Group Movement Test Count.')
def fun_testGroupMoveLoop(axisen, movemode, dist, vel, acc, cyclecnt):
    nRelRunOk = 0
    nRelRunErr = 0
    tmpLastRunState = 0
    iCnt = cyclecnt * 2

    (ret, tmpRunState) = mccard.MoCtrCard_GetRunState()
    if(mccard.FUNRESOK == ret):
        tmpLastRunState = tmpRunState[0]

    # send move command firstly
    if(movemode > 0):
        ret = mccard.MoCtrCard_MCrlGroupAbsMovePTP(axisen, dist, vel, acc)
    else:
        ret = mccard.MoCtrCard_MCrlGroupRelMovePTP(axisen, dist, vel, acc)

    if(mccard.FUNRESOK == ret):
        iCnt = iCnt - 1
        while(iCnt > 0):
            time.sleep(0.3)

            # ask the NC Run state, and check the axis move state
            (ret, tmpRunState) = mccard.MoCtrCard_GetRunState()
            if(mccard.FUNRESOK == ret):
                # if Axis stop, send another move command 
                if((tmpRunState[0] & 0x40000000) != (tmpLastRunState & 0x40000000)):
                    tmpLastRunState = tmpRunState[0]
                    dist[0] = 0 - dist[0]
                    dist[1] = 0 - dist[1]
                    dist[2] = 0 - dist[2]
                    dist[3] = 0 - dist[3]
                    dist[4] = 0 - dist[4]
                    dist[5] = 0 - dist[5]

                    if(movemode > 0):
                        ret = mccard.MoCtrCard_MCrlGroupAbsMovePTP(axisen, dist, vel, acc)
                    else:
                        ret = mccard.MoCtrCard_MCrlGroupRelMovePTP(axisen, dist, vel, acc)

                    if(mccard.FUNRESOK == ret):
                        iCnt = iCnt - 1
                        nRelRunOk += 1
                    else:
                        nRelRunErr += 1
                    
                    print("Move %d times, Move OK = %d and Move Error = %d" % (iCnt, nRelRunOk, nRelRunErr))
                    #print ("Move Err [", nRelRunErr, "] Move OK [", nRelRunOk, "]")
            # get the all axis position
            (res, tmpPos) = mccard.MoCtrCard_GetAxisPos(0xFF)
            if(res == mccard.FUNRESOK):
                #print("Axis[%d]'s position = %f" % (0, tmpPos[0]))
                print("axes position = ")
                print(tmpPos)

        mccard.MoCtrCard_ResetCoordinate(0xFF, 0.0)     #clear the axis position
    else:
        print("Send Group PTP Move Command Failed!\n")

@click.command()
#@click.option('--axisid', default = 0, prompt = "Axis ID", help='Axis Index.')
@click.option('--interval', default = 0.5, help='ask information interval.')
def fun_testAskInformaton(interval):
    tmpOutputStt = 0
    tmpOutIndx = 0

    while(True):
        # ask input state
        (res, tmpRes) = mccard.MoCtrCard_GetInputState()
        if(res == mccard.FUNRESOK):
            print("Input Value = %x" % tmpRes[0])
        
        # ask output state
        (res, tmpRes) = mccard.MoCtrCard_GetOutputState()
        if(res == mccard.FUNRESOK):
            print("Output Value = %x" % tmpRes[0])

        # set the output
        tmpOutIndx = tmpOutIndx + 1
        if(mccard.FUNRESERR == mccard.MoCtrCard_SetOutput(tmpOutIndx, tmpOutputStt)):
            print("Set Output Error")
        if(tmpOutIndx > 15):
            tmpOutputStt = 0 if(tmpOutputStt > 0) else 1
            tmpOutIndx = 0

        # read Parameter
        (res, tmpRes) = mccard.MoCtrCard_ReadPara(0, 1)
        if(mccard.FUNRESOK == res):
            print("Axis 0 Manual Distance is %f" % tmpRes)

        # read ad value
        (res, tmpRes) = mccard.MoCtrCard_GetADValue(0)
        if(mccard.FUNRESOK == res):
            print("AD Value is %f" % tmpRes[0])
            #for tmpADVal in tmpRes:
            #    print("AD Value is %d" % tmpADVal)

        time.sleep(interval)

# key word in click command must be low case
@click.command()
@click.option('--axisid', default = 0, prompt = "Axis ID", help='Axis Index.')
@click.option('--movemode', default = 0, prompt = "Move mode", help='Axis move mode, 0:rel, 1:abs.')
@click.option('--dist', default = 10.0, prompt='Distance/Position', help='Test distance/position move Realtive.')
@click.option('--vel', default = 1.0, prompt='Velocity', help='Command Velcity.')
@click.option('--acc', default = 0.0, help='Command Acceleration.')
@click.option('--cycle', default = 1, prompt = "cycle count", help='Test cycle times.')
def fun_testEachAxisMoveLoop(axisid, movemode, dist, vel, acc, cycle):
    nRelRunOk = 0
    nRelRunErr = 0
    tmpLastRunState = 0
    iCnt = cycle * 2
    fPos = math.fabs(dist)

    # send move command firstly
    if(0 == movemode):
        mccard.MoCtrCard_MCrlAxisRelMove(axisid, fPos, vel, acc)
    else:
        mccard.MoCtrCard_MCrlAxisAbsMove(axisid, fPos, vel, acc)

    iCnt = iCnt - 1
    while(iCnt > 0):
        time.sleep(0.3)

        # ask the NC Run state, and check the axis move state
        (ret, tmpRunState) = mccard.MoCtrCard_GetRunState()

        if(mccard.FUNRESOK == ret):
            # if Axis stop, send another move command 
            if((tmpRunState[0] & 0x01) != (tmpLastRunState & 0x01)):
                tmpLastRunState = tmpRunState[0]
                if(0 == movemode):
                    tmpRes = mccard.MoCtrCard_MCrlAxisRelMove(axisid, fPos, vel, acc)
                else:
                    tmpRes = mccard.MoCtrCard_MCrlAxisAbsMove(axisid, fPos, vel, acc)

                if(mccard.FUNRESOK == tmpRes):
                    fPos = -fPos
                    iCnt = iCnt - 1
                    nRelRunOk += 1
                else:
                    nRelRunErr += 1
                
                print("Move %d times, Move OK = %d and Move Error = %d" % (iCnt, nRelRunOk, nRelRunErr))
                #print ("Move Err [", nRelRunErr, "] Move OK [", nRelRunOk, "]")

        # get the all axis position
        (res, tmpPos) = mccard.MoCtrCard_GetAxisPos(axisid)
        if(res == mccard.FUNRESOK):
            print("Axis[%d]'s position = %f" % (axisid, tmpPos[axisid]))
        
        (res, tmpSpd) = mccard.MoCtrCard_GetAxisSpeed(axisid)
        if(res == mccard.FUNRESOK):
            print("Axis[%d]'s speed = %f" % (axisid, tmpSpd[axisid]))



if __name__ == '__main__':
    portlist = mccard.MoCtrCard_GetAvailablePorts()
    if len(portlist) == 0:
        print("not available ports!")
    else:
        for i in range(0, len(portlist)):
            print(portlist[i])

    print ("Input the COM PORT, example 'COM1'")
    comPort = input()
    if(mccard.FUNRESERR ==  mccard.MoCtrCard_Initial(comPort)):
        print("Open the Port Error, and Inital MCC Error!")
    else:
        print("Open the Port Ok, and Initial MCC OK!")
    
    print("start test...")
    #enable one of the test functions below
    #fun_testEachAxisMoveLoop()
    #fun_testGroupMoveLoop()
    #fun_testAskInformaton()
