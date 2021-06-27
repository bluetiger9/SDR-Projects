import wave
import sys
    
class Decoder:
    MIN_STATE_LEN = 50
    
    zeros = 0
    pos = 0
    neg = 0
    state = "ZEROS"
    prevState = "ZEROS"
    stateLen = 0
    onOffLen = 0
    onOffState = "OFF"
    prevOnOffState = "OFF"
    prevOnOffLen = 0
    msg = ""
    msgStart = -1
    avgSum = 0
    avgMax = 0
     
    def updateState(self, final = False):
        if self.stateLen >= self.MIN_STATE_LEN:
            if self.pos > 4062027 and self.pos < 4102027: print(self.pos, self.prevState, self.stateLen)
            if self.prevState == "ZEROS":
              self.onOffState = "OFF"
                                          
            else:
              self.onOffState = "ON"
            
            if self.onOffLen > 0 and self.avgSum / self.onOffLen <= 30.0:
              self.prevOnOffState = "OFF"
            
            if self.prevOnOffState != self.onOffState:
              #print(prevOnOffState, onOffLen, prevState, state)
              if self.prevOnOffState == "ON":
                if self.onOffLen > 500 and self.onOffLen < 1000:
                  self.msg += "0"
                  #print("LOW", self.avgSum / self.onOffLen, self.avgMax)
                elif self.onOffLen > 1200 and self.onOffLen < 2000:
                  self.msg += "1"
                  #print("HIGH", self.avgSum / self.onOffLen, self.avgMax)
                elif self.onOffLen > 4000:
                  self.msg = ""
                  self.msgStart = self.pos                  
                  print("SYNC", self.onOffLen, self.avgSum / self.onOffLen, self.avgMax, self.pos)
                else:
                  print("UNKNOWN", self.onOffLen, self.avgSum / self.onOffLen, self.avgMax, self.pos)
              elif self.onOffLen > 5000:
                 print("{}(+{})\t{}".format(self.msgStart, self.pos - self.msgStart, self.msg))
                 self.msg = ""
                 self.msgStart = -1

              self.prevOnOffLen = self.onOffLen
              self.prevOnOffState = self.onOffState
              self.onOffLen = 0
              self.avgSum = 0
              self.avgMax = 0

            self.onOffLen += self.stateLen
            #print(prevState, stateLen, onLen, offLen)            
            self.stateLen = 0           
           
        if final:
           self.stateLen = 99999
           self.onOffLen = 99999
           self.prevState = "NEG"
           self.prevOnOffState = "OFF"
           self.updateState(False)

    def processValue(self, val):
        #intVal = int.from_bytes([val], "big", signed = True)        
        if abs(val) < 50:
            val = 0        
        
        if self.pos > 4062027 and self.pos < 4102027: print(self.pos, val)
        
        self.avgSum += abs(val)
        self.avgMax = abs(val) if abs(val) > self.avgMax else self.avgMax
        self.prevState = self.state if self.stateLen >= self.MIN_STATE_LEN else self.prevState
        if val > 0:
          self.zeros = 0
          self.state = "POS"
          
        elif val < 0:
          self.zeros = 0
          self.state = "NEG"
        
        else:
          self.zeros += 1
          if self.zeros >= self.MIN_STATE_LEN:
            self.state = "ZEROS"
          
        if self.state is not self.prevState:
          self.updateState()
          
        self.stateLen += 1        
        self.pos += 1
        #print(val)

def main():
    file = sys.argv[1]    
    print("WAV File: {}".format(file))
    
    w = wave.open(file, 'r')
    nrFrames = w.getnframes()
    print("Nr frames: {}".format(nrFrames))
    total = 0
    
    decoder = Decoder()
    for i in range(int(nrFrames / 1024 / 1024) + 1):
      frame = w.readframes(1024*1024)
      
      for j in range(0, len(frame), 2):
        val = frame[j] - 128        
        decoder.processValue(val)        
        
      total += len(frame)
    
    decoder.updateState(True)
    
    print("Read frames: {}".format(total)) 
    print("Done")

if __name__ == "__main__":
    main()
