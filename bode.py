#!/usr/bin/env python3

#
#MIT License
#
#Copyright (c) 2018 Dmitry Melnichansky
#Copyright (c) 2023 Antti J. "Uuki" Niskanen, OH2GVB
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#

import socket, pyvisa, logging, time, math, sys, pathlib

# WHAT MESSAGES DO YOU WANT? NORMALLY "INFO", IN CASE OF PROBLEMS "DEBUG"
#logging.basicConfig(format='%(message)s', level=logging.DEBUG)
logging.basicConfig(format='%(message)s', level=logging.INFO)

VERSION = 'ver. 0.02 / 2023-02-10'
HOST, RPCBIND_PORT, VXI11_PORT = '0.0.0.0', 111, 703
ID_BYTES = b'IDN-SGLT-PRI SDG0000X'

def int2bytes(num):
  return bytes([(num//0x1000000)&0xFF, (num//0x10000)&0xFF,
  (num//0x100)&0xFF, num&0xFF])


########## CONNECT TO, IDENTIFY, AND INITIALIZE SIGNAL GENERATOR ##########

def initialize_generator():
  global gen, instr

  # CONNECT TO GENERATOR AND IDENTIFY
  logging.info("Connecting to generator " + sys.argv[1] + "...")
  rm = pyvisa.ResourceManager()
  try:
    instr = rm.open_resource(sys.argv[1])
    instr.write('*IDN?')
    gen_id=instr.read_raw()
    while True:   # some IDs contain ridiculous extra whitespaces
      x=gen_id
      gen_id=gen_id.replace(b'  ', b' ')
      if gen_id == x: break
    logging.info(gen_id)

    if gen_id[:8]==b'HP 8904A':   # HP 8904A MULTIFUNCTION SYNTHESIZER
      logging.info("Using HP 8904A drirver")
      gen="8904a"
      instr.write('*RST')
      instr.write('GM0;>')                      # ch config mode, show chA
      instr.write('OO1OF;OO2OF;FC1OF;FC2OF')    # outputs off, not float
      instr.write('WFASI;FRA1KZ;APA1VL;PHA0DG') # chA sine 1kHz 1V phase 0
      instr.write('WFBSI;FRB1KZ;APB1VL;PHB0DG') # chB ditto
      instr.write('DEAOC1;DEBOC2;DECOF;DEDOF')  # chA,B to out1,2; chC,D off

    else:   # GENERIC RF SIGNAL GENERATOR THAT TALKS STANDARD SCPI
      logging.info("Using generic SCPI driver")
      gen="scpi"
      instr.write('*RST')
      time.sleep(1)
      instr.write('SYST:PRES')
      time.sleep(1)
      instr.write('*CLS')

  except:
    logging.error("Connection failed")
    quit()


########## SEND COMMAND TO SIGNAL GENERATOR ##########

def send_cmd(what, arg=1):
  try:
    # SPECIAL CASE: Dummy mode without signal generator
    if gen=="dummy": return
  
    # SPECIAL CASE: HP 8904A Multifunction Synthesizer
    elif gen=="8904a":
      if what=="freq": instr.write("FRA%.1fHZ;FRB%.1fHZ" % (arg,arg))
      if what=="ampl": instr.write("APA%.6fVL;APB%.6fVL" % (arg,arg))
      if what=="dbm":
        vpp = sqrt(10**(arg/10)* 50 *0.008)   # This synth prefers volts
        instr.write("APA%.6fVL;APB%.6fVL" % (vpp,vpp))
      if what=="on": instr.write("OO1ON;OO2ON")
      if what=="off": instr.write("OO1OF;OO2OF")

    elif gen=="scpi":
      if what=="freq": 
        instr.write("SOURce1:FREQ %.3f" % (arg))
      if what=="ampl":
        instr.write("SOURce1:VOLTage:IMMediate:AMPL %.3f" % (arg))

      if what=="dbm": logging.info("no dbm >:C")
      if what=="on": instr.write("OUTP:STAT ON")
      if what=="off": instr.write("OUTP:STAT OFF")
      instr.write("SYST:ERR?")
      resp=instr.read_raw()
      if resp[0:1] != b'0' and resp[0:2] != b'+0': logging.error(resp)

    # DEFAULT: Generic SCPI RF signal generator
    else:
      if what=="freq": instr.write("FREQ %.3f HZ" % (arg))
      if what=="ampl":
        dbm = 10*math.log10(arg**2/ 50 /0.008)   # 50ohm load
        instr.write("POWER %.3f DBM" % (dbm))   # RF generators prefer dBm
      if what=="dbm": instr.write("POWER %.3f DBM" % (arg))
      if what=="on": instr.write("OUTP:STAT ON")
      if what=="off": instr.write("OUTP:STAT OFF")
      instr.write("SYST:ERR?")
      resp=instr.read_raw()
      if resp[0:1] != b'0' and resp[0:2] != b'+0': logging.error(resp)

  except:
    logging.error("Error while talking to instrument")
    quit()


########## PARSE COMMAND FROM OSCILLOSCOPE ##########

def parse_cmd(line):
  line=line.strip()
  logging.debug(line)
  if line.endswith(b'?'): return  #ignore queries
  channel = int(line[1])   #unused for now
  for cmd in line[3:].split(b';'):  #BSWV or OUTP commands separated by ";"
    token = cmd[0:4]
    args = cmd[5:].split(b',')   #command arguments separated by ","
    if token == b'BSWV':
      n = 0
      while n < len(args):
        if args[n] == b'FRQ':
          send_cmd("freq", float(args[n+1]))
          n += 2
        elif args[n] == b'AMP':
          send_cmd("ampl", float(args[n+1]))
          n += 2
        elif args[n] == b'AMPDBM':
          send_cmd("dbm", float(args[n+1]))
          n += 2
        elif args[n] == b'WVTP' or args[n] == b'OFST' or args[n] == b'PHSE':
          n += 2   #wave type, offset and phase with arguments are ignored
        else:
          n += 1   #anything else is also ignored
    elif token == b'OUTP':
      n = 0
      while n < len(args):
        if args[n] == b'ON':
          send_cmd("on")
          n += 1
        elif args[n] == b'OFF':   #this never happens, by the way
          send_cmd("off")
          n += 1
        elif args[n] == b'LOAD':
          n += 2     #load impedance is whatever, it shall be ignored
        else:
          n += 1     #anything else is also ignored


####################################################
##########    MAIN PROGRAM STARTS HERE    ##########
####################################################

print('\n' + pathlib.Path(__file__).name + '  ' + VERSION + '\n')
if len(sys.argv) != 2:
  print('Usage:  ' + pathlib.Path(__file__).name + ' [RESOURCE_ID]\n\n'
  'RESOURCE_ID is the PyVISA resource ID of the signal generator. Examples:\n'
  '  GPIB::19::INSTR  for instrument with ID 19 on GPIB bus\n'
  '  ASRL/dev/ttyUSB0::INSTR  for serial instrument on ttyUSB0\n'
  '  TCPIP::10.42.47.18::INSTR  for Ethernet instrument at 10.42.47.18\n'
  '  USB0::0x1234::0x9876::something::INSTR  for USBTMC instrument\n'
  '\n'
  'If RESOURCE_ID is not specified, the program will run in "dummy mode"\n'
  'and communicate only with the oscilloscope, not with any signal\n'
  'generator.\n')
if len(sys.argv) > 2: quit()
if len(sys.argv) == 1:
  gen="dummy"
  print('\n * * *  NOW RUNNING IN DUMMY MODE!  * * *\n')
else: initialize_generator()

# BIND TO THE SOCKETS
rpc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
rpc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
rpc_sock.bind((HOST, RPCBIND_PORT))
rpc_sock.listen(1)
lxi_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lxi_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lxi_sock.bind((HOST, VXI11_PORT))
lxi_sock.listen(1)
logging.info("Server started")

# RUN THE SERVER
try:   #until Ctrl+C is pressed
  while True:
    conn, addr = rpc_sock.accept()   #addr is unused
    rx_buf = conn.recv(128)
    if len(rx_buf) > 0:
      # expecting GET PORT procedure (3) and VXI11 core ID (395183)
      if rx_buf[0x18:0x1c] != b'\x00\x00\x00\x03'\
      or rx_buf[0x2C:0x30] != b'\x00\x06\x07\xAF':
        logging.warning("Incompatible request.")
        continue
      logging.debug("Received request")
      resp = int2bytes(VXI11_PORT)
      # reply with XID, reply (1), accept (0), AUTH_NULL (0),
      # length 0, RPC success (0)
      rpc_hdr = rx_buf[0x04:0x08] + b'\x00\x00\x00\x01'\
      + b'\x00\x00\x00\x00' + b'\x00\x00\x00\x00'\
      + b'\x00\x00\x00\x00' + b'\x00\x00\x00\x00'
      size_hdr = int2bytes((len(rpc_hdr)+len(resp)) | 0x80000000)
      conn.send(size_hdr + rpc_hdr + resp)
    conn.close()
    conn, addr = lxi_sock.accept()
    while True:
      rx_buf = conn.recv(255)
      if len(rx_buf) == 0:
        continue   #nothing received, nothing to do this round
      if rx_buf[0x10:0x14] != b'\x00\x06\x07\xAF':   #VXI core ID
        logging.warning("Request from unknown source.")
        break
      if rx_buf[0x18:0x1C] == b'\x00\x00\x00\x0A':
        logging.debug("Create link")
        #no error (0), link ID 0, abort port 0, max rcv size 0x800000
        resp = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'\
        + b'\x00\x80\x00\x00'
      elif rx_buf[0x18:0x1C] == b'\x00\x00\x00\x0B':
        logging.debug("Device write")
        cmd = rx_buf[0x40:0x40+int.from_bytes(rx_buf[0x3C:0x40],"big")]
        parse_cmd(cmd)
      elif rx_buf[0x18:0x1C] == b'\x00\x00\x00\x0C':
        logging.debug("Device read")
        #no error (0), END (4)
        resp = b'\x00\x00\x00\x00\x00\x00\x00\x04'\
        + int2bytes(len(ID_BYTES)+3) + ID_BYTES + b'\x0A\x00\x00'
      elif rx_buf[0x18:0x1C] == b'\x00\x00\x00\x17':
        logging.debug("Destroy link")
        break
      else:
        logging.warning("Unknown VXI-11 request")
        break
      rpc_hdr = rx_buf[0x04:0x08] + b'\x00\x00\x00\x01\x00\x00\x00\x00'\
      + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
      size_hdr = int2bytes((len(rpc_hdr)+len(resp)) | 0x80000000)
      conn.send(size_hdr + rpc_hdr + resp)
    conn.close()
  try: lxi_sock.close()
  except: pass
except KeyboardInterrupt: logging.info("\n\nExiting...")

# CLOSE THE SERVER PORTS AND TURN OFF THE GENERATOR OUTPUT
try: rpc_sock.close()
except: pass
try: lxi_sock.close()
except: pass
if gen!="dummy":
  send_cmd("off")
  instr.close()
logging.info("Bye!")

